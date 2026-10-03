# Objetivo
Construir un **MVP de trading multiagente con LLM** que opere primero en *paper trading* y backtesting, con deliberación entre agentes especializados, gestión de riesgo explícita y auditoría completa de decisiones (trazabilidad).

---

## Alcance del MVP (4–6 semanas)
1. **Mercado**: Acciones US (universo S&P 100 para empezar).
2. **Horizonte**: *Swing trading* diario (D1) y 4H; ejecución al abrir/cerrar.
3. **Datos**: OHLCV (mínimo 2–5 años), noticias y sentimiento de titulares.
4. **Agentes**:
   - **Técnico** (señales: MA cross, RSI, MACD, ATR para stop sizing).
   - **Noticias/Sentimiento** (resumen + score de titulares recientes por ticker).
   - **Riesgo** (posición, exposición, drawdown, stop/TP, sizing por volatilidad).
   - **Bull vs Bear** (formulan hipótesis opuestas con evidencia).
   - **Portfolio Manager (PM)** (agrega, pide nuevas rondas si hay conflicto, decide la orden final).
   - **Ejecución** (traduce decisión a órdenes y simula *slippage/fees*).
5. **Motor de backtesting**: `vectorbt` (rápido, pandas/numpy) o `backtrader` (más broker-like). Para el MVP: **vectorbt** + modelo simple de comisiones y *slippage*.
6. **Evaluación**: CAGR, Sharpe/Sortino, Máx. Drawdown, Calmar, Hit ratio, Turnover, Exposure, *Tail risk* (CVaR aproximado).
7. **Primero backtest**, luego **paper trading** (p. ej., Alpaca), y logs explicables.

---

## Arquitectura (alto nivel)
- **Orquestación**: Grafo de agentes con estados compartidos (LangGraph o state machine propia).
- **Capa de datos**:
  - *Market data*: OHLCV por ticker (CSV/Parquet local + caché) y "live" (cuando pasemos a paper trading).
  - *Noticias*: titulares recientes por ticker; si no hay API aún, usar dataset estático para MVP.
  - *Features*: indicadores técnicos (talib/ta), volatilidad (ATR), *risk-free* para Sharpe.
- **Capa de agentes** (LLM/tool calling): cada agente lee el *state* y escribe: `rationale`, `signal` (BUY/SELL/HOLD), `confidence ∈ [0,1]`, `constraints`.
- **Consenso**: PM agrega señales usando **votos ponderados por confianza** + **reglas del Risk**; si hay desacuerdo fuerte, invoca una **2ª ronda** de deliberación breve.
- **Ejecución/Simulación**: traduce decisión a órdenes, respeta límites, y registra *fills* simulados.
- **Trazabilidad**: Guardar `state.jsonl` por ciclo (inputs, prompts, salidas, decisión final, métricas).

---

## Protocolo de deliberación (simplificado)
1. **Ronda 1**: Técnico, Noticias y Bull/Bear generan `signal`, `price_target`, `stop`, `rationale`.
2. **Risk** valida: tamaño máximo por volatilidad, límites por ticker/sector, exposición neta, *MDD guardrail*.
3. **PM** agrega señales (p. ej. votación ponderada + veto del Risk) → propuesta de órdenes.
4. Si **conflicto** (desviación alta entre agentes o baja confianza agregada), **Ronda 2** con *focused prompts* sobre discrepancias.
5. **Ejecución** (simulada) y **logging** completo.

---

## Reglas de riesgo (MVP)
- **Tamaño por volatilidad (ATR)**: riesgo por trade ≤ 0.5% de capital.
- **Límites**: posición máx. por ticker 5%, por sector 15%, exposición neta long 60%, short 30% (MVP long-only si se prefiere).
- **Stops**: dinámicos con ATR (p. ej. 2×ATR) y *time stop* (5–10 días sin progreso).
- **Circuit breaker**: si MDD > 8% en backtest/semana, reducir tamaño 50% o pausar.

---

## Métricas y reporting
- **Rendimiento**: CAGR, Sharpe, Sortino, Calmar.
- **Riesgo**: Máx. Drawdown, VaR/CVaR (histórico), Volatilidad.
- **Operativa**: Win rate, Profit factor, Avg R/R, Turnover, Costs %, Slippage %.
- **Explicabilidad**: *Reason traces* por trade, *feature attributions* simples (qué señal pesó más).

---

## Stack sugerido (alineado a tu entorno)
- **Python 3.12**, **FastAPI** para API/servicios.
- **LangGraph** (o implementación propia) para orquestar el flujo multiagente.
- **OpenAI/Local LLM**: coste/latencia; usar "mini" para scouting y *retry* con modelo mayor en conflictos.
- **vectorbt** + `pandas`, `ta`/`pandas-ta`.
- **Persistencia**: Parquet para datos; JSONL para logs de razonamiento; **MLflow** o Weights&Biases para experimentos.
- **Paper trading**: Alpaca (equities) o IBKR; empezar con Alpaca Paper.
- **Infra**: Docker + `docker-compose`; scheduler (*cron* o Prefect/Airflow si crece).

---

