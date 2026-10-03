"""Carga y valida la configuracion del entorno de trading."""

import os


class ConfiguracionMetaTrader:
    """Configuracion de conexion al terminal MetaTrader 5, tomada de variables de entorno."""

    def __init__(self):
        self.login = int(self._obtener_variable_requerida("MT5_LOGIN"))
        self.password = self._obtener_variable_requerida("MT5_PASSWORD")
        self.server = self._obtener_variable_requerida("MT5_SERVER")
        self.ruta_terminal = os.environ.get("MT5_PATH") or None

    @staticmethod
    def _obtener_variable_requerida(nombre: str) -> str:
        valor = os.environ.get(nombre)
        if not valor:
            raise ValueError(f"Falta definir la variable de entorno {nombre}")
        return valor
