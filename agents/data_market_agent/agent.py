"""data_market_agent/agent.py"""
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from tools.data_manage import get_data_yfinance

from dotenv import load_dotenv

load_dotenv()

def run_agent(
    ticker: str,
    period: str = '1mo',
    interval: str = '1d'
    ) -> str:
    """Ejecución del agente de manejo de datos del mercado

    Args:
        ticker (str): Identificador del activo financiero

    Returns:
        str: Respuesta del modelo
    """
    agent = create_react_agent(
        model = ChatOpenAI(model='gpt-4o'),
        tools = [get_data_yfinance]
    )

    response = agent.invoke({
        'messages': [{
            'role': 'user',
            'content': f'''
                Obtener los registros de la data de {ticker}
                para el periodo {period}, con el intervalo: {interval}
            '''
        }]
    })

    result = response['messages'][-1].content

    return result

if __name__ ==  '__main__':
    ticker = input('Introduce el ticker: ')
    period = input('Introduce el periodo: ')
    interval = input('Introduce el intervalo: ')

    final_response = run_agent(ticker, period, interval)

    print(final_response)
