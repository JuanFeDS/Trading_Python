"""model_prophet.py
Entrenador con Prophet compatible con el flujo existente.

Interfaz:
- prepare_features(market_data, technical_indicators, target_horizon)
- train(market_data, technical_indicators, target_horizon)
- save_model(model_name)

Compatibilidad:
Se guarda un objeto con claves: model (wrapper con predict), scaler, feature_names,
model_type, alpha; para que prediction.py y evaluator.py funcionen sin cambios.
"""
import os
from typing import Dict, Any, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

try:
    from prophet import Prophet
except Exception as e:  # pragma: no cover
    raise ImportError("Se requiere 'prophet'. Instala con: pip install prophet") from e


class _ProphetWrapper:
    """Wrapper que ofrece predict(X) para integrarse con el pipeline.

    Ignora X en valores y usa sus índices (fechas) para devolver yhat
    desplazado por el horizonte configurado.
    """
    def __init__(self, model: Prophet, yhat: pd.Series, horizon: int, index_to_ds: pd.Series):
        self.model = model
        self.yhat = yhat  # Serie indexada por el índice original del DataFrame
        self.h = int(horizon)
        self.index_to_ds = index_to_ds  # map index -> ds
        self.needs_index = True  # Indica que predict requiere X con índice (DataFrame)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        idx = X.index
        # Desplazar yhat para que la predicción en t sea el yhat de t+h
        yhat_shifted = self.yhat.shift(-self.h)
        return yhat_shifted.loc[idx].to_numpy()

    def predict_with_ds(self, ds_series: pd.Series) -> np.ndarray:
        """Predice usando nuevas fechas (ds). Devuelve yhat desplazado por h."""
        df = pd.DataFrame({"ds": pd.to_datetime(ds_series.values)})
        forecast = self.model.predict(df)
        yhat = forecast["yhat"].reset_index(drop=True)
        return yhat.shift(-self.h).to_numpy()


class ProphetModelTrainer:
    """Entrenador Prophet para predicción de precios futuros."""

    def __init__(self, **prophet_kwargs: Any):
        self.prophet_kwargs = prophet_kwargs or {}
        self.model: Prophet | None = None
        self.scaler = StandardScaler()
        self.feature_names: list[str] = ["Close"]
        self.is_trained = False
        self.horizon = 1
        self._index_to_ds: pd.Series | None = None
        self._yhat: pd.Series | None = None

    def prepare_features(
        self,
        market_data: pd.DataFrame,
        technical_indicators: Dict[str, Any],  # no usados, por compatibilidad
        target_horizon: int = 1,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        df = market_data.copy()
        if "Date" in df.columns:
            ds = pd.to_datetime(df["Date"])  # yfinance a veces trae 'Date'
        else:
            # Si el índice ya es datetime, úsalo; de lo contrario conviértelo
            ds = pd.to_datetime(df.index)
        y = df["Close"].astype(float)
        self.horizon = int(target_horizon)
        self._index_to_ds = pd.Series(ds.values, index=df.index)
        # Para compatibilidad con el pipeline, X será solo 'Close'
        X = pd.DataFrame({"Close": y.values}, index=df.index)
        return X, y

    def train(
        self,
        market_data: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        target_horizon: int = 1,
    ) -> Dict[str, Any]:
        X, y = self.prepare_features(market_data, technical_indicators, target_horizon)
        self.scaler.fit_transform(X)  # mantener contrato del pipeline
        df_fit = pd.DataFrame({
            "ds": self._index_to_ds.loc[X.index].values,
            "y": y.loc[X.index].values,
        })
        m = Prophet(**self.prophet_kwargs)
        m.fit(df_fit)
        # Pronóstico in-sample para todas las fechas del set
        forecast = m.predict(df_fit[["ds"]])
        yhat = pd.Series(forecast["yhat"].values, index=X.index)
        self.model = m
        self._yhat = yhat
        self.is_trained = True
        return {"n_features": len(self.feature_names), "features": self.feature_names, "is_trained": True}

    def save_model(self, model_name: str) -> None:
        if not self.is_trained or self.model is None or self._yhat is None or self._index_to_ds is None:
            raise RuntimeError("El modelo debe ser entrenado antes de guardar.")
        path = "./models/" + model_name + ".joblib"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        wrapper = _ProphetWrapper(self.model, self._yhat, self.horizon, self._index_to_ds)
        joblib.dump(
            {
                "model": wrapper,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
                "model_type": "linear",  # compatibilidad con load_model existente
                "alpha": 1.0,
            },
            path,
        )