## Estructura de proyecto (propuesta)
```
trading-agents/
├─ src/
│  ├─ data/
│  │  ├─ loaders.py          # Yahoo/Polygon/Alpaca; caché Parquet
│  │  ├─ features.py         # Indicadores técnicos, ATR, volatilidad
│  │  └─ news.py             # Titulares + simple sentiment
│  ├─ agents/
│  │  ├─ base.py             # Interface Agent
│  │  ├─ technical.py        # Agente Técnico
│  │  ├─ news.py             # Agente Noticias/Sentimiento
│  │  ├─ bull_bear.py        # Hipótesis opuestas
│  │  ├─ risk.py             # Reglas de riesgo, sizing
│  │  └─ pm.py               # Portfolio Manager (consenso)
│  ├─ exec/
│  │  ├─ simulator.py        # Slippage, fees, fills
│  │  └─ broker_alpaca.py    # (fase 2) Paper trading
│  ├─ bt/
│  │  ├─ backtest.py         # Loop de backtest y métricas
│  │  └─ metrics.py          # Sharpe, MDD, etc.
│  ├─ api/
│  │  └─ app.py              # FastAPI: /run_backtest, /paper_trade, /logs
│  ├─ prompts/
│  │  ├─ technical.md
│  │  ├─ news.md
│  │  ├─ bull.md
│  │  ├─ bear.md
│  │  └─ pm.md
│  └─ graph.py               # Orquestación LangGraph/state machine
├─ tests/
├─ data/                     # Parquet/CSV cache
├─ docker/Dockerfile
├─ docker-compose.yml
└─ README.md
```

---

## Especificación de estado compartido (clave)
```yaml
State:
  as_of: <timestamp>
  universe: [AAPL, MSFT, ...]
  ohlcv: <DataFrame refs>
  features: { ticker: { rsi: float, macd: float, atr: float, ... } }
  news: { ticker: [{title, ts, source, sentiment}...] }
  proposals: [{
     ticker, side, entry, stop, take_profit,
     rationale, agent, confidence
  }]
  risk_report: { exposure, breaches: [...], sizing: {...} }
  decision: { orders: [...], rationale, confidence }
  logs_uri: "logs/2025-08-24/run_001.jsonl"
```

---

## Plantillas de *prompt* (MVP)
**Agente Técnico** (`prompts/technical.md`)
```
Eres un analista técnico disciplinado. Con base en los indicadores provistos:
- Propón UNA operación por ticker o HOLD.
- Define: side (BUY/SELL/HOLD), entry, stop (en ATRs), take_profit, y confianza 0–1.
- Explica en ≤80 palabras la razón.
Recuerda: evita señales contradictorias y prioriza relación R/R ≥ 1.8.
Entradas: {features_json}
```

**Agente Noticias/Sentimiento** (`prompts/news.md`)
```
Eres un analista de noticias. Resume titulares recientes y asigna un score de -1 a 1.
- Si la señal contradice fuerte al técnico, justifica.
- Devuelve: side, rationale (≤60 palabras), confidence.
Titulares: {news_json}
```

**Bull / Bear** (`prompts/bull.md` / `prompts/bear.md`)
```
Defiende la hipótesis {BULL|BEAR} para el ticker. Usa evidencia de features/news.
Devuelve: side, target, invalidation (stop), 2 bullets de evidencia, confidence.
```

**Risk** (no LLM, reglas determinísticas)
- Calcula tamaño con `risk_per_trade = 0.5%` y stop en ATR.
- Banderas rojas si liquidity baja, gaps > 5%, earnings inminentes.

**PM** (`prompts/pm.md`)
```
Eres el gestor de portafolio. Toma las propuestas, aplica reglas del Risk, y decide.
- Si consenso < τ o conflicto alto, solicita otra ronda enfocada.
- Devuelve órdenes finales + mini-razonamiento trazable.
```

---

## Bucle de backtest (pseudocódigo)
```python
for ts in trading_calendar:
    state = load_state(ts)
    props = []
    props += technical_agent(state)
    props += news_agent(state)
    props += bull_bear_agents(state)

    risk_report = risk_engine(props, state)
    decision = pm_agent(props, risk_report)

    fills = simulator.execute(decision, state)
    ledger.update(fills)

    log_run(state, props, risk_report, decision, fills)
```

---

## Modelos y costes (estrategia práctica)
- **Ruta A (eficiencia)**: LLM pequeño (gpt‑mini / local 7–8B) para Ronda 1; si *conflict score* alto → elevar a modelo mayor solo para PM.
- **Ruta B (100% local)**: Llama‑3.x 8B/11B para Técnico/Noticias + reglas más duras en Risk; PM con 70B local si se requiere (más coste/latencia).
- **Guardrails**: límites de tokens, *stop sequences*, grounding estricto (solo usar datos del `state`).

---

## Validación experimental (mínimo)
1. **Universo**: 20 tickers del S&P100.
2. **Periodo**: 2019–2024 train; 2024–2025 out‑of‑sample.
3. **Comparativas**: Buy&Hold, MA crossover, RSI contrarian.
4. **Costes realistas**: 2–5 bps por lado + *slippage* proporcional a ATR.
5. **Tests**: sensibilidad a costes, *ablation* por agente, estabilidad del consenso.

---

## Endpoints (FastAPI)
- `POST /backtest/run` {universe, start, end, params}
- `GET  /backtest/report/{run_id}` métricas + equity curve
- `POST /paper/place` {orders}
- `GET  /logs/{run_id}` descarga del JSONL

---

## Roadmap
**Semana 1–2**: datos + features + motor de backtest + Risk rules.

**Semana 3**: agentes Técnico/Noticias/Bull-Bear + PM + consenso.

**Semana 4**: evaluación, *ablation*, reporte; si pasa umbral → paper trading.

**Semana 5–6**: conectores broker, monitor en tiempo real, panel web.

---

## Próximos pasos inmediatos
1. Acordar universo de tickers y periodo.
2. Elegir `vectorbt` y definir costes/slippage del MVP.
3. Preparar `State` y *prompts* definitivos.
4. Implementar `risk_engine` y `pm_agent` determinista + mínima llamada LLM.
5. Ejecutar el primer backtest y revisar métricas/razonamientos.

