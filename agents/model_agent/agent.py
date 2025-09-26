import sys
import os
from typing import Dict

import pandas as pd

sys.path.append("./")

from agents.data_market_agent.tools.data_manage import get_data_yfinance
from agents.analytics_agent.tools.get_indicators import get_technical_indicators

from agents.model_agent.tools.model_lr import LinearModelTrainer
from agents.model_agent.tools.prediction import predict_from_saved_model
from agents.model_agent.tools.evaluator import backtest_from_saved_model
from agents.model_agent.tools.resume import summarize
from agents.model_agent.tools.model_xgb import XGBModelTrainer
from agents.model_agent.tools.model_prophet import ProphetModelTrainer


def _build_indicators_dict(df: pd.DataFrame) -> Dict[str, pd.Series]:
    cols = ["SMA_20","EMA_20","RSI_14","MACD_line","MACD_signal","MACD_histogram","BB_upper","BB_middle","BB_lower"]
    return {c: df[c] for c in cols if c in df.columns}

def train_and_save_model(
    ticker: str = "GOOGL",
    period: str = "1y",
    interval: str = "1d",
    model_type: str = "ridge",
    alpha: float = 1.0,
    horizon: int = 1,
    model_name: str = "googl_linear",
    engine: str = "linear",
) -> Dict:
    data = get_data_yfinance.invoke({"ticker": ticker, "period": period, "interval": interval})
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise RuntimeError(f"Fallo al obtener datos para {ticker}: {data}")
    df_ind = get_technical_indicators(data, mode="full"); indicators = _build_indicators_dict(df_ind)
    if engine == "xgb":
        trainer = XGBModelTrainer()
    elif engine == "prophet":
        trainer = ProphetModelTrainer()
    else:
        trainer = LinearModelTrainer(model_type=model_type, alpha=alpha)
    info = trainer.train(data, indicators, target_horizon=horizon)
    trainer.save_model(model_name)
    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "model_info": info,
        "model_path": f"./models/{model_name}.joblib",
    }


def predict_latest(
    model_name: str,
    ticker: str = "GOOGL",
    period: str = "6mo",
    interval: str = "1d",
):
    data = get_data_yfinance.invoke({"ticker": ticker, "period": period, "interval": interval})
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise RuntimeError(f"Fallo al obtener datos para {ticker}: {data}")
    df_ind = get_technical_indicators(data, mode="full")
    return predict_from_saved_model(model_name, data, _build_indicators_dict(df_ind), last_only=True)


def evaluate_model(
    model_name: str,
    ticker: str = "GOOGL",
    period: str = "1y",
    interval: str = "1d",
    horizon: int = 1,
):
    data = get_data_yfinance.invoke({"ticker": ticker, "period": period, "interval": interval})
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise RuntimeError(f"Fallo al obtener datos para {ticker}: {data}")
    df_ind = get_technical_indicators(data, mode="full")
    return backtest_from_saved_model(model_name, data, _build_indicators_dict(df_ind), horizon=horizon)


def summarize_models(
    model_names: list[str] = ["googl_linear", "googl_xgb", "googl_prophet"],
    ticker: str = "GOOGL",
    period: str = "1y",
    interval: str = "1d",
    horizon: int = 1,
    as_json: bool = False,
):
    data = get_data_yfinance.invoke({"ticker": ticker, "period": period, "interval": interval})
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise RuntimeError(f"Fallo al obtener datos para {ticker}: {data}")
    df_ind = get_technical_indicators(data, mode="full"); indicators = _build_indicators_dict(df_ind)
    results: Dict[str, dict] = {}
    for name in model_names:
        metrics, _ = backtest_from_saved_model(name, data, indicators, horizon=horizon)
        results[name] = metrics
    return summarize(results, sort_by="r2", as_json=as_json)


def run_agent(
    ticker: str = "GOOGL", period: str = "1y", interval: str = "1d", horizon: int = 1,
    engines: tuple[str, ...] = ("linear","xgb","prophet"),
    predict_period: str = "6mo", predict_interval: str = "1d", as_json: bool = False
):
    results: Dict[str, dict] = {}
    for eng in engines:
        name = f"{ticker.lower()}_" + ("linear" if eng=="linear" else ("xgb" if eng=="xgb" else "prophet"))
        train_and_save_model(ticker, period, interval, "ridge", 1.0, horizon, name, eng)
        pred = predict_latest(model_name=name, ticker=ticker, period=predict_period, interval=predict_interval)
        met, _ = evaluate_model(model_name=name, ticker=ticker, period=period, interval=interval, horizon=horizon)
        results[name] = {"prediction": pred, **met}
    summary = summarize_models(model_names=list(results.keys()), ticker=ticker, period=period, interval=interval, horizon=horizon, as_json=as_json)
    return results, summary


if __name__ == "__main__":
    t=os.getenv("AG_TICKER","GOOGL"); per=os.getenv("AG_PERIOD","1y"); inter=os.getenv("AG_INTERVAL","1d"); horiz=int(os.getenv("AG_HORIZON","1"))
    asj=os.getenv("AG_SUMMARY_JSON","0")=="1"
    engs=tuple([e.strip() for e in os.getenv("AG_ENGINES","linear,xgb,prophet").split(",") if e.strip()])
    pper=os.getenv("AG_PREDICT_PERIOD","6mo"); pint=os.getenv("AG_PREDICT_INTERVAL","1d")
    res,summ=run_agent(ticker=t,period=per,interval=inter,horizon=horiz,engines=engs,predict_period=pper,predict_interval=pint,as_json=asj)
    print("Resultados:",res); print("Resumen:",summ)
