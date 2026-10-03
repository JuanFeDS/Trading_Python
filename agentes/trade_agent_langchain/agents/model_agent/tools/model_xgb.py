"""model_xgb.py
Entrenador de regresión con XGBoost, compatible con el flujo existente.

Interfaz similar a LinearModelTrainer:
- prepare_features(market_data, technical_indicators, target_horizon)
- train(market_data, technical_indicators, target_horizon)
- save_model(model_name)

Nota: El guardado es compatible con load_model() existente de model_lr.py
(se guardan las mismas claves). Para compatibilidad, 'model_type' se
almacena como 'linear' aunque el modelo interno sea XGBRegressor.
"""
import os
from typing import Dict, Any, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBRegressor
except Exception as e:  # pragma: no cover
    raise ImportError("Se requiere xgboost. Instala con: pip install xgboost") from e

class XGBModelTrainer:
    """Entrenador XGBoost para regresión de precios futuros."""

    def __init__(self, **xgb_params: Any):
        default = dict(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.0,
            reg_lambda=1.0,
            random_state=42,
            tree_method="hist",
        )
        default.update(xgb_params or {})
        self.model = XGBRegressor(**default)
        self.scaler = StandardScaler()
        self.feature_names: list[str] = []
        self.is_trained = False

    def prepare_features(
        self,
        market_data: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        target_horizon: int = 1,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        df = market_data.copy()
        df["target"] = df["Close"].shift(-target_horizon)
        for name, values in technical_indicators.items():
            if name not in df.columns and isinstance(values, (pd.Series, np.ndarray)) and len(values) == len(df):
                df[name] = values
        features = ["Open", "High", "Low", "Close", "Volume"]
        avail = [f for f in features + list(technical_indicators.keys()) if f in df.columns]
        df = df[avail + ["target"]].dropna()
        if df.empty:
            raise ValueError("No hay suficientes datos después de la limpieza.")
        self.feature_names = avail
        return df[avail], df["target"]

    def train(
        self,
        market_data: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        target_horizon: int = 1,
    ) -> Dict[str, Any]:
        X, y = self.prepare_features(market_data, technical_indicators, target_horizon)
        Xs = self.scaler.fit_transform(X)
        self.model.fit(Xs, y)
        self.is_trained = True
        return {"n_features": len(self.feature_names), "features": self.feature_names, "is_trained": True}

    def save_model(self, model_name: str) -> None:
        if not self.is_trained:
            raise RuntimeError("El modelo debe ser entrenado antes de guardar.")
        path = "./models/" + model_name + ".joblib"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
                # Compatibilidad con load_model() existente
                "model_type": "linear",
                "alpha": 1.0,
            },
            path,
        )

