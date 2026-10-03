"""Cliente de ejecucion de ordenes contra el terminal MetaTrader 5."""

import time

import MetaTrader5 as mt5

from storage.registro_operaciones import RegistroOperaciones


SYMBOL_FILLING_FOK = 1
SYMBOL_FILLING_IOC = 2

def tamano_pip(info_simbolo) -> float:
    """Tamano de 1 pip para el simbolo. Reutilizado tambien por el motor de backtest."""
    return info_simbolo.point * (10 if info_simbolo.digits in (3, 5) else 1)


class ClienteMetaTrader:
    """Ejecuta ordenes de mercado en la cuenta conectada al terminal MT5 y registra cada una.

    El magic number es por instancia (no global): permite correr varias
    estrategias en paralelo sobre la misma cuenta sin que una toque las
    posiciones de otra.
    """

    def __init__(self, magic: int, nombre_estrategia: str, registro: RegistroOperaciones | None = None):
        self.magic = magic
        self.nombre_estrategia = nombre_estrategia
        self.registro = registro or RegistroOperaciones()

    @staticmethod
    def _elegir_modo_relleno(info_simbolo) -> int:
        """El modo de relleno soportado varia por simbolo/broker; hay que consultarlo en vez de fijarlo."""
        if info_simbolo.filling_mode & SYMBOL_FILLING_IOC:
            return mt5.ORDER_FILLING_IOC
        if info_simbolo.filling_mode & SYMBOL_FILLING_FOK:
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN

    def enviar_orden_mercado(
        self,
        simbolo: str,
        volumen: float,
        comprar: bool,
        distancia_sl_pips: float | None = None,
        distancia_tp_pips: float | None = None,
    ) -> mt5.OrderSendResult:
        if not mt5.symbol_select(simbolo, True):
            raise RuntimeError(f"No se pudo habilitar el simbolo {simbolo}")

        info_simbolo = mt5.symbol_info(simbolo)
        tick = mt5.symbol_info_tick(simbolo)
        if info_simbolo is None or tick is None:
            raise RuntimeError(f"No hay informacion disponible para {simbolo}")

        precio_entrada = tick.ask if comprar else tick.bid

        solicitud = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": simbolo,
            "volume": volumen,
            "type": mt5.ORDER_TYPE_BUY if comprar else mt5.ORDER_TYPE_SELL,
            "price": precio_entrada,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._elegir_modo_relleno(info_simbolo),
            "magic": self.magic,
        }

        if distancia_sl_pips or distancia_tp_pips:
            pip = tamano_pip(info_simbolo)
            signo = 1 if comprar else -1
            if distancia_sl_pips:
                solicitud["sl"] = round(precio_entrada - signo * distancia_sl_pips * pip, info_simbolo.digits)
            if distancia_tp_pips:
                solicitud["tp"] = round(precio_entrada + signo * distancia_tp_pips * pip, info_simbolo.digits)

        resultado = self._enviar(solicitud)
        self.registro.registrar_apertura(
            ticket=resultado.order,
            simbolo=simbolo,
            comprar=comprar,
            volumen=volumen,
            precio=resultado.price,
            estrategia=self.nombre_estrategia,
        )
        return resultado

    def cerrar_posicion(self, ticket: int) -> mt5.OrderSendResult:
        posiciones = mt5.positions_get(ticket=ticket)
        if not posiciones:
            raise RuntimeError(f"No existe una posicion abierta con ticket {ticket}")
        posicion = posiciones[0]

        info_simbolo = mt5.symbol_info(posicion.symbol)
        tick = mt5.symbol_info_tick(posicion.symbol)
        if info_simbolo is None or tick is None:
            raise RuntimeError(f"No hay informacion disponible para {posicion.symbol}")

        es_compra = posicion.type == mt5.ORDER_TYPE_BUY

        solicitud = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": posicion.symbol,
            "volume": posicion.volume,
            "type": mt5.ORDER_TYPE_SELL if es_compra else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "price": tick.bid if es_compra else tick.ask,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._elegir_modo_relleno(info_simbolo),
            "magic": self.magic,
        }

        resultado = self._enviar(solicitud)
        profit = self._obtener_profit_deal(resultado.deal)
        self.registro.registrar_cierre(ticket=ticket, precio_cierre=resultado.price, profit=profit)
        return resultado

    @staticmethod
    def _obtener_profit_deal(ticket_deal: int, intentos: int = 5, espera_segundos: float = 0.2) -> float:
        """El historial de deals puede tardar unos milisegundos en reflejar el deal recien creado."""
        for _ in range(intentos):
            deals = mt5.history_deals_get(ticket=ticket_deal)
            if deals:
                return deals[0].profit
            time.sleep(espera_segundos)
        return 0.0

    @staticmethod
    def _enviar(solicitud: dict) -> mt5.OrderSendResult:
        resultado = mt5.order_send(solicitud)
        if resultado is None:
            raise RuntimeError(f"order_send no respondio: {mt5.last_error()}")
        if resultado.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"Orden rechazada: retcode={resultado.retcode} comment={resultado.comment!r}")
        return resultado

    def obtener_posiciones_abiertas(self, simbolo: str | None = None) -> tuple:
        posiciones = mt5.positions_get(symbol=simbolo) if simbolo else mt5.positions_get()
        if posiciones is None:
            raise RuntimeError(f"No se pudo consultar posiciones abiertas: {mt5.last_error()}")
        return tuple(posicion for posicion in posiciones if posicion.magic == self.magic)
