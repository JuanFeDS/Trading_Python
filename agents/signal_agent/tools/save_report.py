"""tools/save_report.py
Guardar registros de señales en un historial JSONL (una línea por ejecución).

Uso:
    from agents.signal_agent.tools.save_report import save_signal_report
    save_signal_report(report_dict, path="./Reports/signal_log.jsonl")
"""
import os
import json
from datetime import datetime
from typing import Dict, Any


def save_signal_report(report: Dict[str, Any], path: str = "./Reports/signal_log.jsonl") -> str:
    """Guarda un registro de señal (append) en un archivo JSONL.

    Args:
        report: Diccionario con la salida de run_signal_agent
        path: Ruta del archivo JSONL (se crea carpeta si no existe)

    Returns:
        Ruta absoluta del archivo escrito
    """
    # Añadir timestamp si no viene incluido
    if "timestamp" not in report:
        report = {**report, "timestamp": datetime.utcnow().isoformat() + "Z"}

    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Escribir como JSONL (una línea por registro)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")

    return os.path.abspath(path)

