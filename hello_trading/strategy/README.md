# Estrategias

Cada estrategia es una clase pura: no guarda estado ni accede a MT5, decide únicamente a partir de lo que recibe en `calcular_senal(...)`. Todas operan solo en largo (la señal `"cerrar"` sale de una posición existente, no abre una venta).

Hay dos interfaces según qué necesita la estrategia:

- **Solo cierres** (`cruce_medias`, `rsi`, `bollinger`, `macd`): `calcular_senal(cierres: list[float]) -> "comprar" | "cerrar" | None`.
- **Velas OHLC** (`donchian_breakout`, `tendencia_adx`, `mean_reversion_adx`, `fractal_breakout`, marcadas con `REQUIERE_VELAS = True`): `calcular_senal(velas: list[dict]) -> "comprar" | "cerrar" | None`, donde cada vela es `{"time", "open", "high", "low", "close"}` — necesario para ADX, canales de Donchian y fractales, que dependen de máximos/mínimos, no solo del cierre.

El motor de backtest (`backtest/motor_backtest.py`) detecta la interfaz por el atributo `REQUIERE_VELAS` y arma la ventana correcta para cada una, así que ambos tipos conviven en la misma comparación. Se reutiliza en dos contextos:

- **Backtest** (`backtest/`): recorre un historial de velas vela por vela, llamando a `calcular_senal` con una ventana creciente (acotada a `VENTANA_MAXIMA=250` velas para que el costo no crezca cuadráticamente), y simula entradas/salidas con SL/TP fijo.
- **Vivo** (`main.py`): `data/velas.py::FuenteVelasVivo` sondea MT5, detecta cuándo cierra una vela nueva y le pasa esos cierres a la estrategia (hoy solo conecta `cruce_medias`; las nuevas de velas OHLC aún no tienen su propio runner en vivo). En el arranque en frío fija su estado sin evaluar señal, para no disparar una orden por un cruce viejo del historial.

Los indicadores compartidos por las 4 estrategias nuevas (EMA, RSI, ADX, Bandas de Bollinger) viven en `strategy/indicadores.py`. Las 4 estrategias originales se dejaron con su propio cálculo inline, sin migrar.

## Cruce de medias móviles (`moving_average_crossover.py`)

SMA rápida vs SMA lenta sobre el cierre. Cruce alcista (rápida supera a la lenta) → `"comprar"`; cruce bajista → `"cerrar"`.

| Parámetro | Valor por defecto |
|---|---|
| Periodo SMA rápida | 9 |
| Periodo SMA lenta | 21 |

## RSI (`rsi.py`)

Compra cuando el RSI sale de sobreventa (cruza el umbral inferior hacia arriba); cierra cuando entra en sobrecompra (cruza el umbral superior hacia arriba).

| Parámetro | Valor por defecto |
|---|---|
| Periodo | 14 |
| Umbral sobreventa | 30 |
| Umbral sobrecompra | 70 |

## Bandas de Bollinger (`bollinger_bands.py`)

Reversión a la media: compra en el rebote desde la banda inferior; cierra al tocar o superar la banda superior.

| Parámetro | Valor por defecto |
|---|---|
| Periodo (SMA central) | 20 |
| Desviaciones estándar | 2.0 |

## MACD (`macd.py`)

Compra cuando la línea MACD cruza hacia arriba su línea de señal; cierra cuando cruza hacia abajo. EMA sembrada con la SMA de los primeros `periodo` valores (aproximación estándar, no coincide exactamente con el indicador nativo de MT5).

| Parámetro | Valor por defecto |
|---|---|
| Periodo EMA rápida | 12 |
| Periodo EMA lenta | 26 |
| Periodo línea de señal | 9 |

## Donchian Breakout (`donchian_breakout.py`)

El canal (máximo/mínimo de las N velas anteriores, sin incluir la vela actual) se rompe hacia arriba → `"comprar"`; se rompe hacia abajo → `"cerrar"`.

| Parámetro | Valor por defecto |
|---|---|
| Periodo del canal | 20 |

## Trend Following + ADX (`tendencia_adx.py`)

Régimen tendencial (ADX por encima de umbral + EMA lenta con pendiente) + EMA rápida por encima de la lenta + el precio retrocede hasta tocar la EMA rápida + el RSI recupera sobre 50 → `"comprar"`. Cierra cuando la EMA rápida cruza por debajo de la lenta (se pierde la estructura).

