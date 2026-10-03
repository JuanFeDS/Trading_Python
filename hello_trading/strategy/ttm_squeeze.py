"""TTM Squeeze: compresion de volatilidad (Bollinger dentro de Keltner) seguida de breakout.

Hipotesis: cuando las Bandas de Bollinger quedan comprimidas dentro del
Canal de Keltner (squeeze activo), la volatilidad esta anormalmente baja
y suele preceder a un movimiento direccional.

Regla: el squeeze estaba activo y se libera (deja de estarlo) con
momentum positivo (cierre por encima de su EMA) -> 'comprar'. Se cierra
si el squeeze se reactiva o el momentum se vuelve negativo. Solo largo.

Fuente: John Carter (Simpler Trading), popularizado en la practica de
trading. Sin papers academicos que lo respalden -- evidencia de
industria, no cuantitativa formal. Es la idea de "Volatility Compression"
con una regla concreta (BB vs Keltner) en vez del ATR-percentile
propuesto originalmente.
"""

from strategy import indicadores


class EstrategiaTTMSqueeze:
    """Genera senales de entrada/salida a partir de la liberacion del squeeze de volatilidad."""

    REQUIERE_VELAS = True
    NOMBRE = "ttm_squeeze"

    def __init__(self, periodo: int = 20, desviaciones_bb: float = 2.0, multiplicador_kc: float = 1.5):
        self.periodo = periodo
        self.desviaciones_bb = desviaciones_bb
        self.multiplicador_kc = multiplicador_kc

    def _squeeze_activo(self, velas: list[dict], cierres: list[float]) -> bool:
        banda_inferior, _, banda_superior = indicadores.bandas_bollinger(cierres, self.periodo, self.desviaciones_bb)
        ema_central = indicadores.ema(cierres, self.periodo)
        rango_medio = indicadores.atr(velas, self.periodo)
        canal_inferior = ema_central - self.multiplicador_kc * rango_medio
        canal_superior = ema_central + self.multiplicador_kc * rango_medio
        return banda_superior < canal_superior and banda_inferior > canal_inferior

    def calcular_senal(self, velas: list[dict]) -> str | None:
        minimo_requerido = self.periodo + 3
        if len(velas) < minimo_requerido:
            return None

        cierres = [vela["close"] for vela in velas]

        squeeze_actual = self._squeeze_activo(velas, cierres)
        squeeze_previo = self._squeeze_activo(velas[:-1], cierres[:-1])
        squeeze_se_libera = squeeze_previo and not squeeze_actual

        momentum_actual = cierres[-1] - indicadores.ema(cierres, self.periodo)

        if squeeze_se_libera and momentum_actual > 0:
            return "comprar"
        if squeeze_actual or momentum_actual < 0:
            return "cerrar"
        return None
