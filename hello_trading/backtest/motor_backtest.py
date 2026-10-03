"""Motor de backtesting: simula una estrategia sobre velas historicas, sin ejecutar ordenes reales.

Simplificacion: el SL/TP se evalua contra el precio de cierre de cada
vela, no contra el rango intravela (no se descargan maximos/minimos para
la simulacion de salida, aunque las estrategias con REQUIERE_VELAS si
reciben el high/low de cada vela para su propio calculo). Suficiente para
comparar estrategias entre si, no para una simulacion de ejecucion exacta.

Las estrategias que exponen `REQUIERE_VELAS = True` reciben la ventana de
velas completa (dicts con open/high/low/close/time); el resto recibe solo
la lista de cierres, igual que antes.
"""

from dataclasses import dataclass, field

VENTANA_MAXIMA = 250
"""Acota el historial pasado a cada estrategia por llamada, para que el costo total
del backtest crezca linealmente con el numero de velas en vez de cuadraticamente."""


@dataclass
class ResultadoBacktest:
    """Metricas resultantes de correr una estrategia contra un historial de velas."""

    nombre_estrategia: str
    operaciones: int = 0
    operaciones_ganadoras: int = 0
    pips_totales: float = 0.0
    pips_por_operacion: list[float] = field(default_factory=list)
    duracion_velas_por_operacion: list[int] = field(default_factory=list)

    @property
    def tasa_acierto(self) -> float:
        return self.operaciones_ganadoras / self.operaciones if self.operaciones else 0.0

    @property
    def duracion_velas_promedio(self) -> float:
        if not self.duracion_velas_por_operacion:
            return 0.0
        return sum(self.duracion_velas_por_operacion) / len(self.duracion_velas_por_operacion)

    @property
    def peor_racha_perdedora_pips(self) -> float:
        peor = 0.0
        acumulado = 0.0
        for pips in self.pips_por_operacion:
            acumulado = acumulado + pips if pips < 0 else 0.0
            peor = min(peor, acumulado)
        return peor


def correr_backtest(
    estrategia,
    velas: list[dict],
    pip: float,
    distancia_sl_pips: float,
    distancia_tp_pips: float,
    spread_pips: float = 0.0,
) -> ResultadoBacktest:
    """spread_pips: costo de ida y vuelta descontado de cada operacion (comprar al ask, vender al bid).
    Irrelevante con SL/TP de decenas de pips, pero decisivo en scalping con SL/TP de pocos pips."""
    resultado = ResultadoBacktest(nombre_estrategia=getattr(estrategia, "NOMBRE", type(estrategia).__name__))
    requiere_velas = getattr(estrategia, "REQUIERE_VELAS", False)

    precio_entrada = None
    precio_sl = None
    precio_tp = None
    indice_entrada = None

    def _cerrar(precio_salida: float, indice_salida: int) -> None:
        nonlocal precio_entrada
        pips = (precio_salida - precio_entrada) / pip - spread_pips
        resultado.operaciones += 1
        resultado.pips_por_operacion.append(pips)
        resultado.pips_totales += pips
        resultado.duracion_velas_por_operacion.append(indice_salida - indice_entrada)
        if pips > 0:
            resultado.operaciones_ganadoras += 1
        precio_entrada = None

    for indice in range(1, len(velas)):
        precio_actual = velas[indice]["close"]

        if precio_entrada is not None and (precio_actual <= precio_sl or precio_actual >= precio_tp):
            _cerrar(precio_actual, indice)
            continue

        inicio_ventana = max(0, indice + 1 - VENTANA_MAXIMA)
        ventana = velas[inicio_ventana : indice + 1]
        entrada_estrategia = ventana if requiere_velas else [vela["close"] for vela in ventana]
        senal = estrategia.calcular_senal(entrada_estrategia)

        if senal == "comprar" and precio_entrada is None:
            precio_entrada = precio_actual
            precio_sl = precio_entrada - distancia_sl_pips * pip
            precio_tp = precio_entrada + distancia_tp_pips * pip
            indice_entrada = indice
        elif senal == "cerrar" and precio_entrada is not None:
            _cerrar(precio_actual, indice)

    return resultado
