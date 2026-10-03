"""Barrido de parametros: corre una estrategia con distintas combinaciones y ordena por resultado.

Filtra combinaciones con muy pocas operaciones (`operaciones_minimas`) para
no quedarse con resultados que son ruido de una muestra chica.
"""

from itertools import product

from backtest.motor_backtest import ResultadoBacktest, correr_backtest


def barrer_estrategia(
    fabrica_estrategia,
    grilla: dict[str, list],
    velas: list[dict],
    pip: float,
    distancia_sl_pips: float,
    distancia_tp_pips: float,
    operaciones_minimas: int = 15,
) -> list[tuple[dict, ResultadoBacktest]]:
    nombres_parametros = list(grilla.keys())
    combinaciones = list(product(*grilla.values()))

    resultados = []
    for valores in combinaciones:
        parametros = dict(zip(nombres_parametros, valores))
        estrategia = fabrica_estrategia(**parametros)
        resultado = correr_backtest(estrategia, velas, pip, distancia_sl_pips, distancia_tp_pips)
        if resultado.operaciones >= operaciones_minimas:
            resultados.append((parametros, resultado))

    resultados.sort(key=lambda par: par[1].pips_totales, reverse=True)
    return resultados
