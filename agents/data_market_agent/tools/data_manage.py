"""data_manage.py"""
import os
from datetime import datetime

import pandas as pd
import yfinance as yf

from langchain_core.tools import tool

@tool
def get_data_yfinance(
    ticker: str,
    period: str,
    interval: str
    ) -> pd.DataFrame:
    """Tool para descargar los datos de yfinance"""
    try:
        date = int(str(datetime.now().date()).replace('-', ''))

        data = yf.download(
            [ticker],
            period=period,
            interval=interval,
            auto_adjust=False
        ).reset_index()

        if data.empty:
            return f"""
                No se encontraron datos para {ticker}
                en el periodo {period} con intervalo {interval}
            """

        data.columns = [i[0] for i in data.columns]
        os.makedirs('./Data', exist_ok=True)
        data.to_csv(f'./Data/data_{ticker}_{date}.csv', index=False)

        return data

    except Exception as e:
        return f"""
            Error en get_data_yfinance: {str(e)}
        """
