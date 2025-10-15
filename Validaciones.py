import re
import unicodedata
from typing import Dict, Set

class Validaciones:
    """
    Validaciones de texto para Fichas Técnicas:
      - Búsquedas "fuzzy" tolerantes a mayúsculas/minúsculas, tildes y saltos de línea.
      - Números flexibles: acepta $ opcional, separadores (., espacio, ,) y decimales.
      - Selección de checks a ejecutar mediante `checks_enabled`.
    """

    def __init__(self, raw_text: str, sorteo: str, fecha_sorteo: str, dia_de_juego: str,
                 hora_de_juego: str, premio_mayor: str, valor_billete: str,
                 valor_fraccion: str, serie: str, numero: str,
                 checks_enabled: Set[str] = None):
        # Texto base
        self.raw_text = raw_text or ""
        self.text = self._preprocesar(self.raw_text)     # minúsculas + sin saltos (colapsados)
        self.text_noacc = self._strip_accents(self.text) # versión sin acentos (para matching robusto)

        # (opcional, útil si quisieras comparar dígito a dígito sin separadores)
        self.text_digits_soft = re.sub(r'(?<=\d)[\s.,](?=\d)', '', self.text)

        # Entradas normalizadas (minúsculas/strip)
        self.sorteo         = (sorteo or "").lower().strip()
        self.fecha_sorteo   = (fecha_sorteo or "").lower().strip()
        self.dia_de_juego   = (dia_de_juego or "").lower().strip()
        self.hora_de_juego  = (hora_de_juego or "").lower().strip()
        self.premio_mayor   = (premio_mayor or "").lower().strip()
        self.valor_billete  = (valor_billete or "").lower().strip()
        self.valor_fraccion = (valor_fraccion or "").lower().strip()
        self.serie          = (serie or "").lower().strip()
        self.numero         = (numero or "").lower().strip()

        # Checks activos (por defecto, todos)
        self.checks_enabled = set(checks_enabled) if checks_enabled else {
            "sorteo","fecha","dia","hora",
            "premio_mayor","valor_billete","valor_fraccion",
            "serie","numero"
        }

    # ------------------ Utils de normalización/matching ------------------

    @staticmethod
    def _strip_accents(s: str) -> str:
        """Quita tildes/diacríticos: á->a, é->e, ñ->n (no cambia case)."""
        if not s:
            return ""
        return ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        )

    def _preprocesar(self, texto: str) -> str:
        """Minúsculas, reemplaza saltos de línea por espacio y colapsa espacios."""
        texto = (texto or "").lower().replace("\n", " ")
        return re.sub(r"\s+", " ", texto).strip()

    def _contains_fuzzy(self, phrase: str) -> bool:
        """
        Busca 'phrase' permitiendo cualquier cantidad de espacios/saltos entre palabras,
        e ignorando mayúsculas/minúsculas y acentos.
        """
        phrase = (phrase or "").strip()
        if not phrase:
            return False

        # patrón tolerante a espacios/saltos
        patt = re.sub(r"\s+", r"\\s+", re.escape(phrase))
        if re.search(patt, self.text, flags=re.IGNORECASE):
            return True

        # prueba en la versión sin acentos
        patt_noacc = re.sub(r"\s+", r"\\s+", re.escape(self._strip_accents(phrase)))
        return re.search(patt_noacc, self.text_noacc, flags=re.IGNORECASE) is not None

    def _count_fuzzy(self, phrase: str) -> int:
        """Cuenta ocurrencias ‘fuzzy’ (ver arriba) en texto normal y sin acentos."""
        phrase = (phrase or "").strip()
        if not phrase:
            return 0

        patt = re.sub(r"\s+", r"\\s+", re.escape(phrase))
        c1 = len(re.findall(patt, self.text, flags=re.IGNORECASE))

        patt_noacc = re.sub(r"\s+", r"\\s+", re.escape(self._strip_accents(phrase)))
        c2 = len(re.findall(patt_noacc, self.text_noacc, flags=re.IGNORECASE))

        return max(c1, c2)

    def _num_regex_from_value(self, value: str) -> re.Pattern:
        """
        Dado un valor numérico como texto (p. ej. "$12.000", "2,333 millones", "1.549.333.333"):
          - $ opcional
          - separadores de miles con punto/coma/espacio (mezclables)
          - decimales opcionales (.,)
          - tolera 'millon/millón/millones' (si aparecen en el valor)
        """
        v = (value or "").lower().strip()
        if not v:
            return re.compile(r"(?!)")  # patrón imposible

        digits = ''.join(ch for ch in v if ch.isdigit())
        if not digits:
            # sin dígitos: cae a búsqueda fuzzy literal (insensible a espacios/accentos)
            patt = re.sub(r"\s+", r"\\s+", re.escape(v))
            return re.compile(patt, flags=re.IGNORECASE)

        # Construye patrón con separadores opcionales entre miles
        groups = []
        g = digits
        while len(g) > 3:
            groups.append(g[-3:])
            g = g[:-3]
        groups.append(g)
        groups = list(reversed(groups))

        sep = r"[.,\s]"  # separador aceptado
        grouped = groups[0] + ''.join(fr"{sep}?{gr}" for gr in groups[1:])
        number_core = fr"(?:{grouped}|{digits})"  # acepta con o sin separadores
        decimals = r"(?:[.,]\d{1,3})?"            # decimales opcionales
        money = r"\$?\s*"                         # símbolo $ opcional

        # Si el usuario incluyó “millon/millón/millones” en el valor, lo modelamos
        has_millon = any(w in v for w in ["millon", "millón", "millones"])
        # palabra opcional, tolerante a singular/plural y acento
        millon_word = r"(?:\s*(?:millon(?:es)?|millón(?:es)?))?" if has_millon else ""

        pattern = fr"\b{money}{number_core}{decimals}{millon_word}\b"
        return re.compile(pattern, flags=re.IGNORECASE)

    def _check_number_like(self, value: str) -> bool:
        patt = self._num_regex_from_value(value)
        return re.search(patt, self.text) is not None or re.search(patt, self.text_noacc) is not None

    def _count_number_like(self, value: str) -> int:
        patt = self._num_regex_from_value(value)
        return max(len(re.findall(patt, self.text)), len(re.findall(patt, self.text_noacc)))

    # ------------------ Checks ------------------

    def check_sorteo(self) -> bool:
        return self._contains_fuzzy(self.sorteo)

    def check_fecha(self):
        variantes = [self.fecha_sorteo,
                     re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo)]
        return any(v in self.text for v in variantes)

    def check_dia(self) -> bool:
        return self._contains_fuzzy(self.dia_de_juego)

    def check_hora(self) -> bool:
        return self.hora_de_juego in self.text

    def check_premio_mayor(self) -> bool:
        return self._check_number_like(self.premio_mayor)

    def check_valor_billete(self) -> bool:
        return self._check_number_like(self.valor_billete)

    def check_valor_fraccion(self) -> bool:
        return self._check_number_like(self.valor_fraccion)

    def check_serie(self) -> bool:
        # serie puede ser alfanumérica o parecer número con separadores
        return self._contains_fuzzy(self.serie) or self._check_number_like(self.serie)

    def check_numero(self) -> bool:
        return self._contains_fuzzy(self.numero) or self._check_number_like(self.numero)

    def run_all_checks(self) -> Dict[str, bool]:
        checks = {
            "sorteo": self.check_sorteo,
            "fecha": self.check_fecha,
            "dia": self.check_dia,
            "hora": self.check_hora,
            "premio_mayor": self.check_premio_mayor,
            "valor_billete": self.check_valor_billete,
            "valor_fraccion": self.check_valor_fraccion,
            "serie": self.check_serie,
            "numero": self.check_numero,
        }
        return {k: fn() for k, fn in checks.items() if k in self.checks_enabled}

    # ------------------ Conteos ------------------

    def count_sorteo(self) -> int:
        return self._count_fuzzy(self.sorteo)

    def count_fecha(self):
        variantes = {self.fecha_sorteo,
                     re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo),
                     re.sub(r"(\d{1,2})/(\d{1,2})/(\d{4})", r"\1/\2", self.fecha_sorteo)}
        return sum(self.text.count(v) for v in variantes if v)

    def count_dia(self) -> int:
        return self._count_fuzzy(self.dia_de_juego)

    def count_hora(self) -> int:
        return self.text.count(self.hora_de_juego)

    def count_premio_mayor(self) -> int:
        return self._count_number_like(self.premio_mayor)

    def count_valor_billete(self) -> int:
        return self._count_number_like(self.valor_billete)

    def count_valor_fraccion(self) -> int:
        return self._count_number_like(self.valor_fraccion)

    def count_serie(self) -> int:
        return max(self._count_fuzzy(self.serie), self._count_number_like(self.serie))

    def count_numero(self) -> int:
        return max(self._count_fuzzy(self.numero), self._count_number_like(self.numero))

    def run_all_counts(self) -> Dict[str, int]:
        counts = {
            "sorteo": self.count_sorteo,
            "fecha": self.count_fecha,
            "dia": self.count_dia,
            "hora": self.count_hora,
            "premio_mayor": self.count_premio_mayor,
            "valor_billete": self.count_valor_billete,
            "valor_fraccion": self.count_valor_fraccion,
            "serie": self.count_serie,
            "numero": self.count_numero,
        }
        return {k: fn() for k, fn in counts.items() if k in self.checks_enabled}