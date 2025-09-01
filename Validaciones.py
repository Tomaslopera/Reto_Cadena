# Validaciones.py
import re

class Validaciones:
    def __init__(self, raw_text: str, sorteo: str, fecha_sorteo: str, dia_de_juego: str,
                 hora_de_juego: str, premio_mayor: str, valor_billete: str,
                 valor_fraccion: str, serie: str, numero: str):
        self.text = self._preprocesar(raw_text)
        self.sorteo = sorteo.lower()
        self.fecha_sorteo = fecha_sorteo.lower()
        self.dia_de_juego = dia_de_juego.lower()
        self.hora_de_juego = self.hora_de_juego = hora_de_juego.lower()
        self.premio_mayor = premio_mayor.lower()
        self.valor_billete = valor_billete.lower()
        self.valor_fraccion = valor_fraccion.lower()
        self.serie = serie.lower()
        self.numero = numero.lower()

    def _preprocesar(self, texto: str) -> str:
        texto = texto.lower().replace("\n", " ")
        return re.sub(r"\s+", " ", texto)

    # Checks
    def check_sorteo(self): return self.sorteo in self.text
    def check_fecha(self):
        variantes = [self.fecha_sorteo,
                     re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo)]
        return any(v in self.text for v in variantes)
    def check_dia(self): return self.dia_de_juego in self.text
    def check_hora(self): return self.hora_de_juego in self.text
    def check_premio_mayor(self): return self.premio_mayor in self.text
    def check_valor_billete(self): return self.valor_billete in self.text
    def check_valor_fraccion(self): return self.valor_fraccion in self.text
    def check_serie(self): return self.serie in self.text
    def check_numero(self): return self.numero in self.text

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
            "numero": self.check_numero(),
        }

    # Conteos
    def count_sorteo(self): return self.text.count(self.sorteo)
    def count_fecha(self):
        variantes = {self.fecha_sorteo,
                     re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo),
                     re.sub(r"(\d{1,2})/(\d{1,2})/(\d{4})", r"\1/\2", self.fecha_sorteo)}
        return sum(self.text.count(v) for v in variantes if v)
    def count_dia(self): return self.text.count(self.dia_de_juego)
    def count_hora(self): return self.text.count(self.hora_de_juego)
    def count_premio_mayor(self): return self.text.count(self.premio_mayor)
    def count_valor_billete(self): return self.text.count(self.valor_billete)
    def count_valor_fraccion(self): return self.text.count(self.valor_fraccion)
    def count_serie(self): return self.text.count(self.serie)
    def count_numero(self): return self.text.count(self.numero)

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
            "numero": self.count_numero(),
        }
