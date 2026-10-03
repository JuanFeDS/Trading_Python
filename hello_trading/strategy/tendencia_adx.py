"""Trend following condicionado por regimen (EMA + ADX + pullback + RSI).

Regimen tendencial: ADX > umbral y la EMA lenta tiene pendiente (no esta
plana). Entrada: EMA rapida > EMA lenta (tendencia alcista) + el precio
retrocede hasta tocar la EMA rapida + el RSI recupera sobre 50 (confirma
que el retroceso ya termino). Cierre: la EMA rapida cruza por debajo de
la EMA lenta (se pierde la estructura de tendencia). Solo opera en largo.
"""

from strategy import indicadores


class EstrategiaTendenciaADX:
    """Genera senales de entrada/salida siguiendo tendencia, filtradas por ADX."""

    REQUIERE_VELAS = True
    NOMBRE = "tendencia_adx"

    def __init__(
        self,
        periodo_ema_rapida: int = 20,
        periodo_ema_lenta: int = 50,
        periodo_adx: int = 14,
        periodo_rsi: int = 14,
        umbral_adx: float = 25,
        tolerancia_pullback: float = 0.001,
        velas_pendiente: int = 5,
    ):
        self.periodo_ema_rapida = periodo_ema_rapida
        self.periodo_ema_lenta = periodo_ema_lenta
        self.periodo_adx = periodo_adx
        self.periodo_rsi = periodo_rsi
        self.umbral_adx = umbral_adx
        self.tolerancia_pullback = tolerancia_pullback
        self.velas_pendiente = velas_pendiente

    def calcular_senal(self, velas: list[dict]) -> str | None:
        minimo_requerido = max(
            self.periodo_ema_lenta + self.velas_pendiente, 2 * self.periodo_adx + 2, self.periodo_rsi + 2
        )
        if len(velas) < minimo_requerido:
            return None

        cierres = [vela["close"] for vela in velas]

        ema_rapida_actual = indicadores.ema(cierres, self.periodo_ema_rapida)
        ema_lenta_actual = indicadores.ema(cierres, self.periodo_ema_lenta)
        ema_lenta_previa = indicadores.ema(cierres[: -self.velas_pendiente], self.periodo_ema_lenta)

        adx_actual = indicadores.adx(velas, self.periodo_adx)

        rsi_actual = indicadores.rsi(cierres, self.periodo_rsi)
        rsi_previo = indicadores.rsi(cierres[:-1], self.periodo_rsi)

        cierre_actual = cierres[-1]

        tendencia_alcista = ema_rapida_actual > ema_lenta_actual
        regimen_tendencial = adx_actual > self.umbral_adx and ema_lenta_actual != ema_lenta_previa
        pullback_hacia_ema = abs(cierre_actual - ema_rapida_actual) / cierre_actual < self.tolerancia_pullback
        rsi_recupera_50 = rsi_previo <= 50 < rsi_actual

        if regimen_tendencial and tendencia_alcista and pullback_hacia_ema and rsi_recupera_50:
            return "comprar"
        if ema_rapida_actual < ema_lenta_actual:
            return "cerrar"
        return None
