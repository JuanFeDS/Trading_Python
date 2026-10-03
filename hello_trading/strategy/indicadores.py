"""Indicadores tecnicos compartidos entre estrategias basadas en velas OHLC.

No usado por las estrategias originales (cruce_medias, rsi, bollinger, macd),
que se dejaron intactas con su propio calculo inline sobre listas de cierres.
"""


def ema(valores: list[float], periodo: int, historial_max: int = 200) -> float:
    """EMA aproximada, sembrada con la SMA de los primeros `periodo` valores.

    Se limita a los ultimos `historial_max` valores para que el costo por
    llamada sea constante en backtests largos: el peso de valores muy
    antiguos en una EMA ya es despreciable a esa distancia.
    """
    ventana = valores[-historial_max:]
    multiplicador = 2 / (periodo + 1)
    promedio = sum(ventana[:periodo]) / periodo
    for valor in ventana[periodo:]:
        promedio = (valor - promedio) * multiplicador + promedio
    return promedio


def rsi(cierres: list[float], periodo: int) -> float:
    ventana = cierres[-(periodo + 1):]
    cambios = [ventana[i] - ventana[i - 1] for i in range(1, len(ventana))]
    ganancia_media = sum(max(cambio, 0) for cambio in cambios) / periodo
    perdida_media = sum(max(-cambio, 0) for cambio in cambios) / periodo
    if perdida_media == 0:
        return 100.0
    fuerza_relativa = ganancia_media / perdida_media
    return 100 - (100 / (1 + fuerza_relativa))


def bandas_bollinger(cierres: list[float], periodo: int, desviaciones: float) -> tuple[float, float, float]:
    ventana = cierres[-periodo:]
    media = sum(ventana) / periodo
    varianza = sum((cierre - media) ** 2 for cierre in ventana) / periodo
    desviacion_estandar = varianza**0.5
    return media - desviaciones * desviacion_estandar, media, media + desviaciones * desviacion_estandar


def adx(velas: list[dict], periodo: int) -> float:
    """ADX aproximado con medias moviles simples en vez de la suavizacion recursiva de Wilder."""
    ventana = velas[-(2 * periodo + 1):]
    if len(ventana) < periodo + 2:
        return 0.0

    tramos = []
    for indice in range(1, len(ventana)):
        anterior, actual = ventana[indice - 1], ventana[indice]
        subida = actual["high"] - anterior["high"]
        bajada = anterior["low"] - actual["low"]
        mas_dm = subida if subida > bajada and subida > 0 else 0.0
        menos_dm = bajada if bajada > subida and bajada > 0 else 0.0
        rango_verdadero = max(
            actual["high"] - actual["low"],
            abs(actual["high"] - anterior["close"]),
            abs(actual["low"] - anterior["close"]),
        )
        tramos.append((mas_dm, menos_dm, rango_verdadero))

    valores_dx = []
    for indice in range(periodo - 1, len(tramos)):
        tramo = tramos[indice - periodo + 1 : indice + 1]
        suma_mas_dm = sum(t[0] for t in tramo)
        suma_menos_dm = sum(t[1] for t in tramo)
        suma_tr = sum(t[2] for t in tramo)
        if suma_tr == 0:
            valores_dx.append(0.0)
            continue
        mas_di = 100 * suma_mas_dm / suma_tr
        menos_di = 100 * suma_menos_dm / suma_tr
        if mas_di + menos_di == 0:
            valores_dx.append(0.0)
            continue
        valores_dx.append(100 * abs(mas_di - menos_di) / (mas_di + menos_di))

    if not valores_dx:
        return 0.0
    return sum(valores_dx[-periodo:]) / min(periodo, len(valores_dx))


def atr(velas: list[dict], periodo: int) -> float:
    """Average True Range, con media movil simple (no la suavizacion recursiva de Wilder)."""
    ventana = velas[-(periodo + 1):]
    if len(ventana) < 2:
        return 0.0

    rangos_verdaderos = []
    for indice in range(1, len(ventana)):
        anterior, actual = ventana[indice - 1], ventana[indice]
        rangos_verdaderos.append(
            max(
                actual["high"] - actual["low"],
                abs(actual["high"] - anterior["close"]),
                abs(actual["low"] - anterior["close"]),
            )
        )
    return sum(rangos_verdaderos[-periodo:]) / len(rangos_verdaderos[-periodo:])
