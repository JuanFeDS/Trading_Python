"""Barrido de SL/TP en M1 para las estrategias mas prometedoras, apuntando a duracion de operacion corta.

Incluye el spread real del simbolo como costo por operacion -- con SL/TP
de pocos pips el spread deja de ser despreciable.
"""

import sys
from datetime import datetime, timedelta, timezone
from itertools import product

from dotenv import load_dotenv
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding="utf-8")

from backtest.datos_historicos import obtener_velas_historicas
from backtest.motor_backtest import correr_backtest
from config.settings import ConfiguracionMetaTrader
from execution.mt5_client import tamano_pip
from strategy.bollinger_bands import EstrategiaBandasBollinger
from strategy.mean_reversion_adx import EstrategiaMeanReversionADX
from strategy.rsi import EstrategiaRSI

SIMBOLO = "EURUSD.sml"
TIMEFRAME = mt5.TIMEFRAME_M1
MINUTOS_POR_VELA = 1
DIAS_HISTORIAL = 14
OPERACIONES_MINIMAS = 15

COMBINACIONES_SL_TP = [(5, 10), (5, 15), (8, 12), (10, 15), (10, 20)]

ESTRATEGIAS = {
    "bollinger": lambda: EstrategiaBandasBollinger(),
    "rsi": lambda: EstrategiaRSI(periodo=21, umbral_sobreventa=30, umbral_sobrecompra=70),
    "mean_reversion_adx": lambda: EstrategiaMeanReversionADX(umbral_adx_rango=30, umbral_rsi_sobreventa=25),
}


def _iniciar_conexion(configuracion: ConfiguracionMetaTrader) -> None:
    argumentos = {
        "login": configuracion.login,
        "password": configuracion.password,
        "server": configuracion.server,
    }
    if configuracion.ruta_terminal:
        argumentos["path"] = configuracion.ruta_terminal

    if not mt5.initialize(**argumentos):
        raise RuntimeError(f"No se pudo conectar a MT5: {mt5.last_error()}")


def ejecutar():
    load_dotenv()
    configuracion = ConfiguracionMetaTrader()
    _iniciar_conexion(configuracion)

    info_simbolo = mt5.symbol_info(SIMBOLO)
    tick = mt5.symbol_info_tick(SIMBOLO)
    if info_simbolo is None or tick is None:
        raise RuntimeError(f"No hay informacion disponible para {SIMBOLO}")
    pip = tamano_pip(info_simbolo)
    spread_pips = (tick.ask - tick.bid) / pip

    hasta = datetime.now(timezone.utc)
    desde = hasta - timedelta(days=DIAS_HISTORIAL)
    velas = obtener_velas_historicas(SIMBOLO, TIMEFRAME, desde, hasta)
    print(f"📊 {len(velas)} velas M1 de {SIMBOLO} ({DIAS_HISTORIAL} dias) — spread actual: {spread_pips:.2f} pips")

    for nombre, fabrica in ESTRATEGIAS.items():
        print()
        print(f"=== {nombre} ===")
        resultados = []
        for distancia_sl_pips, distancia_tp_pips in COMBINACIONES_SL_TP:
            estrategia = fabrica()
            resultado = correr_backtest(
                estrategia, velas, pip, distancia_sl_pips, distancia_tp_pips, spread_pips=spread_pips
            )
            if resultado.operaciones >= OPERACIONES_MINIMAS:
                resultados.append((distancia_sl_pips, distancia_tp_pips, resultado))

        if not resultados:
            print("  ninguna combinacion alcanzo el minimo de operaciones")
            continue

        resultados.sort(key=lambda item: item[2].pips_totales, reverse=True)
        for sl, tp, resultado in resultados:
            minutos_promedio = resultado.duracion_velas_promedio * MINUTOS_POR_VELA
            print(
                f"  SL={sl} TP={tp} -> operaciones={resultado.operaciones} "
                f"acierto={resultado.tasa_acierto:.1%} pips={resultado.pips_totales:.1f} "
                f"duracion_prom={minutos_promedio:.1f}min"
            )

    mt5.shutdown()


if __name__ == "__main__":
    ejecutar()
