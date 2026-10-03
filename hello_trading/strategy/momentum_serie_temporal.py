"""Time Series Momentum.

Hipotesis: el retorno acumulado de los ultimos N periodos predice
positivamente el retorno futuro -- lo que subio tiende a seguir
subiendo. A diferencia del cruce de medias, no compara dos promedios:
mira directamente el retorno del precio sobre la ventana.

Regla: retorno de los ultimos N periodos > 0 -> 'comprar' (mantener
largo); <= 0 -> 'cerrar'. Se reevalua cada vela, como en el rebalanceo
periodico del paper original, no como un cruce puntual.

Fuente: Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum",
Journal of Financial Economics -- testeado sobre 58 mercados (incluye
forex) con +25 anios de datos. Evidencia academica solida, aunque el
paper usa ventanas mensuales/diarias; aqui se adapta a velas intradia.
"""


class EstrategiaMomentumSerieTemporal:
    """Genera senales a partir del signo del retorno acumulado de los ultimos N periodos."""

    NOMBRE = "momentum_serie_temporal"

    def __init__(self, periodo: int = 20):
        self.periodo = periodo

    def calcular_senal(self, cierres: list[float]) -> str | None:
        if len(cierres) < self.periodo + 1:
            return None

        cierre_inicial = cierres[-1 - self.periodo]
        retorno = (cierres[-1] - cierre_inicial) / cierre_inicial

        if retorno > 0:
            return "comprar"
        return "cerrar"
