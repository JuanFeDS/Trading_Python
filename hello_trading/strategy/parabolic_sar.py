"""Parabolic SAR (stop and reverse).

Hipotesis: el precio en tendencia se mantiene fuera de una curva
parabolica que acelera con el tiempo; cuando el precio la cruza, la
tendencia se invierte. Sirve tanto de senal como de stop dinamico.

Regla: se recalcula la tendencia (alcista/bajista) segun el algoritmo de
Wilder sobre toda la ventana recibida. Si la tendencia acaba de virar a
alcista -> 'comprar'; si acaba de virar a bajista -> 'cerrar'. Solo largo.

Fuente: J. Welles Wilder Jr. (1978), "New Concepts in Technical Trading
Systems" -- mismo origen que RSI y ADX, que ya usamos. El propio autor
documenta que falla en mercados laterales (whipsaws); no se encontraron
backtests academicos rigurosos -- evidencia de practica/industria.

No guarda estado entre llamadas (recalcula el SAR completo sobre la
ventana en cada llamada), para mantener la misma interfaz pura que el
resto de las estrategias. Aproximacion conocida: el punto de arranque
del calculo (los primeros 2 velas de la ventana) puede no coincidir con
el arranque real de la tendencia si esta empezo antes de la ventana;
se vuelve irrelevante bien antes de llegar a la vela actual porque la
ventana (VENTANA_MAXIMA / velas_historial) es mucho mas larga que un
ciclo tipico de reversion del SAR.
"""


class EstrategiaParabolicSAR:
    """Genera senales de entrada/salida cuando el Parabolic SAR invierte de tendencia."""

    REQUIERE_VELAS = True
    NOMBRE = "parabolic_sar"

    def __init__(
        self,
        aceleracion_inicial: float = 0.02,
        aceleracion_incremento: float = 0.02,
        aceleracion_maxima: float = 0.2,
    ):
        self.aceleracion_inicial = aceleracion_inicial
        self.aceleracion_incremento = aceleracion_incremento
        self.aceleracion_maxima = aceleracion_maxima

    def _calcular_tendencias(self, velas: list[dict]) -> list[bool]:
        """Tendencia (True=alcista) para cada vela desde la segunda en adelante."""
        tendencia_alcista = velas[1]["close"] > velas[0]["close"]
        punto_extremo = velas[1]["high"] if tendencia_alcista else velas[1]["low"]
        aceleracion = self.aceleracion_inicial
        sar = velas[0]["low"] if tendencia_alcista else velas[0]["high"]

        tendencias = [tendencia_alcista]

        for indice in range(2, len(velas)):
            vela = velas[indice]
            sar = sar + aceleracion * (punto_extremo - sar)

            if tendencia_alcista:
                sar = min(sar, velas[indice - 1]["low"], velas[indice - 2]["low"])
                if vela["low"] < sar:
                    tendencia_alcista = False
                    sar = punto_extremo
                    punto_extremo = vela["low"]
                    aceleracion = self.aceleracion_inicial
                elif vela["high"] > punto_extremo:
                    punto_extremo = vela["high"]
                    aceleracion = min(aceleracion + self.aceleracion_incremento, self.aceleracion_maxima)
            else:
                sar = max(sar, velas[indice - 1]["high"], velas[indice - 2]["high"])
                if vela["high"] > sar:
                    tendencia_alcista = True
                    sar = punto_extremo
                    punto_extremo = vela["high"]
                    aceleracion = self.aceleracion_inicial
                elif vela["low"] < punto_extremo:
                    punto_extremo = vela["low"]
                    aceleracion = min(aceleracion + self.aceleracion_incremento, self.aceleracion_maxima)

            tendencias.append(tendencia_alcista)

        return tendencias

    def calcular_senal(self, velas: list[dict]) -> str | None:
        if len(velas) < 5:
            return None

        tendencias = self._calcular_tendencias(velas)
        tendencia_actual = tendencias[-1]
        tendencia_previa = tendencias[-2]

        if tendencia_actual and not tendencia_previa:
            return "comprar"
        if not tendencia_actual and tendencia_previa:
            return "cerrar"
        return None