| Parámetro | Valor por defecto |
|---|---|
| Periodo EMA rápida | 20 |
| Periodo EMA lenta | 50 |
| Periodo ADX | 14 |
| Umbral ADX (régimen tendencial) | 25 |
| Periodo RSI | 14 |
| Tolerancia de pullback | 0.1% del precio |

## Mean Reversion + ADX (`mean_reversion_adx.py`)

Como Bollinger, pero solo compra en sobreventa extrema (cierre bajo la banda inferior + RSI bajo) si el ADX confirma que el mercado está en rango (ADX bajo) — evita revertir movimientos durante una tendencia fuerte. Cierra al volver a la banda media.

| Parámetro | Valor por defecto |
|---|---|
| Periodo bandas | 20 |
| Desviaciones estándar | 2.0 |
| Periodo RSI | 14 |
| Umbral RSI sobreventa | 30 |
| Periodo ADX | 14 |
| Umbral ADX (rango) | 20 |

## Fractal Breakout (`fractal_breakout.py`)

Fractales de Bill Williams (ventana de 5 velas, confirmados 2 velas después para evitar look-ahead bias) definen la última resistencia/soporte de estructura. Ruptura de la resistencia + ADX confirma tendencia + EMA con pendiente positiva → `"comprar"`. Cierra si el precio rompe el soporte (stop estructural, no una distancia fija).

| Parámetro | Valor por defecto |
|---|---|
| Periodo EMA | 50 |
| Periodo ADX | 14 |
| Umbral ADX | 20 |

**Fuera de alcance por ahora** (de las ideas planteadas, quedan para una iteración futura si esta sobrevive el backtest): detección explícita de estructura HH/HL/LL/LH como régimen, métricas cuantitativas del fractal (retests, edad, fuerza de ruptura), SL dinámico en el último fractal a nivel de orden (hoy el "cerrar" es una señal, no un stop en el bróker), Regime Switching, Multi-pair Momentum, Session Breakout y Carry+Momentum.

## Time Series Momentum (`momentum_serie_temporal.py`)

Retorno acumulado de los últimos N periodos > 0 → `"comprar"` (mantener largo); ≤ 0 → `"cerrar"`. Se reevalúa cada vela (no es un cruce puntual, es un estado que se reafirma o revierte).

| Parámetro | Valor por defecto |
|---|---|
| Periodo | 20 |

Fuente: Moskowitz, Ooi & Pedersen (2012), *"Time Series Momentum"*, Journal of Financial Economics — testeado sobre 58 mercados (incluye forex) con +25 años de datos. Evidencia académica sólida, aunque el paper usa ventanas mensuales/diarias, no velas intradía.

## TTM Squeeze (`ttm_squeeze.py`)

Compresión de volatilidad: cuando las Bandas de Bollinger quedan dentro del Canal de Keltner (squeeze activo) y luego se liberan con momentum positivo (cierre sobre su EMA) → `"comprar"`. Cierra si el squeeze se reactiva o el momentum se vuelve negativo.

| Parámetro | Valor por defecto |
|---|---|
| Periodo (BB y Keltner) | 20 |
| Desviaciones Bollinger | 2.0 |
| Multiplicador Keltner (× ATR) | 1.5 |

Fuente: John Carter (Simpler Trading), práctica de trading popularizada, sin papers académicos que la respalden. Es la idea de "Volatility Compression" de la lista original, con una regla concreta.

## Parabolic SAR (`parabolic_sar.py`)

Recalcula la tendencia (algoritmo de Wilder) sobre toda la ventana recibida en cada llamada, sin guardar estado. Si la tendencia acaba de virar a alcista → `"comprar"`; si vira a bajista → `"cerrar"`.

| Parámetro | Valor por defecto |
|---|---|
| Aceleración inicial | 0.02 |
| Incremento de aceleración | 0.02 |
| Aceleración máxima | 0.2 |

Fuente: J. Welles Wilder Jr. (1978), *"New Concepts in Technical Trading Systems"* — mismo origen que RSI y ADX. El propio autor documenta que falla en mercados laterales; sin backtests académicos rigurosos encontrados.

## Backtest (`backtest/`)

`python -m backtest.comparar` descarga el historial de `EURUSD.sml` en M5 (30 días por defecto) y corre las 11 estrategias contra el mismo set de datos, con SL 20 / TP 40 pips (mismos valores que `main.py`). Reporta operaciones, tasa de acierto, pips totales y peor racha perdedora. Corre en ~7 segundos para 6300+ velas.

