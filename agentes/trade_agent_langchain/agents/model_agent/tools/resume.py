"""tools/resume.py
Síntesis de resultados de evaluación para múltiples modelos.

Entrada esperada:
results = {
  "model_a": {"mse": ..., "mae": ..., "r2": ..., "directional_accuracy": ..., "n_samples": ...},
  "model_b": {...}
}
"""
from typing import Dict, Any, List, Optional
import json
import math
import pandas as pd


def _to_float(x):
    try:
        if x is None:
            return math.nan
        return float(x)
    except Exception:
        return math.nan


def summarize_to_dataframe(
    results: Dict[str, Dict[str, Any]],
    sort_by: str = "r2",
    ascending: Optional[bool] = None,
) -> pd.DataFrame:
    """Convierte resultados a DataFrame y los ordena por la métrica indicada.

    Si ascending no se especifica, usa ascendente para "mse"/"mae" y descendente para el resto.
    """
    rows: List[Dict[str, Any]] = []
    for name, metrics in results.items():
        rows.append({
            "model": name,
            "mse": _to_float(metrics.get("mse")),
            "mae": _to_float(metrics.get("mae")),
            "r2": _to_float(metrics.get("r2")),
            "directional_accuracy": _to_float(metrics.get("directional_accuracy")),
            "n_samples": int(metrics.get("n_samples", 0)) if str(metrics.get("n_samples", "")).isdigit() else metrics.get("n_samples", 0),
        })

    df = pd.DataFrame(rows)
    if ascending is None:
        ascending = sort_by in ("mse", "mae")
    if sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=ascending, na_position="last")
    df.insert(0, "rank", range(1, len(df) + 1))
    return df.reset_index(drop=True)


def summarize_to_json(
    results: Dict[str, Dict[str, Any]],
    sort_by: str = "r2",
    ascending: Optional[bool] = None,
    indent: Optional[int] = 2,
) -> str:
    """Devuelve un JSON ordenado con los resultados y su ranking."""
    df = summarize_to_dataframe(results, sort_by=sort_by, ascending=ascending)
    payload = df.to_dict(orient="records")
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def summarize(
    results: Dict[str, Dict[str, Any]],
    sort_by: str = "r2",
    ascending: Optional[bool] = None,
    as_json: bool = False,
) -> Any:
    """Interfaz simple: devuelve DataFrame o JSON con ranking y métricas clave."""
    if as_json:
        return summarize_to_json(results, sort_by=sort_by, ascending=ascending)
    return summarize_to_dataframe(results, sort_by=sort_by, ascending=ascending)


