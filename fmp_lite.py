import pandas as pd
import datetime as dt
import json
import os
from urllib.request import urlopen
import certifi
from requests.utils import requote_uri

# Get the API key from the environment variable
apikey = os.getenv('FMP_API_KEY')

# Check if the API key is set
if not apikey:
    raise ValueError("API key not found. Please set the environment variable 'FMP_API_KEY'.")

def fmp_intra(sym, period='30min'):
    """
    Get intraday data for a symbol
    """
    url = f'https://financialmodelingprep.com/api/v3/historical-chart/{period}/{sym}?apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    df = pd.DataFrame(json.loads(data))
    if not df.empty:
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
    return df

def fmp_profF(sym):
    """
    Get company profile
    """
    url = f'https://financialmodelingprep.com/api/v3/profile/{sym}?apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    result = json.loads(data)
    return result[0] if result else None

def fmp_search(searchterm):
    """
    Search for symbols
    """
    url = f'https://financialmodelingprep.com/api/v3/search?query={searchterm}&limit=10&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    df = pd.DataFrame(json.loads(data))
    return df

def fmp_earnSym(sym, n=5):
    """
    Get earnings dates for a symbol
    """
    url = f'https://financialmodelingprep.com/api/v3/earnings-calendar/{sym}?limit={n}&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    df = pd.DataFrame(json.loads(data))
    return df

def fmp_div(sym, num=10):
    """
    Get dividend history
    """
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{sym}?apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    result = json.loads(data)
    if 'historical' in result:
        df = pd.DataFrame(result['historical'])
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
        return df
    return pd.DataFrame() 