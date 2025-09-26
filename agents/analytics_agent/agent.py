"""analytics_agent/agent.py"""
import sys

sys.path.append("./")

from agents.data_market_agent.tools.data_manage import get_data_yfinance
from tools.get_basic_stats import get_basic_stats
from tools.get_indicators import get_technical_indicators


def run_analytics_agent(ticker: str, period: str, interval: str):
    """Función para ejecutar la lógica de analisis del mercado.

    Args:
        ticker (str): Ticker del activo financiero
        period (str): Periodo de la data
        interval (str): Intervalo de la data
    """

    # Descargamos la data
    data = get_data_yfinance.invoke(
        {"ticker": ticker, "period": period, "interval": interval}
    )

    # Obtenemos las estadísticas básicas
    basic_stats = get_basic_stats(data)

    # Obtenemos los indicadores técnicos
    technical_indicators = get_technical_indicators(data)

    print(basic_stats)
    print(technical_indicators)


if __name__ == "__main__":
    run_analytics_agent("AAPL", "1y", "1d")
