"""model_lr.py
Módulo para entrenar y guardar modelos de regresión lineal.
"""
import os
from typing import Dict, Any, Tuple

import pandas as pd
import numpy as np

import joblib

from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler


class LinearModelTrainer:
    """Clase para entrenar y guardar modelos de regresión lineal."""

    def __init__(
        self,
        model_type: str = "linear",
        alpha: float = 1.0,
    ):
        """Inicializa el entrenador del modelo.

        Args:
            model_type: Tipo de modelo ('linear', 'ridge', 'lasso')
            alpha: Parámetro de regularización para Ridge/Lasso
        """
        self.model_type = model_type
        self.alpha = alpha
        self.model = self._initialize_model()
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False

    def _initialize_model(self):
        """Inicializa el modelo según el tipo especificado."""
        if self.model_type == "linear":
            return LinearRegression()
        elif self.model_type == "ridge":
            return Ridge(alpha=self.alpha)
        elif self.model_type == "lasso":
            return Lasso(alpha=self.alpha)
        else:
            raise ValueError("model_type debe ser 'linear', 'ridge' o 'lasso'")

    def prepare_features(
        self,
        market_data: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        target_horizon: int = 1,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepara las características para el entrenamiento.

        Args:
            market_data: DataFrame con datos OHLCV
            technical_indicators: Diccionario con indicadores técnicos
            target_horizon: Períodos futuros a predecir

        Returns:
            Tupla con características (X) y variable objetivo (y)
        """
        df = market_data.copy()

        # Crear variable objetivo (precio futuro)
        df["target"] = df["Close"].shift(-target_horizon)

        # Añadir indicadores técnicos
        for name, values in technical_indicators.items():
            if isinstance(values, (pd.Series, np.ndarray)) and len(values) == len(df):
                df[name] = values

        # Características básicas
        features = ["Open", "High", "Low", "Close", "Volume"]

        # Asegurar que solo usamos columnas existentes
        available_features = [
            f for f in features + list(technical_indicators.keys()) if f in df.columns
        ]

        # Eliminar filas con valores faltantes
        df = df[available_features + ["target"]].dropna()

        if df.empty:
            raise ValueError("No hay suficientes datos después de la limpieza.")

        self.feature_names = available_features
        return df[available_features], df["target"]

    def train(
        self,
        market_data: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        target_horizon: int = 1,
    ) -> Dict[str, Any]:
        """Entrena el modelo con los datos proporcionados.

        Args:
            market_data: DataFrame con datos de mercado
            technical_indicators: Diccionario con indicadores técnicos
            target_horizon: Períodos futuros a predecir

        Returns:
            Diccionario con información del entrenamiento
        """
        X, y = self.prepare_features(market_data, technical_indicators, target_horizon)

        # Estandarizar características
        X_scaled = self.scaler.fit_transform(X)

        # Entrenar modelo
        self.model.fit(X_scaled, y)
        self.is_trained = True

        return {
            "model_type": self.model_type,
            "n_features": len(self.feature_names),
            "features": self.feature_names,
            "is_trained": True,
        }

    def save_model(self, model_name: str) -> None:
        """Guarda el modelo y el escalador en disco.

        Args:
            model_name: Ruta donde se guardará el modelo
        """
        if not self.is_trained:
            raise RuntimeError("El modelo debe ser entrenado antes de guardar.")

        path = './models/'
        path += model_name
        path += '.joblib'
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Guardar modelo y escalador
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "feature_names": self.feature_names,
                "model_type": self.model_type,
                "alpha": self.alpha,
            },
            path,
        )


def load_model(model_name: str) -> LinearModelTrainer:
    """Carga un modelo previamente guardado.

    Args:
        model_name: Ruta al archivo del modelo guardado

    Returns:
        Instancia de LinearModelTrainer con el modelo cargado
    """
    path = './models/'
    path += model_name
    path += '.joblib'
    data = joblib.load(path)

    trainer = LinearModelTrainer(
        model_type=data["model_type"], alpha=data.get("alpha", 1.0)
    )

    trainer.model = data["model"]
    trainer.scaler = data["scaler"]
    trainer.feature_names = data["feature_names"]
    trainer.is_trained = True

    return trainer
