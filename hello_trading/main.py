"""Punto de entrada: corre varias estrategias en paralelo contra el terminal MT5.

Cada estrategia tiene su propio simbolo, magic number y (si REQUIERE_VELAS)
recibe velas OHLC en vez de solo cierres. Las fuentes de velas se comparten
por simbolo (una sola llamada a MT5 por ciclo, no una por estrategia).
"""

import sys
import time
from datetime import datetime

from dotenv import load_dotenv
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding="utf-8")

from config.estrategias_vivo import CONFIGURACION
from config.settings import ConfiguracionMetaTrader
from data.velas import FuenteVelasVivo
from execution.mt5_client import ClienteMetaTrader
from strategy.bollinger_bands import EstrategiaBandasBollinger
from strategy.fractal_breakout import EstrategiaFractalBreakout
from strategy.moving_average_crossover import EstrategiaCruceMedias
from strategy.rsi import EstrategiaRSI
from strategy.tendencia_adx import EstrategiaTendenciaADX

TIMEFRAME = mt5.TIMEFRAME_M5
VOLUMEN_POR_OPERACION = 0.01
DISTANCIA_SL_PIPS = 20
DISTANCIA_TP_PIPS = 40
INTERVALO_SONDEO_SEGUNDOS = 10

INSTANCIAS_ESTRATEGIA = {
    "cruce_medias": EstrategiaCruceMedias(),
    "rsi": EstrategiaRSI(periodo=21, umbral_sobreventa=30, umbral_sobrecompra=70),
    "bollinger": EstrategiaBandasBollinger(),
    "fractal_breakout": EstrategiaFractalBreakout(),
    "tendencia_adx": EstrategiaTendenciaADX(),
}

ESTRATEGIAS = [(nombre, INSTANCIAS_ESTRATEGIA[nombre], magic, simbolo) for nombre, magic, simbolo in CONFIGURACION]


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


def _procesar_estrategia(
    nombre: str, estrategia, cliente: ClienteMetaTrader, simbolo: str, velas: list[dict] | None
) -> None:
    requiere_velas = getattr(estrategia, "REQUIERE_VELAS", False)
    entrada_estrategia = velas if requiere_velas else ([v["close"] for v in velas] if velas is not None else None)
    senal = estrategia.calcular_senal(entrada_estrategia) if entrada_estrategia is not None else None
    posiciones_abiertas = cliente.obtener_posiciones_abiertas(simbolo)

    if senal == "comprar" and not posiciones_abiertas:
        resultado = cliente.enviar_orden_mercado(
            simbolo,
            VOLUMEN_POR_OPERACION,
            comprar=True,
            distancia_sl_pips=DISTANCIA_SL_PIPS,
            distancia_tp_pips=DISTANCIA_TP_PIPS,
        )
        print(f"🟢 [{nombre}] {simbolo} compra abierta: ticket={resultado.order} precio={resultado.price}")
    elif senal == "cerrar" and posiciones_abiertas:
        for posicion in posiciones_abiertas:
            resultado = cliente.cerrar_posicion(posicion.ticket)
            print(f"🔴 [{nombre}] {simbolo} posicion cerrada: ticket={posicion.ticket} precio={resultado.price}")
    else:
        hora = datetime.now().strftime("%H:%M:%S")
        print(f"⏳ [{hora}] [{nombre}] {simbolo} sin senal, {len(posiciones_abiertas)} posicion(es) abierta(s)")


def ejecutar():
    load_dotenv()
    configuracion = ConfiguracionMetaTrader()
    _iniciar_conexion(configuracion)

    resumen = ", ".join(f"{nombre}({simbolo})" for nombre, _, _, simbolo in ESTRATEGIAS)
    print(f"🔌 Conectado a la cuenta {configuracion.login} en {configuracion.server}")
    print(f"   estrategias en paralelo: {resumen}")

    clientes = [
        (nombre, estrategia, ClienteMetaTrader(magic=magic, nombre_estrategia=nombre), simbolo)
        for nombre, estrategia, magic, simbolo in ESTRATEGIAS
    ]

    simbolos_unicos = {simbolo for _, _, _, simbolo in ESTRATEGIAS}
    fuentes_velas = {simbolo: FuenteVelasVivo(simbolo, TIMEFRAME) for simbolo in simbolos_unicos}

    try:
        while True:
            velas_por_simbolo = {
                simbolo: fuente.obtener_velas_si_hay_vela_nueva() for simbolo, fuente in fuentes_velas.items()
            }

            for nombre, estrategia, cliente, simbolo in clientes:
                try:
                    _procesar_estrategia(nombre, estrategia, cliente, simbolo, velas_por_simbolo[simbolo])
                except Exception as error:
                    hora = datetime.now().strftime("%H:%M:%S")
                    print(f"⚠️ [{hora}] [{nombre}] {simbolo} error en el ciclo, se reintenta en el siguiente: {error}")

            time.sleep(INTERVALO_SONDEO_SEGUNDOS)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    ejecutar()
