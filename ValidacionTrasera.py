import re
import unicodedata
from typing import Dict, Set

class ValidacionTrasera:
    """
    Validaciones para la cara TRASERA de la FT:
      - Campos típicos: fecha, sorteo, valor_billete, valor_fraccion,
                        premio_mayor, total_plan_premios, series
      - Búsquedas 'fuzzy' (insensible a tildes/mayús/saltos).
      - Números flexibles: $, miles con . , espacio; decimales opcionales;
        palabras como millón/millones.
    """

    def __init__(self, raw_text: str,
                 fecha_sorteo: str, sorteo: str,
                 valor_billete: str, valor_fraccion: str,
                 premio_mayor: str, total_plan_premios: str,
                 series: str,
                 checks_enabled: Set[str] = None):
        self.raw_text = raw_text or ""
        self.text = self._preprocesar(self.raw_text)
        self.text_noacc = self._strip_accents(self.text)

        # inputs (normalizados)
        self.fecha_sorteo = (fecha_sorteo or "").lower().strip()
        self.sorteo = (sorteo or "").lower().strip()
        self.valor_billete = (valor_billete or "").lower().strip()
        self.valor_fraccion = (valor_fraccion or "").lower().strip()
        self.premio_mayor = (premio_mayor or "").lower().strip()
        self.total_plan_premios = (total_plan_premios or "").lower().strip()
        self.series = (series or "").lower().strip()

        self.checks_enabled = set(checks_enabled) if checks_enabled else {
            "fecha","sorteo","valor_billete","valor_fraccion",
            "premio_mayor","total_plan_premios","series"
        }

    # ---------- utils ----------
    @staticmethod
    def _strip_accents(s: str) -> str:
        if not s: return ""
        return ''.join(c for c in unicodedata.normalize('NFD', s)
                       if unicodedata.category(c) != 'Mn')

    @staticmethod
    def _preprocesar(texto: str) -> str:
        texto = (texto or "").lower().replace("\n", " ")
        return re.sub(r"\s+", " ", texto).strip()

    def _contains_fuzzy(self, phrase: str) -> bool:
        phrase = (phrase or "").strip()
        if not phrase: return False
        patt = re.sub(r"\s+", r"\\s+", re.escape(phrase))
        if re.search(patt, self.text, flags=re.IGNORECASE): return True
        patt_noacc = re.sub(r"\s+", r"\\s+", re.escape(self._strip_accents(phrase)))
        return re.search(patt_noacc, self.text_noacc, flags=re.IGNORECASE) is not None

    def _count_fuzzy(self, phrase: str) -> int:
        phrase = (phrase or "").strip()
        if not phrase: return 0
        patt = re.sub(r"\s+", r"\\s+", re.escape(phrase))
        c1 = len(re.findall(patt, self.text, flags=re.IGNORECASE))
        patt_noacc = re.sub(r"\s+", r"\\s+", re.escape(self._strip_accents(phrase)))
        c2 = len(re.findall(patt_noacc, self.text_noacc, flags=re.IGNORECASE))
        return max(c1, c2)

    def _num_regex_from_value(self, value: str) -> re.Pattern:
        v = (value or "").lower().strip()
        if not v:
            return re.compile(r"(?!)")
        digits = ''.join(ch for ch in v if ch.isdigit())
        if not digits:
            patt = re.sub(r"\s+", r"\\s+", re.escape(v))
            return re.compile(patt, flags=re.IGNORECASE)

        # miles con separadores opcionales
        groups = []
        g = digits
        while len(g) > 3:
            groups.append(g[-3:])
            g = g[:-3]
        groups.append(g)
        groups = list(reversed(groups))
        sep = r"[.,\s]"
        grouped = groups[0] + ''.join(fr"{sep}?{gr}" for gr in groups[1:])
        number_core = fr"(?:{grouped}|{digits})"
        decimals = r"(?:[.,]\d{1,3})?"
        money = r"\$?\s*"

        has_millon = any(w in v for w in ["millon", "millón", "millones"])
        millon_word = r"(?:\s*(?:millon(?:es)?|millón(?:es)?))?" if has_millon else ""

        return re.compile(fr"\b{money}{number_core}{decimals}{millon_word}\b", flags=re.IGNORECASE)

    def _check_number_like(self, value: str) -> bool:
        patt = self._num_regex_from_value(value)
        return re.search(patt, self.text) is not None or re.search(patt, self.text_noacc) is not None

    def _count_number_like(self, value: str) -> int:
        patt = self._num_regex_from_value(value)
        return max(len(re.findall(patt, self.text)), len(re.findall(patt, self.text_noacc)))

    # ---------- checks ----------
    def check_fecha(self):
        variantes = [self.fecha_sorteo,
                     re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo)]
        return any(v in self.text for v in variantes)

    def check_sorteo(self) -> bool:
        # número de sorteo puede venir junto a palabra "sorteo"
        if not self.sorteo: return False
        return self._contains_fuzzy(self.sorteo) or self._contains_fuzzy(f"sorteo {self.sorteo}")

    def check_valor_billete(self) -> bool:
        return self._check_number_like(self.valor_billete)

    def check_valor_fraccion(self) -> bool:
        return self._check_number_like(self.valor_fraccion)

    def check_premio_mayor(self) -> bool:
        return self._check_number_like(self.premio_mayor)

    def check_total_plan_premios(self) -> bool:
        # “TOTAL PLAN PREMIOS 14.400.000.000”
        # acepta que el valor esté separado por saltos/espacios
        return self._check_number_like(self.total_plan_premios)

    def check_series(self) -> bool:
        # “SERIES 300” o "series: 300"
        if not self.series: return False
        return self._contains_fuzzy(self.series) or self._contains_fuzzy(f"series {self.series}")

    def run_all_checks(self) -> Dict[str, bool]:
        checks = {
            "fecha": self.check_fecha,
            "sorteo": self.check_sorteo,
            "valor_billete": self.check_valor_billete,
            "valor_fraccion": self.check_valor_fraccion,
            "premio_mayor": self.check_premio_mayor,
            "total_plan_premios": self.check_total_plan_premios,
            "series": self.check_series,
        }
        return {k: fn() for k, fn in checks.items() if k in self.checks_enabled}

    # ---------- conteos ----------
    def count_fecha(self):
        variantes = {self.fecha_sorteo,
                     re.sub(r"(\d{1,2}) de (\w+)", r"\2 \1", self.fecha_sorteo),
                     re.sub(r"(\d{1,2})/(\d{1,2})/(\d{4})", r"\1/\2", self.fecha_sorteo)}
        return sum(self.text.count(v) for v in variantes if v)

    def count_sorteo(self) -> int:
        if not self.sorteo: return 0
        return max(
            self._count_fuzzy(self.sorteo),
            self._count_fuzzy(f"sorteo {self.sorteo}")
        )

    def count_valor_billete(self) -> int:
        return self._count_number_like(self.valor_billete)

    def count_valor_fraccion(self) -> int:
        return self._count_number_like(self.valor_fraccion)

    def count_premio_mayor(self) -> int:
        return self._count_number_like(self.premio_mayor)

    def count_total_plan_premios(self) -> int:
        return self._count_number_like(self.total_plan_premios)

    def count_series(self) -> int:
        if not self.series: return 0
        return max(
            self._count_fuzzy(self.series),
            self._count_fuzzy(f"series {self.series}")
        )

    def run_all_counts(self) -> Dict[str, int]:
        counts = {
            "fecha": self.count_fecha,
            "sorteo": self.count_sorteo,
            "valor_billete": self.count_valor_billete,
            "valor_fraccion": self.count_valor_fraccion,
            "premio_mayor": self.count_premio_mayor,
            "total_plan_premios": self.count_total_plan_premios,
            "series": self.count_series,
        }
        return {k: fn() for k, fn in counts.items() if k in self.checks_enabled}