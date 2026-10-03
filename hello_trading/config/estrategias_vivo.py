"""Que estrategia corre en vivo, con que magic number y en que simbolo.

Fuente de verdad compartida entre main.py (para ejecutar) y
dashboard/servidor.py (para saber a que estrategia pertenece cada
posicion abierta, sin necesitar la logica de la estrategia en si).
"""

MAGIC_BASE = 234000

# (nombre, magic, simbolo) -- validadas en backtest sobre ese simbolo especifico,
# no asumir que el mismo resultado aplica si se cambia el simbolo sin volver a validar.
CONFIGURACION = [
    ("cruce_medias", MAGIC_BASE + 1, "EURUSD.sml"),
    ("rsi", MAGIC_BASE + 2, "EURUSD.sml"),
    ("bollinger", MAGIC_BASE + 3, "EURUSD.sml"),
    ("fractal_breakout", MAGIC_BASE + 4, "USDJPY.sml"),
    ("tendencia_adx", MAGIC_BASE + 5, "USDJPY.sml"),
]
