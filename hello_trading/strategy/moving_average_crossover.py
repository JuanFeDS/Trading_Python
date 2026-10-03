"""Estrategia de cruce de medias moviles simples (SMA rapida vs SMA lenta).

Regla: cruce alcista (SMA rapida supera a la SMA lenta en el ultimo cierre)
genera senal de 'comprar'; cruce bajista genera senal de 'cerrar'. Solo
opera en largo. Estrategia pura: decide a partir de la lista de cierres
que recibe, sin acceder a MT5 ni guardar estado entre llamadas — el
manejo de "vela nueva" y arranque en frio vive en data.velas.FuenteVelasVivo
(para vivo) o en el motor de backtest (para historico).
"""


class EstrategiaCruceMedias:
    """Genera senales de entrada/salida a partir del cruce de dos SMA."""

    NOMBRE = "cruce_medias"

    def __init__(self, periodo_rapido: int = 9, periodo_lento: int = 21):
        self.periodo_rapido = periodo_rapido
        self.periodo_lento = periodo_lento

    @staticmethod
    def _sma(cierres: list[float], periodo: int) -> float:
        return sum(cierres[-periodo:]) / periodo

    def calcular_senal(self, cierres: list[float]) -> str | None:
        if len(cierres) < self.periodo_lento + 1:
            return None

        sma_rapida_actual = self._sma(cierres, self.periodo_rapido)
        sma_lenta_actual = self._sma(cierres, self.periodo_lento)
        sma_rapida_previa = self._sma(cierres[:-1], self.periodo_rapido)
        sma_lenta_previa = self._sma(cierres[:-1], self.periodo_lento)

        cruce_alcista = sma_rapida_previa <= sma_lenta_previa and sma_rapida_actual > sma_lenta_actual
        cruce_bajista = sma_rapida_previa >= sma_lenta_previa and sma_rapida_actual < sma_lenta_actual

        if cruce_alcista:
            return "comprar"
        if cruce_bajista:
            return "cerrar"
        return None
