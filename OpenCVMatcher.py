# OpenCVMatcher.py
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw

# OpenCV + NumPy
import cv2
import numpy as np

@dataclass
class Detection:
    name: str
    score: float
    box: Tuple[int, int, int, int]   # (x1, y1, x2, y2)
    scale: float

class OpenCVMatcher:
    """
    Template Matching multi-escala con pre-procesamiento opcional.
    - Basado en cv2.matchTemplate con TM_CCOEFF_NORMED.
    - Soporta bordes (Canny) y CLAHE para contraste.
    - NMS para filtrar solapes.
    """

    def __init__(self,
                 use_edges: bool = True,
                 use_clahe: bool = True,
                 canny_low: int = 60,
                 canny_high: int = 180):
        self.use_edges = use_edges
        self.use_clahe = use_clahe
        self.canny_low = canny_low
        self.canny_high = canny_high

    # ---------- Utils ----------
    @staticmethod
    def _pil_to_bgr(img: Image.Image) -> np.ndarray:
        arr = np.array(img.convert("RGB"))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    @staticmethod
    def _to_gray(bgr: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    def _preprocess(self, gray: np.ndarray) -> np.ndarray:
        # CLAHE mejora contraste local en condiciones de iluminación variables
        if self.use_clahe:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        if self.use_edges:
            # Edges robustos a color/iluminación
            gray = cv2.Canny(gray, self.canny_low, self.canny_high)
        return gray

    @staticmethod
    def _nms(boxes: List[Detection], iou_thr: float = 0.4) -> List[Detection]:
        if not boxes:
            return []
        boxes_sorted = sorted(boxes, key=lambda d: d.score, reverse=True)
        picked: List[Detection] = []

        def area(b: Tuple[int,int,int,int]) -> int:
            return max(0, b[2]-b[0]) * max(0, b[3]-b[1])

        def iou(a: Tuple[int,int,int,int], b: Tuple[int,int,int,int]) -> float:
            x1, y1 = max(a[0], b[0]), max(a[1], b[1])
            x2, y2 = min(a[2], b[2]), min(a[3], b[3])
            inter = max(0, x2-x1) * max(0, y2-y1)
            return inter / (area(a) + area(b) - inter + 1e-6)

        while boxes_sorted:
            cur = boxes_sorted.pop(0)
            picked.append(cur)
            boxes_sorted = [d for d in boxes_sorted if iou(cur.box, d.box) < iou_thr]
        return picked

    # ---------- Matching ----------
    def match_single_template(self,
                            ticket_img: Image.Image,
                            tpl_img: Image.Image,
                            tpl_name: str,
                            threshold: float = 0.75,
                            scales: Optional[List[float]] = None,
                            max_per_template: int = 50) -> List[Detection]:
        """
        Devuelve las detecciones por plantilla (sin NMS global).
        Evita crash cuando la plantilla (redimensionada) es mayor que la imagen.
        """
        bgr = self._pil_to_bgr(ticket_img)
        tpl_bgr = self._pil_to_bgr(tpl_img)
        g = self._to_gray(bgr)
        tg = self._to_gray(tpl_bgr)

        g = self._preprocess(g)
        tg = self._preprocess(tg)

        H, W = g.shape[:2]

        if scales is None:
            scales = [1.4, 1.3, 1.2, 1.1, 1.0, 0.95, 0.9, 0.85, 0.8, 0.75]

        dets: List[Detection] = []
        for s in scales:
            th = max(10, int(tg.shape[0] * s))
            tw = max(10, int(tg.shape[1] * s))

            # --- Guardas de seguridad: no intentes match si la plantilla supera el tamaño de la imagen
            if th > H or tw > W:
                continue  # saltar esa escala

            # Redimensiona la plantilla y valida de nuevo
            tpl_rs = cv2.resize(tg, (tw, th), interpolation=cv2.INTER_AREA)
            if tpl_rs.shape[0] > g.shape[0] or tpl_rs.shape[1] > g.shape[1]:
                continue

            # TM_CCOEFF_NORMED recomendado
            res = cv2.matchTemplate(g, tpl_rs, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(res >= threshold)

            for (x, y) in zip(xs, ys):
                score = float(res[y, x])
                dets.append(Detection(
                    name=tpl_name,
                    score=score,
                    box=(int(x), int(y), int(x + tw), int(y + th)),
                    scale=s
                ))
                if len(dets) >= max_per_template:
                    break

        return dets

    def match_multiple(self,
                       ticket_img: Image.Image,
                       templates: Dict[str, Image.Image],
                       threshold: float = 0.75,
                       scales: Optional[List[float]] = None,
                       nms_iou: float = 0.4,
                       max_per_template: int = 50) -> List[Detection]:
        """
        Ejecuta matching para 1..N plantillas y aplica NMS global.
        """
        all_dets: List[Detection] = []
        for name, tpl in templates.items():
            all_dets.extend(self.match_single_template(
                ticket_img, tpl, name,
                threshold=threshold,
                scales=scales,
                max_per_template=max_per_template
            ))
        return self._nms(all_dets, iou_thr=nms_iou)
    
    # --- Diagnóstico: mejor coincidencia global (aunque no supere umbral)
    def find_best_of_templates(self,
                            ticket_img: Image.Image,
                            templates: Dict[str, Image.Image],
                            scales: Optional[List[float]] = None) -> Optional[Detection]:
        bgr = self._pil_to_bgr(ticket_img)
        g = self._to_gray(bgr)
        g = self._preprocess(g)

        best: Optional[Detection] = None

        if scales is None:
            scales = [1.4, 1.3, 1.2, 1.1, 1.0, 0.95, 0.9, 0.85, 0.8, 0.75]

        for name, tpl in templates.items():
            tpl_bgr = self._pil_to_bgr(tpl)
            tg = self._to_gray(tpl_bgr)
            tg = self._preprocess(tg)

            for s in scales:
                th, tw = max(10, int(tg.shape[0]*s)), max(10, int(tg.shape[1]*s))
                if th < 10 or tw < 10 or th > g.shape[0] or tw > g.shape[1]:
                    continue
                tpl_rs = cv2.resize(tg, (tw, th), interpolation=cv2.INTER_AREA)

                res = cv2.matchTemplate(g, tpl_rs, cv2.TM_CCOEFF_NORMED)
                minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(res)
                x, y = int(maxLoc[0]), int(maxLoc[1])
                cand = Detection(name=name, score=float(maxVal),
                                box=(x, y, x+tw, y+th), scale=s)

                if best is None or cand.score > best.score:
                    best = cand
        return best


    # ---------- Visualización ----------
    @staticmethod
    def draw_detections(img: Image.Image,
                        detections: List[Detection],
                        width: int = 4) -> Image.Image:
        out = img.copy()
        draw = ImageDraw.Draw(out)
        for det in detections:
            (x1, y1, x2, y2) = det.box
            draw.rectangle([(x1, y1), (x2, y2)], outline=(0, 200, 0), width=width)
            caption = f"{det.name} {det.score*100:.1f}%"
            tw, th = draw.textlength(caption), 14
            draw.rectangle([(x1, max(0, y1 - th - 4)), (x1 + tw + 6, y1)], fill=(0, 200, 0))
            draw.text((x1 + 3, max(0, y1 - th - 2)), caption, fill="black")
        return out

    def match_article_style(self,
                            ticket_img: Image.Image,
                            tpl_img: Image.Image,
                            tpl_name: str = "template",
                            threshold: float = 0.70,
                            tpl_scale: float = 1.0,
                            nms_iou: float = 0.4,
                            max_hits: int = 200) -> List[Detection]:
        """
        Modo básico 'estilo artículo':
        - 1 sola escala (tpl_scale).
        - Gris, sin Canny/CLAHE (idéntico al ejemplo).
        - Threshold directo sobre TM_CCOEFF_NORMED.
        - NMS para limpiar duplicados.

        Úsalo cuando ya sabes el tamaño aproximado del recorte respecto al billete.
        """
        # PIL -> OpenCV (BGR)
        import cv2, numpy as np
        bgr = self._pil_to_bgr(ticket_img)
        tpl_bgr = self._pil_to_bgr(tpl_img)

        # Gris puro (igual al artículo)
        g  = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        tg = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)

        # Escala de la plantilla (si no es 1.0)
        if abs(tpl_scale - 1.0) > 1e-3:
            new_w = max(10, int(tg.shape[1] * tpl_scale))
            new_h = max(10, int(tg.shape[0] * tpl_scale))
            tg = cv2.resize(tg, (new_w, new_h), interpolation=cv2.INTER_AREA)

        th, tw = tg.shape[:2]
        H, W   = g.shape[:2]
        if th > H or tw > W:
            return []

        # matchTemplate + threshold
        res = cv2.matchTemplate(g, tg, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= float(threshold))

        dets: List[Detection] = []
        for (x, y) in zip(xs, ys):
            score = float(res[y, x])
            dets.append(Detection(
                name=tpl_name,
                score=score,
                box=(int(x), int(y), int(x + tw), int(y + th)),
                scale=tpl_scale
            ))
            if len(dets) >= int(max_hits):
                break

        # Limpieza de solapes
        return self._nms(dets, iou_thr=float(nms_iou))
