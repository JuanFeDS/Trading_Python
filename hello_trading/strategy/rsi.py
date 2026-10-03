"""Estrategia de RSI (indice de fuerza relativa).

Regla: comprar cuando el RSI sale de zona de sobreventa (cruza el umbral
inferior hacia arriba); cerrar cuando el RSI entra en zona de sobrecompra
(cruza el umbral superior hacia arriba). Solo opera en largo.
"""


class EstrategiaRSI:
    """Genera senales de entrada/salida a partir de cruces de umbral del RSI."""

    NOMBRE = "rsi"

    def __init__(self, periodo: int = 14, umbral_sobreventa: float = 30, umbral_sobrecompra: float = 70):
        self.periodo = periodo
        self.umbral_sobreventa = umbral_sobreventa
        self.umbral_sobrecompra = umbral_sobrecompra

    def _rsi(self, cierres: list[float]) -> float:
        ventana = cierres[-(self.periodo + 1):]
        cambios = [ventana[i] - ventana[i - 1] for i in range(1, len(ventana))]
        ganancia_media = sum(max(cambio, 0) for cambio in cambios) / self.periodo
        perdida_media = sum(max(-cambio, 0) for cambio in cambios) / self.periodo

        if perdida_media == 0:
            return 100.0
        fuerza_relativa = ganancia_media / perdida_media
        return 100 - (100 / (1 + fuerza_relativa))

    def calcular_senal(self, cierres: list[float]) -> str | None:
        if len(cierres) < self.periodo + 2:
            return None

        rsi_actual = self._rsi(cierres)
        rsi_previo = self._rsi(cierres[:-1])

        sale_de_sobreventa = rsi_previo <= self.umbral_sobreventa < rsi_actual
        entra_en_sobrecompra = rsi_previo < self.umbral_sobrecompra <= rsi_actual

        if sale_de_sobreventa:
            return "comprar"
        if entra_en_sobrecompra:
            return "cerrar"
        return None
