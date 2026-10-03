"""Estrategia de Bandas de Bollinger (reversion a la media).

Regla: comprar en el rebote desde la banda inferior (el cierre estaba en
o por debajo de la banda inferior y el siguiente cierre vuelve a estar
por encima); cerrar cuando el precio toca o supera la banda superior.
Solo opera en largo.
"""


class EstrategiaBandasBollinger:
    """Genera senales de entrada/salida a partir de bandas de Bollinger sobre el cierre."""

    NOMBRE = "bollinger"

    def __init__(self, periodo: int = 20, desviaciones: float = 2.0):
        self.periodo = periodo
        self.desviaciones = desviaciones

    def _bandas(self, cierres: list[float]) -> tuple[float, float]:
        ventana = cierres[-self.periodo:]
        media = sum(ventana) / self.periodo
        varianza = sum((cierre - media) ** 2 for cierre in ventana) / self.periodo
        desviacion_estandar = varianza**0.5
        banda_inferior = media - self.desviaciones * desviacion_estandar
        banda_superior = media + self.desviaciones * desviacion_estandar
        return banda_inferior, banda_superior

    def calcular_senal(self, cierres: list[float]) -> str | None:
        if len(cierres) < self.periodo + 1:
            return None

        banda_inferior_previa, _ = self._bandas(cierres[:-1])
        banda_inferior_actual, banda_superior_actual = self._bandas(cierres)

        cierre_previo = cierres[-2]
        cierre_actual = cierres[-1]

        rebote_desde_banda_inferior = cierre_previo <= banda_inferior_previa and cierre_actual > banda_inferior_actual
        toca_banda_superior = cierre_actual >= banda_superior_actual

        if rebote_desde_banda_inferior:
            return "comprar"
        if toca_banda_superior:
            return "cerrar"
        return None
