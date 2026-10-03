"""Mean reversion con Bollinger + RSI, filtrado por ADX.

Regla: compra cuando el cierre rompe la banda inferior de Bollinger con
RSI en sobreventa, pero solo si el ADX confirma que el mercado esta en
rango (ADX bajo) -- evita "atrapar cuchillos" durante una tendencia
fuerte. Cierra al volver a tocar la banda media. Solo opera en largo.
"""

from strategy import indicadores


class EstrategiaMeanReversionADX:
    """Genera senales de entrada/salida por reversion a la media, filtradas por ADX."""

    REQUIERE_VELAS = True
    NOMBRE = "mean_reversion_adx"

    def __init__(
        self,
        periodo_bandas: int = 20,
        desviaciones: float = 2.0,
        periodo_rsi: int = 14,
        umbral_rsi_sobreventa: float = 30,
        periodo_adx: int = 14,
        umbral_adx_rango: float = 20,
    ):
        self.periodo_bandas = periodo_bandas
        self.desviaciones = desviaciones
        self.periodo_rsi = periodo_rsi
        self.umbral_rsi_sobreventa = umbral_rsi_sobreventa
        self.periodo_adx = periodo_adx
        self.umbral_adx_rango = umbral_adx_rango

    def calcular_senal(self, velas: list[dict]) -> str | None:
        minimo_requerido = max(self.periodo_bandas, 2 * self.periodo_adx + 2, self.periodo_rsi + 2)
        if len(velas) < minimo_requerido:
            return None

        cierres = [vela["close"] for vela in velas]
        banda_inferior, banda_media, _ = indicadores.bandas_bollinger(cierres, self.periodo_bandas, self.desviaciones)
        rsi_actual = indicadores.rsi(cierres, self.periodo_rsi)
        adx_actual = indicadores.adx(velas, self.periodo_adx)

        cierre_actual = cierres[-1]

        mercado_en_rango = adx_actual < self.umbral_adx_rango
        sobreventa_extrema = cierre_actual < banda_inferior and rsi_actual < self.umbral_rsi_sobreventa

        if sobreventa_extrema and mercado_en_rango:
            return "comprar"
        if cierre_actual >= banda_media:
            return "cerrar"
        return None
