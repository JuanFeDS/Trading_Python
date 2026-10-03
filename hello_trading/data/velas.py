"""Fuente de velas cerradas en vivo desde MT5, con deteccion de vela nueva."""

import MetaTrader5 as mt5


class FuenteVelasVivo:
    """Entrega las velas cerradas (OHLC) solo cuando aparece una vela nueva.

    En el arranque en frio (primera llamada) fija el estado en la ultima
    vela cerrada sin devolver nada, para que el llamador no evalue una
    senal contra un cruce que ya paso hace rato en el historial.
    """

    def __init__(self, simbolo: str, timeframe: int, velas_historial: int = 200):
        self.simbolo = simbolo
        self.timeframe = timeframe
        self.velas_historial = velas_historial
        self._hora_ultima_vela_evaluada = None

    def obtener_velas_si_hay_vela_nueva(self) -> list[dict] | None:
        if not mt5.symbol_select(self.simbolo, True):
            raise RuntimeError(f"No se pudo habilitar el simbolo {self.simbolo}")

        velas = mt5.copy_rates_from_pos(self.simbolo, self.timeframe, 0, self.velas_historial)
        if velas is None or len(velas) < 2:
            return None

        velas_cerradas = velas[:-1]
        hora_ultima_vela_cerrada = velas_cerradas[-1]["time"]

        if self._hora_ultima_vela_evaluada is None:
            self._hora_ultima_vela_evaluada = hora_ultima_vela_cerrada
            return None

        if hora_ultima_vela_cerrada == self._hora_ultima_vela_evaluada:
            return None

        self._hora_ultima_vela_evaluada = hora_ultima_vela_cerrada
        return [
            {
                "time": vela["time"],
                "open": vela["open"],
                "high": vela["high"],
                "low": vela["low"],
                "close": vela["close"],
            }
            for vela in velas_cerradas
        ]
