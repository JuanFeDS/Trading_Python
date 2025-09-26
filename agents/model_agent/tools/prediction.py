"""tools/prediction.py
Utilidades de predicción agnósticas al tipo de modelo.

Permite:
 - Cargar un modelo guardado (y su scaler/feature_names)
 - Construir la matriz de características para inferencia
 - Predecir con un modelo individual o con un ensemble
"""
from typing import Dict, List, Union

import numpy as np
import pandas as pd

from agents.model_agent.tools.model_lr import load_model


def _build_feature_matrix(
    market_data: pd.DataFrame,
    indicators: Dict[str, Union[pd.Series, np.ndarray, list]],
    feature_names: List[str],
) -> pd.DataFrame:
    """Construye X para inferencia usando las columnas requeridas por el modelo.

    No genera objetivo ni aplica desplazamientos; asume que el modelo fue entrenado
    con y = Close.shift(-h) y X en tiempo t.
    """
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
    X = df[feature_names].copy().dropna()
    if X.empty:
        raise ValueError("No hay filas válidas para inferencia tras eliminar NaNs.")
    return X


def predict_from_saved_model(
    model_name: str,
    market_data: pd.DataFrame,
    indicators: Dict[str, Union[pd.Series, np.ndarray, list]],
    last_only: bool = True,
):
    """Carga el modelo guardado y devuelve predicciones.

    Args:
        model_name: Nombre base del modelo guardado en ./models/<name>.joblib
        market_data: DataFrame OHLCV
        indicators: Diccionario de indicadores (Series/arrays alineados)
        last_only: Si True, devuelve solo la última predicción
    """
    trainer = load_model(model_name)
    X = _build_feature_matrix(market_data, indicators, trainer.feature_names)
    X_scaled = trainer.scaler.transform(X)
    # Si el modelo permite predecir con fechas (ds), úsalo para evitar problemas de índice
    if hasattr(trainer.model, "predict_with_ds"):
        if "Date" in market_data.columns:
            ds_series = pd.to_datetime(market_data.loc[X.index, "Date"])  # yfinance
        else:
            ds_series = pd.to_datetime(market_data.index).to_series().loc[X.index]
        preds = trainer.model.predict_with_ds(ds_series)
    else:
        X_for_pred = X if getattr(trainer.model, "needs_index", False) else X_scaled
        preds = trainer.model.predict(X_for_pred)
    preds = np.asarray(preds).reshape(-1)
    if last_only:
        # Elegir el último valor no-NaN disponible (maneja horizon y bordes de serie)
        mask = np.isfinite(preds)
        if mask.any():
            return preds[np.where(mask)[0][-1]]
        return float('nan')
    return preds


def ensemble_predict(
    models: List, X: Union[pd.DataFrame, np.ndarray], task: str = "regression"
):
    """Predicción en conjunto (ensemble).

    Args:
        models: Lista de modelos ya ajustados (con método predict)
        X: Matriz de características lista para predecir (no se estandariza aquí)
        task: "regression" para promedio, "classification" para voto mayoritario
    """
    preds_list = [np.asarray(m.predict(X)) for m in models]
    if task == "classification":
        # Voto mayoritario por elemento
        stacked = np.vstack(preds_list)
        final = []
        for i in range(stacked.shape[1]):
            vals, counts = np.unique(stacked[:, i], return_counts=True)
            final.append(vals[np.argmax(counts)])
        return np.array(final)
    # Regresión: promedio simple
    return np.mean(np.vstack(preds_list), axis=0)
