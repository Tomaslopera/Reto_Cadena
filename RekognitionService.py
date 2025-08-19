# RekognitionService.py
import io
import re
from io import BytesIO
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import boto3
from PIL import Image, ImageDraw, ImageFont  # <-- agregado ImageFont

# --- OpenCV opcional (para template matching) ---
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False


@dataclass
class BBox:
    left: float
    top: float
    width: float
    height: float


class RekognitionService:
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("rekognition", region_name=region_name)

    # ---------- Utilidades ----------
    @staticmethod
    def _pil_to_bytes(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _normbox_to_pixels(bbox: Dict, img_w: int, img_h: int) -> Tuple[int, int, int, int]:
        x1 = int(bbox["Left"] * img_w)
        y1 = int(bbox["Top"] * img_h)
        x2 = int((bbox["Left"] + bbox["Width"]) * img_w)
        y2 = int((bbox["Top"] + bbox["Height"]) * img_h)
        return x1, y1, x2, y2

    @staticmethod
    def draw_boxes(img: Image.Image, boxes: List[Tuple[int, int, int, int]], width: int = 4) -> Image.Image:
        out = img.copy()
        draw = ImageDraw.Draw(out)
        for (x1, y1, x2, y2) in boxes:
            draw.rectangle([(x1, y1), (x2, y2)], outline=(255, 0, 0), width=width)
        return out

    @staticmethod
    def _safe_font(size: int = 16):
        """Intenta cargar una fuente TTF; si no, usa la por defecto."""
        try:
            return ImageFont.truetype("arial.ttf", size=size)
        except Exception:
            try:
                return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=size)
            except Exception:
                return ImageFont.load_default()

    # ---------- Rekognition: texto/etiquetas ----------
    def detect_text(self, image_bytes: bytes) -> Dict:
        return self.client.detect_text(Image={"Bytes": image_bytes})

    def find_cruz_roja_by_text(self, image_bytes: bytes, min_conf: float = 80.0) -> Dict:
        """Busca la frase completa como LINE (a veces no aparece así)."""
        resp = self.detect_text(image_bytes)
        lines = [
            t
            for t in resp.get("TextDetections", [])
            if t.get("Type") == "LINE" and t.get("Confidence", 0) >= min_conf
        ]
        found_boxes = []
        for line in lines:
            text = line.get("DetectedText", "").lower()
            if "cruz" in text and "roja" in text and "colombiana" in text:
                found_boxes.append(line["Geometry"]["BoundingBox"])
        return {"found": len(found_boxes) > 0, "boxes": found_boxes, "raw": resp}

    def detect_labels(self, image_bytes: bytes, max_labels: int = 20, min_conf: float = 70.0) -> Dict:
        """Detecta etiquetas genéricas como en la demo de AWS."""
        return self.client.detect_labels(
            Image={"Bytes": image_bytes},
            MaxLabels=max_labels,
            MinConfidence=min_conf
        )

    def draw_label_instances_with_names(self, img: Image.Image, labels_resp: Dict) -> Optional[Image.Image]:
        """
        Dibuja cajas para cada 'Instance' de cada etiqueta (si existen),
        rotulando con 'Nombre Conf%'. Si no hay instancias, retorna None.
        """
        labels = labels_resp.get("Labels", [])
        has_any = any(len(lb.get("Instances", [])) > 0 for lb in labels)
        if not has_any:
            return None

        out = img.copy()
        draw = ImageDraw.Draw(out)
        W, H = out.size
        # tamaño de fuente proporcional al ancho
        font = self._safe_font(size=max(12, int(W * 0.015)))

        for lb in labels:
            name = lb.get("Name", "")
            conf_lab = lb.get("Confidence", 0.0)
            for inst in lb.get("Instances", []):
                bbox = inst.get("BoundingBox")
                if not bbox:
                    continue
                x1, y1, x2, y2 = self._normbox_to_pixels(bbox, W, H)
                # caja
                draw.rectangle([(x1, y1), (x2, y2)], outline=(255, 0, 0), width=3)
                # rótulo
                label_txt = f"{name} {conf_lab:.1f}%"
                try:
                    # PIL >= 8.0
                    tx1, ty1, tx2, ty2 = draw.textbbox((0, 0), label_txt, font=font)
                    tw, th = (tx2 - tx1), (ty2 - ty1)
                except Exception:
                    # Fallback
                    tw = int(draw.textlength(label_txt, font=font))
                    th = font.size + 6

                # fondo del rótulo (arriba de la caja)
                pad = 4
                y_top = max(0, y1 - th - 2)
                draw.rectangle([(x1, y_top), (x1 + tw + 2 * pad, y_top + th)], fill=(255, 0, 0))
                draw.text((x1 + pad, y_top), label_txt, fill=(255, 255, 255), font=font)

        return out

    def find_phrase_by_words(
        self,
        image_bytes: bytes,
        target_words=("cruz", "roja", "colombiana"),
        min_conf: float = 70.0,
        word_gap_px: int = 140,
        y_tol: float = 0.12
    ) -> Dict:
        """
        Busca la secuencia target_words como WORDs en la misma línea visual.
        Retorna: found, boxes_px, boxes_norm, raw, debug_matches
        """
        pil_img = Image.open(BytesIO(image_bytes)).convert("RGB")
        W, H = pil_img.size

        resp = self.detect_text(image_bytes)
        dets = resp.get("TextDetections", [])

        words = []
        for t in dets:
            if t.get("Type") != "WORD":
                continue
            if t.get("Confidence", 0) < min_conf:
                continue
            txt = re.sub(r"[^0-9a-záéíóúñ]+", "", t.get("DetectedText", "").lower())
            if not txt:
                continue
            bb = t["Geometry"]["BoundingBox"]
            x1, y1, x2, y2 = self._normbox_to_pixels(bb, W, H)
            words.append({
                "text": txt,
                "bb_norm": bb,
                "bb_px": (x1, y1, x2, y2),
                "cx": (x1 + x2) // 2,
                "cy": (y1 + y2) // 2,
                "left": x1,
            })

        words.sort(key=lambda w: (w["cy"], w["left"]))

        found_boxes_px: List[Tuple[int, int, int, int]] = []
        debug = []

        for i, w1 in enumerate(words):
            if w1["text"] != target_words[0]:
                continue
            for j in range(i + 1, len(words)):
                w2 = words[j]
                if abs(w2["cy"] - w1["cy"]) > y_tol * H:
                    continue
                if w2["left"] <= w1["bb_px"][2]:
                    continue
                if (w2["left"] - w1["bb_px"][2]) > word_gap_px:
                    break
                if w2["text"] != target_words[1]:
                    continue

                for k in range(j + 1, len(words)):
                    w3 = words[k]
                    if abs(w3["cy"] - w1["cy"]) > y_tol * H:
                        continue
                    if w3["left"] <= w2["bb_px"][2]:
                        continue
                    if (w3["left"] - w2["bb_px"][2]) > word_gap_px:
                        break
                    if w3["text"] != target_words[2]:
                        continue

                    x1 = w1["bb_px"][0]
                    y1 = min(w1["bb_px"][1], w2["bb_px"][1], w3["bb_px"][1])
                    x2 = w3["bb_px"][2]
                    y2 = max(w1["bb_px"][3], w2["bb_px"][3], w3["bb_px"][3])
                    found_boxes_px.append((x1, y1, x2, y2))
                    debug.append((w1["text"], w2["text"], w3["text"]))
                    break

        boxes_norm = []
        for (x1, y1, x2, y2) in found_boxes_px:
            boxes_norm.append({
                "Left": x1 / W,
                "Top": y1 / H,
                "Width": (x2 - x1) / W,
                "Height": (y2 - y1) / H
            })

        return {
            "found": len(found_boxes_px) > 0,
            "boxes_px": found_boxes_px,
            "boxes_norm": boxes_norm,
            "raw": resp,
            "debug_matches": debug
        }

    # ---------- Template matching opcional ----------
    def template_match_logo(
        self,
        ticket_img: Image.Image,
        logo_img: Image.Image,
        threshold: float = 0.75,
        multi_scale: bool = True,
        scales: Optional[List[float]] = None,
        use_edges: bool = True
    ) -> List[Tuple[int,int,int,int]]:
        """
        Coincidencia de plantilla para ubicar el logo dentro del billete.
        - threshold: 0.70–0.85 suele ir bien.
        - multi_scale: busca en varias escalas.
        - use_edges: activa matching sobre bordes (Canny) que es más robusto a color/iluminación.
        Devuelve lista de cajas (x1,y1,x2,y2) en píxeles.
        """
        if not CV2_AVAILABLE:
            return []

        import numpy as np, cv2

        # --- PIL -> OpenCV
        tik = cv2.cvtColor(np.array(ticket_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        tpl = cv2.cvtColor(np.array(logo_img.convert("RGB")),  cv2.COLOR_RGB2BGR)

        # --- A grises
        tik_gray = cv2.cvtColor(tik, cv2.COLOR_BGR2GRAY)
        tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)

        # --- Pre-procesamiento suave (mejora contraste local)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        tik_gray = clahe.apply(tik_gray)
        tpl_gray = clahe.apply(tpl_gray)

        if use_edges:
            # Edges (robusto a color/ruido)
            tik_gray = cv2.Canny(tik_gray, 60, 180)
            tpl_gray = cv2.Canny(tpl_gray, 60, 180)

        # --- Multi-escala
        if scales is None:
            # Rango amplio; ajusta si tu recorte es muy grande/pequeño
            scales = [1.4, 1.3, 1.2, 1.1, 1.0, 0.95, 0.9, 0.85, 0.8, 0.75]

        boxes: List[Tuple[int,int,int,int]] = []

        for s in scales if multi_scale else [1.0]:
            th, tw = max(10, int(tpl_gray.shape[0] * s)), max(10, int(tpl_gray.shape[1] * s))
            if th < 10 or tw < 10:
                continue
            tpl_rs = cv2.resize(tpl_gray, (tw, th), interpolation=cv2.INTER_AREA)

            # Matching normalizado (COEFF_NORMED)
            res = cv2.matchTemplate(tik_gray, tpl_rs, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= threshold)

            for pt in zip(*loc[::-1]):  # (x, y)
                x1, y1 = int(pt[0]), int(pt[1])
                x2, y2 = x1 + tw, y1 + th
                boxes.append((x1, y1, x2, y2))

        # --- NMS para limpiar duplicados
        return self._nms(boxes, iou_threshold=0.4)

    @staticmethod
    def _nms(boxes: List[Tuple[int, int, int, int]], iou_threshold: float = 0.4) -> List[Tuple[int, int, int, int]]:
        if not boxes:
            return []
        def area(b): return max(0, b[2] - b[0]) * max(0, b[3] - b[1])
        def iou(a, b):
            x1, y1 = max(a[0], b[0]), max(a[1], b[1])
            x2, y2 = min(a[2], b[2]), min(a[3], b[3])
            inter = max(0, x2 - x1) * max(0, y2 - y1)
            return inter / (area(a) + area(b) - inter + 1e-6)
        boxes_sorted = sorted(boxes, key=area, reverse=True)
        picked = []
        while boxes_sorted:
            cur = boxes_sorted.pop(0)
            picked.append(cur)
            boxes_sorted = [b for b in boxes_sorted if iou(cur, b) < iou_threshold]
        return picked
