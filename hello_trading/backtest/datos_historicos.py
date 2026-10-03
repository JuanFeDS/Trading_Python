"""Descarga de velas historicas desde MT5 para backtesting."""

from datetime import datetime

import MetaTrader5 as mt5


def obtener_velas_historicas(simbolo: str, timeframe: int, desde: datetime, hasta: datetime) -> list[dict]:
    if not mt5.symbol_select(simbolo, True):
        raise RuntimeError(f"No se pudo habilitar el simbolo {simbolo}")

    velas = mt5.copy_rates_range(simbolo, timeframe, desde, hasta)
    if velas is None or len(velas) == 0:
        raise RuntimeError(f"No se pudo obtener historial para {simbolo}: {mt5.last_error()}")

    return [
        {
            "time": vela["time"],
            "open": vela["open"],
            "high": vela["high"],
            "low": vela["low"],
            "close": vela["close"],
        }
        for vela in velas
    ]
