"""Corre un barrido de parametros para cada estrategia del set y muestra el top 3 de cada una."""

import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding="utf-8")

from backtest.barrido import barrer_estrategia
from backtest.datos_historicos import obtener_velas_historicas
from config.settings import ConfiguracionMetaTrader
from execution.mt5_client import tamano_pip
from strategy.bollinger_bands import EstrategiaBandasBollinger
from strategy.donchian_breakout import EstrategiaDonchianBreakout
from strategy.fractal_breakout import EstrategiaFractalBreakout
from strategy.macd import EstrategiaMACD
from strategy.mean_reversion_adx import EstrategiaMeanReversionADX
from strategy.moving_average_crossover import EstrategiaCruceMedias
from strategy.rsi import EstrategiaRSI
from strategy.tendencia_adx import EstrategiaTendenciaADX

SIMBOLO = "EURUSD.sml"
TIMEFRAME = mt5.TIMEFRAME_M5
DIAS_HISTORIAL = 30
DISTANCIA_SL_PIPS = 20
DISTANCIA_TP_PIPS = 40
OPERACIONES_MINIMAS = 15
TOP_N = 3

GRILLAS = {
    "cruce_medias": (
        EstrategiaCruceMedias,
        {"periodo_rapido": [5, 9, 12], "periodo_lento": [21, 34, 50]},
    ),
    "rsi": (
        EstrategiaRSI,
        {"periodo": [10, 14, 21], "umbral_sobreventa": [20, 30], "umbral_sobrecompra": [70, 80]},
    ),
    "bollinger": (
        EstrategiaBandasBollinger,
        {"periodo": [14, 20, 30], "desviaciones": [1.5, 2.0, 2.5]},
    ),
    "macd": (
        EstrategiaMACD,
        {"periodo_rapido": [8, 12, 16], "periodo_lento": [21, 26, 34], "periodo_senal": [9]},
    ),
    "donchian_breakout": (
        EstrategiaDonchianBreakout,
        {"periodo": [10, 20, 40, 80]},
    ),
    "tendencia_adx": (
        EstrategiaTendenciaADX,
        {"umbral_adx": [15, 20, 25], "tolerancia_pullback": [0.001, 0.002, 0.003]},
    ),
    "mean_reversion_adx": (
        EstrategiaMeanReversionADX,
        {"umbral_adx_rango": [15, 20, 25, 30], "umbral_rsi_sobreventa": [20, 25, 30]},
    ),
    "fractal_breakout": (
        EstrategiaFractalBreakout,
        {"umbral_adx": [10, 15, 20], "periodo_ema": [20, 50]},
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
    if info_simbolo is None:
        raise RuntimeError(f"No hay informacion disponible para {SIMBOLO}")
    pip = tamano_pip(info_simbolo)

    hasta = datetime.now(timezone.utc)
    desde = hasta - timedelta(days=DIAS_HISTORIAL)
    velas = obtener_velas_historicas(SIMBOLO, TIMEFRAME, desde, hasta)
    print(f"📊 {len(velas)} velas historicas de {SIMBOLO} ({DIAS_HISTORIAL} dias, M5)")
    print(f"   (filtrando combinaciones con menos de {OPERACIONES_MINIMAS} operaciones)")

    for nombre, (fabrica, grilla) in GRILLAS.items():
        resultados = barrer_estrategia(
            fabrica, grilla, velas, pip, DISTANCIA_SL_PIPS, DISTANCIA_TP_PIPS, OPERACIONES_MINIMAS
        )
        print()
        print(f"=== {nombre} ({len(resultados)} combinaciones validas) ===")
        if not resultados:
            print("  ninguna combinacion alcanzo el minimo de operaciones")
            continue
        for parametros, resultado in resultados[:TOP_N]:
            print(
                f"  {parametros} -> operaciones={resultado.operaciones} "
                f"acierto={resultado.tasa_acierto:.1%} pips={resultado.pips_totales:.1f} "
                f"peor_racha={resultado.peor_racha_perdedora_pips:.1f}"
            )

    mt5.shutdown()


if __name__ == "__main__":
    ejecutar()
