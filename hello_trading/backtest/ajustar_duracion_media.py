"""Barrido en M5 (parametros de estrategia + SL/TP mas chico) apuntando a 30-60 min por operacion.

M5 tiene menos ruido relativo que M1 y el spread pesa menos frente a un
SL/TP de 8-30 pips (vs. 5-10 en el intento de scalping en M1).
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
TIMEFRAME = mt5.TIMEFRAME_M5
MINUTOS_POR_VELA = 5
DIAS_HISTORIAL = 30
OPERACIONES_MINIMAS = 15
DURACION_OBJETIVO_MIN_MIN = 30
DURACION_OBJETIVO_MIN_MAX = 60
TOP_N = 5

COMBINACIONES_SL_TP = [(8, 16), (10, 15), (10, 20), (12, 18), (15, 25), (15, 30)]

GRILLAS = {
    "bollinger": (
        EstrategiaBandasBollinger,
        {"periodo": [14, 20, 30], "desviaciones": [1.5, 2.0, 2.5]},
    ),
    "rsi": (
        EstrategiaRSI,
        {"periodo": [10, 14, 21], "umbral_sobreventa": [20, 30], "umbral_sobrecompra": [70, 80]},
    ),
    "mean_reversion_adx": (
        EstrategiaMeanReversionADX,
        {"umbral_adx_rango": [15, 20, 25, 30], "umbral_rsi_sobreventa": [20, 25, 30]},
    ),
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
    print(f"📊 {len(velas)} velas M5 de {SIMBOLO} ({DIAS_HISTORIAL} dias) — spread: {spread_pips:.2f} pips")
    print(f"   (minimo {OPERACIONES_MINIMAS} operaciones, objetivo de duracion {DURACION_OBJETIVO_MIN_MIN}-{DURACION_OBJETIVO_MIN_MAX}min)")

    for nombre, (fabrica, grilla) in GRILLAS.items():
        nombres_parametros = list(grilla.keys())
        combinaciones_parametros = list(product(*grilla.values()))

        resultados = []
        for valores in combinaciones_parametros:
            parametros = dict(zip(nombres_parametros, valores))
            for distancia_sl_pips, distancia_tp_pips in COMBINACIONES_SL_TP:
                estrategia = fabrica(**parametros)
                resultado = correr_backtest(
                    estrategia, velas, pip, distancia_sl_pips, distancia_tp_pips, spread_pips=spread_pips
                )
                if resultado.operaciones >= OPERACIONES_MINIMAS:
                    resultados.append((parametros, distancia_sl_pips, distancia_tp_pips, resultado))

        print()
        print(f"=== {nombre} ({len(resultados)} combinaciones validas) ===")
        if not resultados:
            print("  ninguna combinacion alcanzo el minimo de operaciones")
            continue

        resultados.sort(key=lambda item: item[3].pips_totales, reverse=True)
        for parametros, sl, tp, resultado in resultados[:TOP_N]:
            minutos_promedio = resultado.duracion_velas_promedio * MINUTOS_POR_VELA
            dentro_de_objetivo = DURACION_OBJETIVO_MIN_MIN <= minutos_promedio <= DURACION_OBJETIVO_MIN_MAX
            marca = "✅" if dentro_de_objetivo else "  "
            print(
                f"  {marca} {parametros} SL={sl} TP={tp} -> operaciones={resultado.operaciones} "
                f"acierto={resultado.tasa_acierto:.1%} pips={resultado.pips_totales:.1f} "
                f"duracion_prom={minutos_promedio:.1f}min"
            )

    mt5.shutdown()


if __name__ == "__main__":
    ejecutar()
