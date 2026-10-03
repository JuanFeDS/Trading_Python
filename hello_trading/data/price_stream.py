"""Obtencion de precios en tiempo real desde el terminal MetaTrader 5 (via sondeo)."""

import time
from collections.abc import Iterator

import MetaTrader5 as mt5


class FlujoPrecios:
    """Sondea el terminal MT5 y emite un tick cada vez que cambia el precio de un simbolo."""

    def __init__(self, simbolos: list[str], intervalo_segundos: float = 1.0):
        self.simbolos = simbolos
        self.intervalo_segundos = intervalo_segundos

    def escuchar(self) -> Iterator[dict]:
        for simbolo in self.simbolos:
            if not mt5.symbol_select(simbolo, True):
                raise RuntimeError(f"No se pudo habilitar el simbolo {simbolo}")

        ultimo_tick_por_simbolo = {}

        while True:
            for simbolo in self.simbolos:
                tick = mt5.symbol_info_tick(simbolo)
                if tick is None or ultimo_tick_por_simbolo.get(simbolo) == tick.time_msc:
                    continue
                ultimo_tick_por_simbolo[simbolo] = tick.time_msc
                yield {
                    "simbolo": simbolo,
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "hora_msc": tick.time_msc,
                }
            time.sleep(self.intervalo_segundos)
