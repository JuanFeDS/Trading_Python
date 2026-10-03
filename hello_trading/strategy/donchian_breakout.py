"""Estrategia de ruptura de canal de Donchian.

Regla: el canal se calcula con las N velas anteriores a la actual (nunca
incluye la vela que rompe, para no volverse trivial). Si el cierre supera
el maximo del canal -> 'comprar'. Si cae por debajo del minimo del canal
-> 'cerrar'. Solo opera en largo.
"""


class EstrategiaDonchianBreakout:
    """Genera senales de entrada/salida a partir de rupturas del canal de Donchian."""

    REQUIERE_VELAS = True
    NOMBRE = "donchian_breakout"

    def __init__(self, periodo: int = 20):
        self.periodo = periodo

    def calcular_senal(self, velas: list[dict]) -> str | None:
        if len(velas) < self.periodo + 2:
            return None

        canal = velas[-(self.periodo + 1) : -1]
        maximo_canal = max(vela["high"] for vela in canal)
        minimo_canal = min(vela["low"] for vela in canal)

        cierre_actual = velas[-1]["close"]

        if cierre_actual > maximo_canal:
            return "comprar"
        if cierre_actual < minimo_canal:
            return "cerrar"
        return None