**Simplificaciones conocidas:**
- El SL/TP de la simulación se evalúa contra el precio de cierre de cada vela, no contra el rango intravela — sirve para comparar estrategias entre sí, no como simulación exacta de ejecución.
- La ventana pasada a cada estrategia se acota a `VENTANA_MAXIMA=250` velas (ver `motor_backtest.py`) por rendimiento; ninguna estrategia actual necesita más historial que eso.
- ADX usa una aproximación con medias móviles simples, no la suavización recursiva de Wilder.

**Resultado de referencia** (30 días, `EURUSD.sml` M5, SL 20 / TP 40 pips):

| Estrategia | Operaciones | Tasa acierto | Pips totales | Peor racha |
|---|---|---|---|---|
| cruce_medias | 168 | 32.1% | -139.9 | -50.5 |
| rsi | 80 | 63.7% | -76.8 | -60.6 |
| bollinger | 78 | 62.8% | **+56.1** | -44.4 |
| macd | 273 | 27.8% | -199.4 | -59.6 |
| donchian_breakout | 74 | 27.0% | -168.4 | -48.4 |
| tendencia_adx | 30 | 30.0% | -39.2 | -42.1 |
| mean_reversion_adx | 10 | 40.0% | -42.0 | -30.8 |
| fractal_breakout | 87 | 31.0% | -125.5 | -46.0 |
| momentum_serie_temporal | 360 | 30.3% | -202.2 | -36.5 |
| ttm_squeeze | 79 | 20.3% | -85.9 | -36.5 |
| parabolic_sar | 286 | 35.0% | -210.0 | -56.1 |

Bollinger sigue siendo la única con pips totales positivos en esta ventana de 30 días — ni Time Series Momentum (a pesar de su respaldo académico) ni TTM Squeeze ni Parabolic SAR la superan aquí; los tres, con parámetros por defecto, están entre las peores del set. `tendencia_adx` y `mean_reversion_adx` operan muy poco (30 y 10 operaciones) — sus filtros de régimen son estrictos, lo que probablemente pide más historial o parámetros menos conservadores antes de descartarlas. No es una recomendación definitiva, solo el punto de partida para decidir cuáles pasan a forward-testing en demo.

## Barrido de parámetros (`backtest/barrido.py`, `ajustar_parametros.py`)

`python -m backtest.ajustar_parametros` corre un grid search por estrategia (filtrando combinaciones con menos de 15 operaciones) y muestra el top 3 de cada una. Con 30 días de M5: bollinger ya estaba en su óptimo (20, 2.0); rsi mejoró bastante con periodo=21 (de -76.8 a -4.9 pips); mean_reversion_adx casi llegó a breakeven con umbral_adx_rango=30 (+0.4 pips). El resto no mejoró de forma relevante en el rango probado.

## Duración de operación: intento de scalping (descartado)

Se probó acortar la duración promedio de una operación (bollinger/rsi/mean_reversion_adx tardan 1.5-3.2h en M5) por dos caminos, ambos sin éxito:

1. **Timeframe M1 con SL/TP de 5-10 pips** (`backtest/scalping.py`, `ajustar_scalping.py`), incluyendo el spread real (~0.8 pips) como costo por operación. Ni con un barrido completo de parámetros recalibrado para M1 se encontró una combinación sólidamente rentable con duración <30min — lo más cercano fue `mean_reversion_adx` prácticamente en breakeño (-1.9 pips), es decir, ruido, no ventaja real.
2. **M5 con SL/TP más chico** (`ajustar_duracion_media.py`, objetivo 30-60min): no acortó la duración de forma relevante (siguió en 150-300+ min) porque en estas estrategias la salida casi siempre la dispara la señal (RSI en sobrecompra, precio toca la banda media), no el SL/TP — y además empeoró a bollinger (de +56 a -7.9 pips) al recortar ganancias antes de tiempo.

**Conclusión:** la duración larga de bollinger en M5 (~3.2h) es inherente a cómo sale de la posición, no un defecto ajustable con SL/TP o timeframe. Para acortarla de verdad haría falta un mecanismo nuevo (cierre forzado por tiempo máximo), no probado todavía. Por ahora se acepta la duración larga y se sigue con bollinger M5 original (periodo=20, desviaciones=2.0, SL 20 / TP 40 pips).
