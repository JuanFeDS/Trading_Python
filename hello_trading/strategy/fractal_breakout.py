"""Fractales de Bill Williams + ruptura de estructura de mercado.

Un fractal alcista en la vela i requiere que su high sea el maximo de las
5 velas centradas en i (i-2..i+2); solo se confirma 2 velas despues, para
no introducir look-ahead bias en el backtest (no se puede operar sobre un
fractal antes de que exista la confirmacion). Se guarda el ultimo fractal
alcista confirmado como resistencia y el ultimo bajista como soporte.

Entrada: el cierre rompe la resistencia (ultimo fractal alcista confirmado)
con ADX > umbral (confirma regimen tendencial) y la EMA con pendiente
positiva. Cierre: el precio rompe el soporte (ultimo fractal bajista
confirmado) -- actua como stop estructural basado en la ultima estructura
de mercado, no en una distancia fija. Solo opera en largo.

No implementa deteccion de HH/HL/LL/LH como regimen explicito ni metricas
cuantitativas del fractal (retests, edad, fuerza de ruptura) -- eso queda
para una iteracion futura si esta estrategia sobrevive el backtest inicial.
"""

from strategy import indicadores


class EstrategiaFractalBreakout:
    """Genera senales de entrada/salida por ruptura del ultimo fractal confirmado."""

    REQUIERE_VELAS = True
    NOMBRE = "fractal_breakout"

    def __init__(self, periodo_ema: int = 50, periodo_adx: int = 14, umbral_adx: float = 20, velas_pendiente: int = 5):
        self.periodo_ema = periodo_ema
        self.periodo_adx = periodo_adx
        self.umbral_adx = umbral_adx
        self.velas_pendiente = velas_pendiente

    @staticmethod
    def _fractales_confirmados(velas: list[dict]) -> tuple[float | None, float | None]:
        """Ultima resistencia y ultimo soporte confirmados, buscando desde el final hacia atras
        y deteniendose apenas se encuentran ambos (evita recorrer toda la historia en cada llamada)."""
        resistencia = None
        soporte = None
        # el fractal en el indice i necesita i-2..i+2; el ultimo confirmable es len(velas)-3
        for indice in range(len(velas) - 3, 1, -1):
            if resistencia is not None and soporte is not None:
                break
            ventana = velas[indice - 2 : indice + 3]
            highs = [vela["high"] for vela in ventana]
            lows = [vela["low"] for vela in ventana]
            if resistencia is None and ventana[2]["high"] == max(highs) and highs.count(max(highs)) == 1:
                resistencia = ventana[2]["high"]
            if soporte is None and ventana[2]["low"] == min(lows) and lows.count(min(lows)) == 1:
                soporte = ventana[2]["low"]
        return resistencia, soporte

    def calcular_senal(self, velas: list[dict]) -> str | None:
        minimo_requerido = max(self.periodo_ema + self.velas_pendiente, 2 * self.periodo_adx + 2, 10)
        if len(velas) < minimo_requerido:
            return None

        resistencia, soporte = self._fractales_confirmados(velas)
        if resistencia is None or soporte is None:
            return None

        cierres = [vela["close"] for vela in velas]
        cierre_actual = cierres[-1]

        ema_actual = indicadores.ema(cierres, self.periodo_ema)
        ema_previa = indicadores.ema(cierres[: -self.velas_pendiente], self.periodo_ema)
        adx_actual = indicadores.adx(velas, self.periodo_adx)

        ruptura_alcista = cierre_actual > resistencia
        tendencia_confirmada = adx_actual > self.umbral_adx and ema_actual > ema_previa

        if ruptura_alcista and tendencia_confirmada:
            return "comprar"
        if cierre_actual < soporte:
            return "cerrar"
        return None
