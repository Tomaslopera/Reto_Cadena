# RekognitionService.py
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from io import BytesIO
import io

import boto3
from PIL import Image, ImageDraw, ImageFont

@dataclass
class BBoxNorm:
    Left: float
    Top: float
    Width: float
    Height: float

class RekognitionService:
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("rekognition", region_name=region_name)

    # ---------- Utilidades ----------
    @staticmethod
    def pil_to_bytes(img: Image.Image) -> bytes:
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
    def _safe_font(size: int = 16):
        try:
            return ImageFont.truetype("arial.ttf", size=size)
        except Exception:
            try:
                return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=size)
            except Exception:
                return ImageFont.load_default()

    # ---------- Rekognition: DetectLabels ----------
    def detect_labels(self, image_bytes: bytes, max_labels: int = 20, min_conf: float = 70.0) -> Dict:
        return self.client.detect_labels(
            Image={"Bytes": image_bytes},
            MaxLabels=max_labels,
            MinConfidence=min_conf
        )

    def detect_labels_pretty(self, image_bytes: bytes, max_labels: int = 20, min_conf: float = 70.0) -> Dict:
        """
        Devuelve una estructura amigable:
        {
          "labels": [{"name","confidence","parents", "instances"}...],
          "labeled_boxes": [{"name","confidence","box":(x1,y1,x2,y2)}...],
          "raw": <respuesta completa de Rekognition>
        }
        """
        resp = self.detect_labels(image_bytes, max_labels=max_labels, min_conf=min_conf)

        labels_tbl: List[Dict] = []
        labeled_boxes: List[Dict] = []

        # (para dibujar cajas, necesitamos tamaño de imagen)
        pil_img = Image.open(BytesIO(image_bytes)).convert("RGB")
        W, H = pil_img.size

        for lb in resp.get("Labels", []):
            name = lb.get("Name", "")
            conf = round(float(lb.get("Confidence", 0.0)), 2)
            parents = [p.get("Name", "") for p in lb.get("Parents", []) if p.get("Name")]
            instances = lb.get("Instances", []) or []

            labels_tbl.append({
                "name": name,
                "confidence": conf,
                "parents": parents,
                "instances": len(instances)
            })

            for inst in instances:
                bbox = inst.get("BoundingBox")
                if not bbox:
                    continue
                x1, y1, x2, y2 = self._normbox_to_pixels(bbox, W, H)
                labeled_boxes.append({
                    "name": name,
                    "confidence": conf,
                    "box": (x1, y1, x2, y2)
                })

        return {
            "labels": labels_tbl,
            "labeled_boxes": labeled_boxes,
            "raw": resp
        }

    def draw_labeled_boxes(self, img: Image.Image, labeled_boxes: List[Dict], width: int = 3) -> Image.Image:
        """
        Dibuja rectángulos y rótulos "Nombre Conf%" sobre la imagen.
        """
        if not labeled_boxes:
            return img

        out = img.copy()
        draw = ImageDraw.Draw(out)
        W, H = out.size
        font = self._safe_font(size=max(12, int(W * 0.015)))

        for obj in labeled_boxes:
            name = obj.get("name", "")
            conf = obj.get("confidence", 0.0)
            (x1, y1, x2, y2) = obj.get("box", (0, 0, 0, 0))

            # caja
            draw.rectangle([(x1, y1), (x2, y2)], outline=(255, 0, 0), width=width)

            # rótulo
            label_txt = f"{name} {conf:.1f}%"
            try:
                tx1, ty1, tx2, ty2 = draw.textbbox((0, 0), label_txt, font=font)
                tw, th = (tx2 - tx1), (ty2 - ty1)
            except Exception:
                tw = int(draw.textlength(label_txt, font=font))
                th = font.size + 6

            pad = 4
            y_top = max(0, y1 - th - 2)
            draw.rectangle([(x1, y_top), (x1 + tw + 2 * pad, y_top + th)], fill=(255, 0, 0))
            draw.text((x1 + pad, y_top), label_txt, fill=(255, 255, 255), font=font)

        return out
