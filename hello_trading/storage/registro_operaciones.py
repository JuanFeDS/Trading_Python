"""Registro persistente de operaciones ejecutadas, en una base SQLite local."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

RUTA_BASE_DATOS = Path(__file__).parent.parent / "operaciones.db"


class RegistroOperaciones:
    """Guarda la apertura y el cierre de cada operacion en SQLite."""

    def __init__(self, ruta_base_datos: Path = RUTA_BASE_DATOS):
        self.ruta_base_datos = ruta_base_datos
        self._crear_tabla()

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self.ruta_base_datos)

    def _crear_tabla(self) -> None:
        with self._conectar() as conexion:
            conexion.execute(
                """
                CREATE TABLE IF NOT EXISTS operaciones (
                    ticket INTEGER PRIMARY KEY,
                    simbolo TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    volumen REAL NOT NULL,
                    precio_apertura REAL NOT NULL,
                    hora_apertura TEXT NOT NULL,
                    precio_cierre REAL,
                    hora_cierre TEXT,
                    profit REAL
                )
                """
            )
            columnas_existentes = {fila[1] for fila in conexion.execute("PRAGMA table_info(operaciones)")}
            if "estrategia" not in columnas_existentes:
                conexion.execute("ALTER TABLE operaciones ADD COLUMN estrategia TEXT")

    def registrar_apertura(
        self, ticket: int, simbolo: str, comprar: bool, volumen: float, precio: float, estrategia: str
    ) -> None:
        with self._conectar() as conexion:
            conexion.execute(
                "INSERT INTO operaciones (ticket, simbolo, tipo, volumen, precio_apertura, hora_apertura, estrategia) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ticket,
                    simbolo,
                    "compra" if comprar else "venta",
                    volumen,
                    precio,
                    datetime.now(timezone.utc).isoformat(),
                    estrategia,
                ),
            )

    def registrar_cierre(self, ticket: int, precio_cierre: float, profit: float) -> None:
        with self._conectar() as conexion:
            conexion.execute(
                "UPDATE operaciones SET precio_cierre = ?, hora_cierre = ?, profit = ? WHERE ticket = ?",
                (precio_cierre, datetime.now(timezone.utc).isoformat(), profit, ticket),
            )
