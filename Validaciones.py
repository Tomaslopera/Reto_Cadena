import re
from RekognitionService import RekognitionService
from typing import Dict, List, Tuple
from PIL import Image

class Validaciones:
    def __init__(self, raw_text: str, sorteo: str, fecha_sorteo: str, dia_de_juego: str, hora_de_juego: str, premio_mayor: str, valor_billete: str, valor_fraccion: str, serie: str, numero: str):
        self.text = self._preprocesar(raw_text)
        self.sorteo = sorteo.lower()
        self.fecha_sorteo = fecha_sorteo.lower()
        self.dia_de_juego = dia_de_juego.lower()
        self.hora_de_juego = hora_de_juego.lower()
        self.premio_mayor = premio_mayor.lower()
        self.valor_billete = valor_billete.lower()
        self.valor_fraccion = valor_fraccion.lower()
        self.serie = serie.lower()
        self.numero = numero.lower()
        # self.numero_escrito = [p.lower().strip() for p in numero_escrito if p.strip()]
    
    def _preprocesar(self, texto: str) -> str:
        # Convierte a minúsculas, elimina saltos de línea y múltiples espacios
        texto = texto.lower()
        texto = texto.replace("\n", " ")
        texto = re.sub(r"\s+", " ", texto)  # Remueve espacios duplicados
        return texto    

    def check_sorteo(self):
        return self.sorteo in self.text
    
    def check_fecha(self):
        # Acepta variantes como "15 de abril", "abril 15", etc.
        fecha_variantes = [
            self.fecha_sorteo,
            re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo),  # "15 de abril" -> "abril 15"
        ]
        return any(var in self.text for var in fecha_variantes)

    def check_dia(self):
        return self.dia_de_juego in self.text

    def check_hora(self):
        return self.hora_de_juego in self.text

    def check_premio_mayor(self):
        return self.premio_mayor in self.text

    def check_valor_billete(self):
        return self.valor_billete in self.text

    def check_valor_fraccion(self):
        return self.valor_fraccion in self.text

    def check_serie(self):
        return self.serie in self.text
    
    def check_numero(self):
        return self.numero in self.text

    def run_all_checks(self):
        return {
            "sorteo": self.check_sorteo(),
            "fecha": self.check_fecha(),
            "dia": self.check_dia(),
            "hora": self.check_hora(),
            "premio_mayor": self.check_premio_mayor(),
            "valor_billete": self.check_valor_billete(),
            "valor_fraccion": self.check_valor_fraccion(),
            "serie": self.check_serie(),
            "numero": self.check_numero()
        }
    
    def count_sorteo(self):
        return self.text.count(self.sorteo)

    def count_fecha(self):
        variantes = set([
            self.fecha_sorteo,
            re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo),  # "15 de abril" → "abril 15"
            re.sub(r"(\d{1,2})/(\d{1,2})/(\d{4})", r"\1/\2", self.fecha_sorteo),  # "15/04/2025" → "15/04"
        ])
        return sum(self.text.count(var) for var in variantes if var)

    def count_dia(self):
        return self.text.count(self.dia_de_juego)

    def count_hora(self):
        return self.text.count(self.hora_de_juego)

    def count_premio_mayor(self):
        return self.text.count(self.premio_mayor)

    def count_valor_billete(self):
        return self.text.count(self.valor_billete)

    def count_valor_fraccion(self):
        return self.text.count(self.valor_fraccion)

    def count_serie(self):
        return self.text.count(self.serie)
    
    def count_numero(self):
        return self.text.count(self.numero)


    def run_all_counts(self):
        return {
            "sorteo": self.count_sorteo(),
            "fecha": self.count_fecha(),
            "dia": self.count_dia(),
            "hora": self.count_hora(),
            "premio_mayor": self.count_premio_mayor(),
            "valor_billete": self.count_valor_billete(),
            "valor_fraccion": self.count_valor_fraccion(),
            "serie": self.count_serie(),
            "numero": self.count_numero()
        }
        

def validar_logo_cruz_roja_por_texto(
    img_pil: Image.Image, 
    region: str = "us-east-1", 
    min_conf: float = 80.0
) -> Dict:
    """
    Usa Rekognition DetectText para confirmar la presencia de 'Cruz Roja Colombiana'.
    Devuelve: {'found': bool, 'boxes_norm': [bboxes], 'raw': respuesta_rekognition}
    """
    srv = RekognitionService(region_name=region)
    image_bytes = srv._pil_to_bytes(img_pil)
    res = srv.find_cruz_roja_by_text(image_bytes, min_conf=min_conf)
    return {"found": res["found"], "boxes_norm": res["boxes"], "raw": res["raw"]}

def localizar_logo_por_template(
    ticket_img: Image.Image, 
    logo_img: Image.Image, 
    threshold: float = 0.78
) -> List[Tuple[int,int,int,int]]:
    """
    Fallback local para ubicar el logo. Si OpenCV no está disponible, retorna [].
    """
    srv = RekognitionService()
    return srv.template_match_logo(ticket_img, logo_img, threshold=threshold)

def validar_logo_cruz_roja_por_palabras(
    img_pil: Image.Image,
    region: str = "us-east-1",
    min_conf: float = 70.0,
    gap_px: int = 160,
    y_tol: float = 0.12
) -> Dict:
    srv = RekognitionService(region_name=region)
    res = srv.find_phrase_by_words(
        srv._pil_to_bytes(img_pil),
        target_words=("cruz","roja","colombiana"),
        min_conf=min_conf,
        word_gap_px=gap_px,
        y_tol=y_tol
    )
    return res
