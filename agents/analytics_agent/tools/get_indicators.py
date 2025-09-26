"""analytics_agent/tools/get_indicators.py"""
import pandas as pd


def calculate_sma(df: pd.DataFrame, window: int = 20):
    """Calcula el SMA (Simple Moving Average) para un DataFrame de precios.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['Close', 'Volume', ...]
        window (int): Tamaño de la ventana para el SMA

    Returns:
        pd.Series: Serie con los valores del SMA
    """
    sma = df['Close'].rolling(window=window).mean()

    return sma

def calculate_ema(df: pd.DataFrame, window: int = 20):
    """Calcula el EMA (Exponential Moving Average) para un DataFrame de precios.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['Close', 'Volume', ...]
        window (int): Tamaño de la ventana para el EMA

    Returns:
        pd.Series: Serie con los valores del EMA
    """
    ema = df["Close"].ewm(span=window, adjust=False).mean()
    return ema

def calculate_rsi(df: pd.DataFrame, window: int = 14):
    """Calcula el RSI (Relative Strength Index) para un DataFrame de precios.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['Close', 'Volume', ...]
        window (int): Tamaño de la ventana para el RSI

    Returns:
        pd.Series: Serie con los valores del RSI
    """
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(
    df: pd.DataFrame,
    short_window: int = 12,
    long_window: int = 26,
    signal_window: int = 9,
):
    """Calcula el MACD (Moving Average Convergence Divergence) para un DataFrame de precios.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['Close', 'Volume', ...]
        short_window (int): Tamaño de la ventana para el EMA corto
        long_window (int): Tamaño de la ventana para el EMA largo
        signal_window (int): Tamaño de la ventana para el EMA de la señal

    Returns:
        tuple: Tupla con las series de valores del MACD, la señal y el histograma
    """
    ema_short = calculate_ema(df, short_window)
    ema_long = calculate_ema(df, long_window)
    macd_line = ema_short - ema_long
    signal_line = macd_line.ewm(span=signal_window, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: int = 2):
    """Calcula las bandas de Bollinger para un DataFrame de precios.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['Close', 'Volume', ...]
        window (int): Tamaño de la ventana para el SMA
        num_std (int): Número de desviaciones estándar para las bandas

    Returns:
        tuple: Tupla con las series de valores de las bandas superiores, medios y inferiores
    """
    sma = calculate_sma(df, window)
    rolling_std = df["Close"].rolling(window=window).std()
    upper_band = sma + (rolling_std * num_std)
    lower_band = sma - (rolling_std * num_std)
    return upper_band, sma, lower_band

def get_technical_indicators(df: pd.DataFrame, mode: str = "full"):
    """Calcula indicadores técnicos para un DataFrame de precios.

    Args:
        df (pd.DataFrame): DataFrame con columnas ['Close', 'Volume', ...]
        mode (str): "full" para devolver todo el DataFrame con columnas de indicadores,
                    "last" para devolver solo el último valor de cada indicador.

    Returns:
        pd.DataFrame | dict
    """
    df = df.copy()

    # SMA y EMA
    df["SMA_20"] = calculate_sma(df, 20)
    df["EMA_20"] = calculate_ema(df, 20)

    # RSI
    df["RSI_14"] = calculate_rsi(df, 14)

    # MACD
    macd_line, signal_line, histogram = calculate_macd(df)
    df["MACD_line"] = macd_line
    df["MACD_signal"] = signal_line
    df["MACD_histogram"] = histogram

    # Bollinger Bands
    upper, middle, lower = calculate_bollinger_bands(df)
    df["BB_upper"] = upper
    df["BB_middle"] = middle
    df["BB_lower"] = lower

    if mode == "last":
        return {
            "SMA_20": float(df["SMA_20"].iloc[-1]),
            "EMA_20": float(df["EMA_20"].iloc[-1]),
            "RSI_14": float(df["RSI_14"].iloc[-1]),
            "MACD": {
                "line": float(df["MACD_line"].iloc[-1]),
                "signal": float(df["MACD_signal"].iloc[-1]),
                "histogram": float(df["MACD_histogram"].iloc[-1]),
            },
            "BollingerBands": {
                "upper": float(df["BB_upper"].iloc[-1]),
                "middle": float(df["BB_middle"].iloc[-1]),
                "lower": float(df["BB_lower"].iloc[-1]),
            },
        }
    return df
