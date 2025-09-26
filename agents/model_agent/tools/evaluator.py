"""tools/evaluator.py
Evaluación tipo backtesting, agnóstica al modelo.

Asume que el modelo fue entrenado con objetivo en t+h (p.ej. Close.shift(-h))
usando características en t. Reconstruye X, predice y compara contra y real.
"""
from typing import Dict, Union, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from agents.model_agent.tools.model_lr import load_model


def _build_feature_matrix(
    market_data: pd.DataFrame,
    indicators: Dict[str, Union[pd.Series, np.ndarray, list]],
    feature_names: list,
) -> pd.DataFrame:
    df = market_data.copy()
    for name, values in indicators.items():
        if name not in df.columns:
            v = values
            if isinstance(v, list):
                v = np.asarray(v)
            if isinstance(v, (pd.Series, np.ndarray)) and len(v) == len(df):
                df[name] = v
    missing = [c for c in feature_names if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan características requeridas por el modelo: {missing}")
    X = df[feature_names].copy()
    return X


def _compute_directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    try:
        sign_true = np.sign(np.diff(y_true, prepend=y_true[0]))
        sign_pred = np.sign(np.diff(y_pred, prepend=y_pred[0]))
        return float(np.mean(sign_true == sign_pred))
    except Exception:
        return float("nan")


def backtest_from_saved_model(
    model_name: str,
    market_data: pd.DataFrame,
    indicators: Dict[str, Union[pd.Series, np.ndarray, list]],
    horizon: int = 1,
) -> Tuple[Dict[str, float], pd.DataFrame]:
    """Ejecuta backtesting cargando un modelo guardado.

    Args:
        model_name: Nombre base en ./models/<model_name>.joblib
        market_data: DataFrame OHLCV
        indicators: Diccionario de indicadores alineados temporalmente
        horizon: Pasos adelante usados al entrenar (target = Close.shift(-h))

    Returns:
        metrics: Dict con MSE, MAE, R2 y precisión direccional
        results: DataFrame con y_true, y_pred
    """
    trainer = load_model(model_name)
    X_raw = _build_feature_matrix(market_data, indicators, trainer.feature_names)
    X = X_raw.dropna()
    # Alinear y_true con X (mismas filas) y aplicar shift futuro
    y_true = market_data.loc[X.index, "Close"].shift(-horizon)
    valid_idx = y_true.dropna().index.intersection(X.index)
    X = X.loc[valid_idx]
    y_true = y_true.loc[valid_idx]

    # Escalar y predecir
    X_scaled = trainer.scaler.transform(X)
    X_for_pred = X if getattr(trainer.model, "needs_index", False) else X_scaled
    y_pred = trainer.model.predict(X_for_pred)
    y_pred = np.asarray(y_pred).reshape(-1)

    # Métricas de regresión
    metrics = {
        "mse": float(mean_squared_error(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
        "directional_accuracy": _compute_directional_accuracy(y_true.values, y_pred),
        "n_samples": int(len(y_true)),
    }

    results = pd.DataFrame({
        "y_true": y_true.values,
        "y_pred": y_pred,
    }, index=valid_idx)

    return metrics, results
