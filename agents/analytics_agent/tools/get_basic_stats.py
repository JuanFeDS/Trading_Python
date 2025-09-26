"""get_basic_stats.py"""
import pandas as pd

def get_basic_stats(data: pd.DataFrame) -> dict:
    """Función para obtener las estadísticas básicas de los datos de mercado

    Args:
        data (pd.DataFrame): Dataframe con los datos de mercado.

    Returns:
        dict: Diccionario con las estadísticas básicas.
    """

    # Calculamos el drawdown
    roll_max = data['Close'].cummax()
    drawdons = (data['Close'] - roll_max) / roll_max

    # Calculamos los retornos
    returns = data['Close'].pct_change().dropna()

    basic_stats = {
        # Precios
        'last_close': float(data['Close'].iloc[-1]),
        'max_price': float(data['High'].max()),
        'min_price': float(data['Low'].min()),
        'range': float(data['High'].max() - data['Low'].min()),
        'avg_price': float(data['Close'].mean()),

        # Volumen
        'total_volume': int(data['Volume'].sum()),
        'avg_volume': float(data['Volume'].mean()),
        'high_volume_periods': int((data['Volume'] > data['Volume'].mean()).sum()),

        # Rachas
        'up_periods': int((data['Close'] > data['Open']).sum()),
        'down_periods': int((data['Close'] < data['Open']).sum()),

        # Drawdown
        'max_drawdown': float(drawdons.min()),
        'avg_drawdown': float(drawdons.mean()),
        'std_drawdown': float(drawdons.std()),  

        # Retornos
        'cumulative_return': float(data['Close'].iloc[-1] / data['Close'].iloc[0]),
        'avg_period_return': float(returns.mean()),
        'volatility': float(returns.std()),
    }

    return basic_stats
