import json
import os
from urllib.request import urlopen
import certifi
from datetime import datetime
import pandas as pd
import numpy as np

# Get the API key from the environment variable
apikey = os.getenv('FMP_API_KEY')

# Check if the API key is set
if not apikey:
    raise ValueError("API key not found. Please set the environment variable 'FMP_API_KEY'.")

def fmp_price(syms, start='1960-01-01', end=str(datetime.now().date()), facs=['close']):
    '''
    Historical Price - Single Symbol - Multiple Facs
    sym: string for single symbol as in 'SPY' with no []
    start/end = string like 'YYYY-mm-dd'
    facs= returns any of: 'open', 'high', 'low', 'close', 'adjClose', 'volume', 'unadjustedVolume', 
    'change', 'changePercent', 'vwap', 'label', 'changeOverTime' with facs as column names 
    returns: DF with facs as the columns
    '''
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{syms}?from={start}&to={end}&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff = json.loads(data)
    l = stuff['historical'] 
    idx = [sub['date'] for sub in l]
    idx = pd.to_datetime(idx)
    df = pd.DataFrame([[sub[k] for k in facs] for sub in l], columns=facs, index=idx)
    return df.iloc[::-1]

def fmp_intra(sym, period='30min'):
    """
    Get intraday data for a symbol
    """
    url = f'https://financialmodelingprep.com/api/v3/historical-chart/{period}/{sym}?apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    result = json.loads(data)
    if result:
        # Convert dates to datetime objects and sort
        for item in result:
            item['date'] = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
        result.sort(key=lambda x: x['date'], reverse=True)
    return result

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
    return json.loads(data)

def fmp_earnSym(sym, n=5):
    """
    input: symbol as string
           n as int.  the number of quarters to return
    returns:  historical and future earnings dates, times and estimates
    """
    url = f"https://financialmodelingprep.com/api/v3/historical/earning_calendar/{sym}?apikey={apikey}"
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    result = json.loads(data)
    if result:
        # Convert dates to datetime objects
        for item in result:
            item['date'] = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
        # Sort by date descending (newest first) and take first n items
        result.sort(key=lambda x: x['date'], reverse=True)
        result = result[:n]
        # Sort back to ascending (oldest first) for display
        result.sort(key=lambda x: x['date'])
    return result

def fmp_div(sym, num=13):
    """
    Get dividend history with yield calculations
    """
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{sym}?apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    result = json.loads(data)
    
    if 'historical' in result:
        # Convert to DataFrame
        df = pd.DataFrame(result['historical'])
        df = df.drop(columns=['label'])
        df = df.rename(columns={'date': 'exDate'})
        df.set_index('exDate', inplace=True)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        # Calculate trailing dividends (last 359 days)
        df['trail'] = df.adjDividend.rolling(window='359D').sum()
        
        # Get price data for yield calculations using fmp_price
        price = fmp_price(sym, start=df.index[0].strftime('%Y-%m-%d'))
        price.index = pd.to_datetime(price.index)
        newdf = pd.concat([df, price.reindex(df.index)], axis=1)
        
        # Calculate yields
        dividend_count = df['dividend'].rolling(window='360D').count().iloc[-1]  # Get the last value
        newdf['trailYield'] = np.round(newdf.trail/newdf.close*100, 2)
        newdf['curYield'] = np.round(newdf.adjDividend*dividend_count/newdf.close*100, 2)
        
        # Take the most recent num rows
        newdf = newdf.tail(num)
        
        # Convert back to list of dictionaries for frontend
        result = []
        for date, row in newdf.iterrows():
            result.append({
                'date': date.isoformat(),
                'dividend': row['adjDividend'],
                'stockPrice': row['close'],
                'trailYield': row['trailYield'],
                'curYield': row['curYield'],
                'recordDate': row.get('recordDate'),
                'paymentDate': row.get('paymentDate'),
                'declarationDate': row.get('declarationDate')
            })
        return result
    return [] 

def fmp_close(sym, n=1):
    """
    Get the last n closing prices for a symbol
    """
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{sym}?timeseries={n}&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    result = json.loads(data)
    if 'historical' in result:
        return result['historical']
    return []

def fmpw_rt(sym):
    """Fetch real-time stock quote data and calculate price metrics.
    
    Args:
        sym (str): Stock symbol (e.g., 'LXS.DE', 'FXE').
    
    Returns:
        dict: Dictionary containing stock metrics:
            - price (float): Current stock price
            - chg (numpy.float64): Price change from previous close (rounded to 2 decimals)
            - ret (numpy.float64): Percentage return from previous close (rounded to 2 decimals)
            Returns {'price': None, 'chg': None, 'ret': None} if data is unavailable.
    
    Raises:
        IndexError: If no price data is available from the API, prints a message and
                   returns a dictionary with None values.
        URLError: If the API request fails (handled by urlopen).
    
    Example:
        >>> fmpw_rt('LXS.DE')
        {'price': 31.92, 'chg': np.float64(4.23), 'ret': np.float64(15.28)}
        >>> fmpw_rt('INVALID')
        INVALID : No Price Data Available
        {'price': None, 'chg': None, 'ret': None}
    
    Notes:
        - Requires an API key stored in `apikey` variable.
        - Uses Financial Modeling Prep API for quote data.
        - Depends on external `fmp_close` function for previous close data.
        - Requires `fmp`, `numpy`, `json`, `urllib.request`, and `certifi` modules.
    """
    rturl = f'https://financialmodelingprep.com/api/v3/quote-short/{sym}?apikey={apikey}'
    response = urlopen(rturl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff = json.loads(data)
    
    try:
        p = stuff[0]['price']
        # when the market is trading prev day close is lbk=2
        pc = fmp_close(sym, 2)[0]['close']
        return {
            'price': p,
            'chg': np.round(p-pc, 2),
            'ret': np.round(((p/pc)-1)*100, 2)
        }
        
    except IndexError:
        print(sym, ':  No Price Data Available')
        
    return {'price': None, 'chg': None, 'ret': None} 