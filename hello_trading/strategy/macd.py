"""Estrategia de MACD (convergencia/divergencia de medias moviles).

Regla: comprar cuando la linea MACD cruza hacia arriba su linea de senal;
cerrar cuando cruza hacia abajo. Solo opera en largo. La EMA se calcula
con la semilla clasica (SMA de los primeros `periodo` valores).
"""


class EstrategiaMACD:
    """Genera senales de entrada/salida a partir del cruce de MACD contra su linea de senal."""

    NOMBRE = "macd"

    def __init__(self, periodo_rapido: int = 12, periodo_lento: int = 26, periodo_senal: int = 9):
        self.periodo_rapido = periodo_rapido
        self.periodo_lento = periodo_lento
        self.periodo_senal = periodo_senal

    @staticmethod
    def _ema_serie(valores: list[float], periodo: int) -> list[float]:
        multiplicador = 2 / (periodo + 1)
        serie = [sum(valores[:periodo]) / periodo]
        for valor in valores[periodo:]:
            serie.append((valor - serie[-1]) * multiplicador + serie[-1])
        return serie

    def calcular_senal(self, cierres: list[float]) -> str | None:
        minimo_requerido = self.periodo_lento + self.periodo_senal + 1
        if len(cierres) < minimo_requerido:
            return None

        ema_rapida = self._ema_serie(cierres, self.periodo_rapido)
        ema_lenta = self._ema_serie(cierres, self.periodo_lento)

        desfase = len(ema_rapida) - len(ema_lenta)
        linea_macd = [rapida - lenta for rapida, lenta in zip(ema_rapida[desfase:], ema_lenta)]

        if len(linea_macd) < self.periodo_senal + 2:
            return None

        linea_senal = self._ema_serie(linea_macd, self.periodo_senal)
        macd_alineado = linea_macd[len(linea_macd) - len(linea_senal):]

        macd_actual, macd_previo = macd_alineado[-1], macd_alineado[-2]
        senal_actual, senal_previa = linea_senal[-1], linea_senal[-2]

        cruce_alcista = macd_previo <= senal_previa and macd_actual > senal_actual
        cruce_bajista = macd_previo >= senal_previa and macd_actual < senal_actual

        if cruce_alcista:
            return "comprar"
        if cruce_bajista:
            return "cerrar"
        return None
