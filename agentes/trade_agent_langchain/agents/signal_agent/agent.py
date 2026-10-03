import sys
import os
from typing import Dict, List

import pandas as pd

sys.path.append("./")

from agents.data_market_agent.tools.data_manage import get_data_yfinance
from agents.analytics_agent.tools.get_indicators import get_technical_indicators

from agents.model_agent.tools.prediction import predict_from_saved_model
from agents.model_agent.agent import train_and_save_model

from agents.signal_agent.tools.save_report import save_signal_report


def _build_indicators_dict(df: pd.DataFrame) -> Dict[str, pd.Series]:
    cols = [
        "SMA_20","EMA_20","RSI_14",
        "MACD_line","MACD_signal","MACD_histogram",
        "BB_upper","BB_middle","BB_lower",
    ]
    return {c: df[c] for c in cols if c in df.columns}


def _rule_based_signal(row: pd.Series, pred_up: bool) -> str:
    ema_gt_sma = row.get("EMA_20", pd.NA) > row.get("SMA_20", pd.NA)
    rsi_bull = row.get("RSI_14", 50) > 50
    macd_bull = row.get("MACD_line", 0) > row.get("MACD_signal", 0)
    bull = bool(ema_gt_sma and rsi_bull and macd_bull and pred_up)

    ema_lt_sma = row.get("EMA_20", pd.NA) < row.get("SMA_20", pd.NA)
    rsi_bear = row.get("RSI_14", 50) < 50
    macd_bear = row.get("MACD_line", 0) < row.get("MACD_signal", 0)
    bear = bool(ema_lt_sma and rsi_bear and macd_bear and (not pred_up))

    if bull:
        return "BUY"
    if bear:
        return "SELL"
    return "HOLD"


def _ensure_model(model_name: str, default_ticker: str, period: str, interval: str, horizon: int = 1) -> None:
    path = f"./models/{model_name}.joblib"
    if os.path.exists(path):
        return
    parts = model_name.split("_")
    m_ticker = parts[0].upper() if parts else default_ticker
    engine = "linear"
    if model_name.endswith("_xgb"):
        engine = "xgb"
    elif model_name.endswith("_prophet"):
        engine = "prophet"
    train_and_save_model(
        ticker=m_ticker,
        period=period,
        interval=interval,
        model_type="ridge",
        alpha=1.0,
        horizon=horizon,
        model_name=model_name,
        engine=engine,
    )


def run_signal_agent(
    ticker: str = "GOOGL",
    period: str = "5d",
    interval: str = "1m",
    model_names: List[str] = ("googl_linear","googl_xgb","googl_prophet"),
) -> Dict:
    data = get_data_yfinance.invoke({"ticker": ticker, "period": period, "interval": interval})
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise RuntimeError(f"Fallo al obtener datos para {ticker}: {data}")

    df_ind = get_technical_indicators(data, mode="full")
    ind_dict = _build_indicators_dict(df_ind)

    # Lista de modelos explícita
    model_names = list(model_names)

    preds = {}
    last_close = float(data["Close"].iloc[-1])
    for name in model_names:
        # Garantizar que el modelo exista; si no, entrenar y guardar
        _ensure_model(name, ticker, period, interval, horizon=1)
        try:
            p = predict_from_saved_model(name, data, ind_dict, last_only=True)
            preds[name] = float(p)
        except Exception as e:
            preds[name] = None

    valid_preds = [v for v in preds.values() if isinstance(v, (int, float))]
    avg_pred = float(pd.Series(valid_preds).mean()) if valid_preds else None
    pred_up = (avg_pred is not None) and (avg_pred > last_close)

    row = df_ind.iloc[-1]
    signal = _rule_based_signal(row, pred_up)

    rationale = {
        "ema_vs_sma": f"EMA20 {'>' if row.get('EMA_20',0)>row.get('SMA_20',0) else '<='} SMA20",
        "rsi": float(row.get("RSI_14", 50)),
        "macd": float(row.get("MACD_line", 0) - row.get("MACD_signal", 0)),
        "last_close": last_close,
        "avg_pred": avg_pred,
        "pred_up": pred_up,
    }

    result = {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "signal": signal,
        "models": preds,
        "rationale": rationale,
    }
    saved_path = save_signal_report(result, path="./reports/signal_log.jsonl")
    return {**result, "saved_to": saved_path}


if __name__ == "__main__":
    t = os.getenv("AG_SIGNAL_TICKER", "AAPL")
    per = os.getenv("AG_SIGNAL_PERIOD", "5d")
    inter = os.getenv("AG_SIGNAL_INTERVAL", "1m")
    models_env = os.getenv("AG_SIGNAL_MODELS", "").strip()
    models = [m.strip() for m in models_env.split(",") if m.strip()] if models_env else ["googl_linear","googl_xgb","googl_prophet"]
    res = run_signal_agent(ticker=t, period=per, interval=inter, model_names=models)
    print(res)

