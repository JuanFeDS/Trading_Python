"""Corre un backtest de todas las estrategias del set sobre el mismo historial y compara resultados."""

import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding="utf-8")

from backtest.datos_historicos import obtener_velas_historicas
from backtest.motor_backtest import correr_backtest
from config.settings import ConfiguracionMetaTrader
from execution.mt5_client import tamano_pip
from strategy.bollinger_bands import EstrategiaBandasBollinger
from strategy.donchian_breakout import EstrategiaDonchianBreakout
from strategy.fractal_breakout import EstrategiaFractalBreakout
from strategy.macd import EstrategiaMACD
from strategy.mean_reversion_adx import EstrategiaMeanReversionADX
from strategy.momentum_serie_temporal import EstrategiaMomentumSerieTemporal
from strategy.moving_average_crossover import EstrategiaCruceMedias
from strategy.parabolic_sar import EstrategiaParabolicSAR
from strategy.rsi import EstrategiaRSI
from strategy.tendencia_adx import EstrategiaTendenciaADX
from strategy.ttm_squeeze import EstrategiaTTMSqueeze

SIMBOLO = sys.argv[1] if len(sys.argv) > 1 else "EURUSD.sml"
TIMEFRAME = mt5.TIMEFRAME_M5
MINUTOS_POR_VELA = 5  # debe coincidir con TIMEFRAME; mt5.TIMEFRAME_* no se puede usar directo como minutos salvo M1..M30
DIAS_HISTORIAL = 30
DISTANCIA_SL_PIPS = 20
DISTANCIA_TP_PIPS = 40


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
    print()

    estrategias = [
        EstrategiaCruceMedias(),
        EstrategiaRSI(),
        EstrategiaBandasBollinger(),
        EstrategiaMACD(),
        EstrategiaDonchianBreakout(),
        EstrategiaTendenciaADX(),
        EstrategiaMeanReversionADX(),
        EstrategiaFractalBreakout(),
        EstrategiaMomentumSerieTemporal(),
        EstrategiaTTMSqueeze(),
        EstrategiaParabolicSAR(),
    ]

    encabezado = (
        f"{'Estrategia':<25} {'Operaciones':>11} {'Tasa acierto':>13} "
        f"{'Pips totales':>13} {'Peor racha':>11} {'Duracion prom.':>15}"
    )
    print(encabezado)
    print("-" * len(encabezado))

    for estrategia in estrategias:
        resultado = correr_backtest(estrategia, velas, pip, DISTANCIA_SL_PIPS, DISTANCIA_TP_PIPS)
        horas_promedio = resultado.duracion_velas_promedio * MINUTOS_POR_VELA / 60
        print(
            f"{resultado.nombre_estrategia:<25} {resultado.operaciones:>11} "
            f"{resultado.tasa_acierto:>12.1%} {resultado.pips_totales:>13.1f} "
            f"{resultado.peor_racha_perdedora_pips:>11.1f} {horas_promedio:>13.1f}h"
        )

    mt5.shutdown()


if __name__ == "__main__":
    ejecutar()
