#version 1.0.5  updated 2/17/25 added acceptance date as a fmp_incts factor

import time
import certifi
import pandas as pd
import numpy as np
import datetime as dt
import json
import re
import logging
logging.captureWarnings(True)
from collections import defaultdict
from urllib.request import urlopen
from urllib.parse import urlencode
import requests   
from datetime import datetime 
from tqdm import tqdm
from requests.utils import requote_uri
import os

# Get the API key from the environment variable
apikey = os.getenv('FMP_API_KEY')

# Check if the API key is set
if not apikey:
    raise ValueError("API key not found. Please set the environment variable 'FMP_API_KEY'.")


#-----------------------------------------------------  

def fmp_price(syms, start='1960-01-01', end=str(dt.datetime.now().date()), facs=['close']):
    '''
    Historical Price - Single Symbol - Multiple Facs
    sym: string for single symbol as in 'SPY' with no []
    start/end = string like 'YYYY-mm-dd'
    facs= returns any of: 'open', 'high', 'low', 'close', 'adjClose', 'volume', 'unadjustedVolume', 
    'change', 'changePercent', 'vwap', 'label', 'changeOverTime' with facs as column names 
    returns: DF with facs as the columns
    '''
    
    
   
    url=requote_uri(f'https://financialmodelingprep.com/api/v3/historical-price-full/{syms}?from={start}&to={end}&apikey={apikey}')
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    l=stuff['historical'] 
    idx = [sub['date'] for sub in l]
    idx=pd.to_datetime(idx)
    df = pd.DataFrame([[sub[k] for k in facs] for sub in l], columns=facs, index=idx)
    return df.iloc[::-1]


#-----------------------------------------------------
def fmp_priceMult(syms, start='1960-01-01', end=str(dt.datetime.now().date()), fac='adjClose'):
    
    '''
    Historical Price limited to 1 year. - Mutiple Symbols - Single Fac
    ***Max 5 symbols... returns the 1st 5 symbols without error***
    syms: list of strings separated by commas ['SPY,'TLT']
    start/end = string like 'YYYY-mm-dd'
    facs= returns any of: 'open', 'high', 'low', 'close', 'adjClose', 'volume', 'unadjustedVolume', 
    'change', 'changePercent', 'vwap', 'label', 'changeOverTime' with facs as column names 
    returns: Df with syms as columns
    '''
    syms=tuple(syms)
    syms=','.join(syms)

    url=requote_uri('https://financialmodelingprep.com/api/v3/historical-price-full/'+syms+'?from='+start+'&to='+end+'&apikey='+apikey)
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    data=stuff['historicalStockList'] 
    idx=[x['date'] for x in data[0]['historical']]
    idx=pd.to_datetime(idx)
    df = pd.DataFrame({d['symbol']: [x[fac] for x in d['historical']] for d in data}, 
                  index=idx)

    print ('fac= ', fac)
    return df.iloc[::-1]



#----------------------------------------------------------------------------


def fmp_priceLoop(syms, start='1960-01-01', end=str(dt.datetime.now().date()), fac='close', supress=True):
    '''
    Multi Symbols no limit on history.
    sym: string or a list of strings
    start/end = string like 'YYYY-mm-dd'
    facs= returns one of: 'open', 'high', 'low', 'close', 'adjClose', 'volume', 'unadjustedVolume', 
    'change', 'changePercent', 'vwap', 'label', 'changeOverTime' with facs as column names
    returns df: for single sym column names are facs, for mult sym column names are sym:facs
    '''
    df=pd.DataFrame()
    if supress:
        for i in syms:
            dff=fmp_price(i, start=start, end=end, facs=[fac])
            df[i]=dff
      
    else:
        for i in tqdm(syms, disable=False):
            dff=fmp_price(i, start=start, end=end, facs=[fac])
            df[i]=dff
   
    return df

#-----------------------------------------------------

def fmp_priceLbk(sym, date,facs=['close']):  
    '''
    inputs sym: single symbol as a string,
           date: 'YYYY-mm-dd' as a string
           facs: "date", "open","high", "low", "close", "adjClose",
           "volume", "unadjustedVolume", "change", "changePercent",
           "vwap", "label", "changeOverTime"
           
    '''
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{sym}?from={date}&to={date}&apikey={apikey}"
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff = json.loads(data)
    l = stuff['historical'][0]
    return [l[key] for key in facs]
#--------------------------------------------------------    
def fmp_spread(long, short, start='1960-01-01', end=str(dt.datetime.now().date()), ratio=False):
    '''
    long: string long symbol
    short: string short symbol
    start/end = string like 'YYYY-mm-dd'
    ratio: bool, long / short (default is long - short)
    '''
    syms = [long, short]
    df=pd.DataFrame()
    
    if ratio:
        for i in syms:
            dff=fmp_price(i, start=start, end=end).pct_change().cumsum()
            df=pd.concat([df,dff], axis=1)
            df=df.dropna()
        df['spread'] = df.iloc[:,[0]]/df.iloc[:,[1]]
    else:
        for i in syms:
            dff=fmp_price(i, start=start, end=end).pct_change().cumsum()
            df=pd.concat([df,dff], axis=1)
            df=df.dropna()
        df['spread'] = df.iloc[:,[0]]-df.iloc[:,[1]]
    return df.spread




#-----------------------------------------------------

def fmp_mcap(sym):
    '''
input: symbols as a string
outputs: dataframe of marketcap values with a datetime index
    '''
    df=fmp_entts(sym, facs=['numberOfShares'])
    dfp=fmp_price(sym)
    dff = pd.concat([df, dfp], axis=1)
    dff.ffill(inplace=True)
    dff.dropna(inplace=True)
    dff['mktCap']=(dff.numberOfShares*dff.close) 
    return dff.mktCap

#-----------------------------------------------------

def fmp_balts(sym, facs=None, period='quarter'):
    '''
    
	facs: LIST = ['date', 'symbol', 'reportedCurrency', 'fillingDate', 'acceptedDate',
       'period', 'cashAndCashEquivalents', 'shortTermInvestments',
       'cashAndShortTermInvestments', 'netReceivables', 'inventory',
       'otherCurrentAssets', 'totalCurrentAssets', 'propertyPlantEquipmentNet',
       'goodwill', 'intangibleAssets', 'goodwillAndIntangibleAssets',
       'longTermInvestments', 'taxAssets', 'otherNonCurrentAssets',
       'totalNonCurrentAssets', 'otherAssets', 'totalAssets',
       'accountPayables', 'shortTermDebt', 'taxPayables', 'deferredRevenue',
       'otherCurrentLiabilities', 'totalCurrentLiabilities', 'longTermDebt',
       'deferredRevenueNonCurrent', 'deferredTaxLiabilitiesNonCurrent',
       'otherNonCurrentLiabilities', 'totalNonCurrentLiabilities',
       'otherLiabilities', 'totalLiabilities', 'commonStock',
       'retainedEarnings', 'accumulatedOtherComprehensiveIncomeLoss',
       'othertotalStockholdersEquity', 'totalStockholdersEquity',
       'totalLiabilitiesAndStockholdersEquity', 'totalInvestments',
       'totalDebt', 'netDebt']
    period = quarter, year
    
    '''
  
    if facs==None:
        full=['date', 'symbol', 'reportedCurrency', 
       'period', 'cashAndCashEquivalents', 'shortTermInvestments',
       'cashAndShortTermInvestments', 'netReceivables', 'inventory',
       'otherCurrentAssets', 'totalCurrentAssets', 'propertyPlantEquipmentNet',
       'goodwill', 'intangibleAssets', 'goodwillAndIntangibleAssets',
       'longTermInvestments', 'taxAssets', 'otherNonCurrentAssets',
       'totalNonCurrentAssets', 'otherAssets', 'totalAssets',
       'accountPayables', 'shortTermDebt', 'taxPayables', 'deferredRevenue',
       'otherCurrentLiabilities', 'totalCurrentLiabilities', 'longTermDebt',
       'deferredRevenueNonCurrent', 'deferredTaxLiabilitiesNonCurrent',
       'otherNonCurrentLiabilities', 'totalNonCurrentLiabilities',
       'otherLiabilities', 'totalLiabilities', 'commonStock',
       'retainedEarnings', 'accumulatedOtherComprehensiveIncomeLoss',
       'othertotalStockholdersEquity', 'totalStockholdersEquity',
       'totalLiabilitiesAndStockholdersEquity', 'totalInvestments',
       'totalDebt', 'netDebt']	
        facs=full
    sym=sym.upper()
    url='https://financialmodelingprep.com/api/v3/balance-sheet-statement/'+sym+'?period='+period+'&limit=400&apikey='+apikey
   
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    idx = [sub['date'] for sub in stuff]
    idx=pd.to_datetime(idx)
	
	 #[[sub[k] for k in keys] for sub in ld] to extract values from a list of keys as would be used in a function.  
    # ie: the user selects the keys in the function.see below where k is items in list of function paramater values see: facs=[last of parameters/keys]
	# and l is a list of dicts
	
    df = pd.DataFrame([[sub[k] for k in facs] for sub in stuff], columns=facs, index=idx)
   
    return df.iloc[::-1]
	
#-----------------------------------------------------------------------------

def fmp_incts(sym, facs=None, period='quarter'):
    '''
    ######stmt = income-statement, balance-sheet-statement, cash-flow-statement, enterprise-values####
	facs = ['date', 'symbol', 'reportedCurrency', 'fillingDate', 'acceptedDate',
       'period', 'revenue', 'costOfRevenue', 'grossProfit', 'grossProfitRatio',
       'researchAndDevelopmentExpenses', 'generalAndAdministrativeExpenses',
       'sellingAndMarketingExpenses',
       'sellingGeneralAndAdministrativeExpenses', 'otherExpenses',
       'operatingExpenses', 'costAndExpenses', 'interestExpense',
       'depreciationAndAmortization', 'ebitda', 'ebitdaratio',
       'operatingIncome', 'operatingIncomeRatio',
       'totalOtherIncomeExpensesNet', 'incomeBeforeTax',
       'incomeBeforeTaxRatio', 'incomeTaxExpense', 'netIncome',
       'netIncomeRatio', 'eps', 'epsdiluted', 'weightedAverageShsOut',
       'weightedAverageShsOutDil'
    period = quarter, year
    
    '''
  
    if facs==None:
        full=['date','acceptedDate', 'symbol', 'reportedCurrency',
       'period', 'revenue', 'costOfRevenue', 'grossProfit', 'grossProfitRatio',
       'researchAndDevelopmentExpenses', 'generalAndAdministrativeExpenses',
       'sellingAndMarketingExpenses',
       'sellingGeneralAndAdministrativeExpenses', 'otherExpenses',
       'operatingExpenses', 'costAndExpenses', 'interestExpense',
       'depreciationAndAmortization', 'ebitda', 'ebitdaratio',
       'operatingIncome', 'operatingIncomeRatio',
       'totalOtherIncomeExpensesNet', 'incomeBeforeTax',
       'incomeBeforeTaxRatio', 'incomeTaxExpense', 'netIncome',
       'netIncomeRatio', 'eps', 'epsdiluted', 'weightedAverageShsOut',
       'weightedAverageShsOutDil']	
        facs=full
    sym=sym.upper()
    
  
    url='https://financialmodelingprep.com/api/v3/income-statement/'+sym+'?period='+period+'&limit=400&apikey='+apikey
   
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    idx = [sub['date'] for sub in stuff]
    idx=pd.to_datetime(idx)

    df = pd.DataFrame([[sub[k] for k in facs] for sub in stuff], columns=facs, index=idx)
   
    return df.iloc[::-1]	
#-----------------------------------------------------
def fmp_entts(sym, facs=None, period='quarter'):
    '''
   
	facs = ['symbol', 'date', 'stockPrice', 'numberOfShares', 'marketCapitalization', 
    'minusCashAndCashEquivalents', 'addTotalDebt', 'enterpriseValue']
    period = quarter, year
    
    '''
  
    if facs==None:
        full=['date', 'numberOfShares', 
              'minusCashAndCashEquivalents', 
              'addTotalDebt']	
        facs=full
    sym=sym.upper()
    
  
    url='https://financialmodelingprep.com/api/v3/enterprise-values/'+sym+'?period='+period+'&limit=400&apikey='+apikey
   
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    idx = [sub['date'] for sub in stuff]
    idx=pd.to_datetime(idx)

    df = pd.DataFrame([[sub[k] for k in facs] for sub in stuff], columns=facs, index=idx)
   
    return df.iloc[::-1]	
    
#-----------------------------------------------------	

def fmp_cashfts(sym, facs=None, period='quarter'):
    '''
    ######stmt = income-statement, balance-sheet-statement, cash-flow-statement, enterprise-values####
	facs = ['date', 'symbol', 'reportedCurrency', 'fillingDate', 'acceptedDate', 'period', 'netIncome', 
    'depreciationAndAmortization', 'deferredIncomeTax', 'stockBasedCompensation', 
    'changeInWorkingCapital', 'accountsReceivables', 'inventory', 'accountsPayables', 
    'otherWorkingCapital', 'otherNonCashItems', 'netCashProvidedByOperatingActivities', 
    'investmentsInPropertyPlantAndEquipment', 'acquisitionsNet', 'purchasesOfInvestments', 
    'salesMaturitiesOfInvestments', 'otherInvestingActivites', 'netCashUsedForInvestingActivites', 
    'debtRepayment', 'commonStockIssued', 'commonStockRepurchased', 'dividendsPaid', 'otherFinancingActivites', 
    'netCashUsedProvidedByFinancingActivities', 'effectOfForexChangesOnCash', 'netChangeInCash', 
    'cashAtEndOfPeriod', 'cashAtBeginningOfPeriod', 'operatingCashFlow', 'capitalExpenditure', 
    'freeCashFlow', 'link', 'finalLink']
    
    period = quarter, year
    
    '''
  
    if facs==None:
         full=['date', 'symbol', 'reportedCurrency', 'period', 'netIncome', 
    'depreciationAndAmortization', 'deferredIncomeTax', 'stockBasedCompensation', 
    'changeInWorkingCapital', 'accountsReceivables', 'inventory', 'accountsPayables', 
    'otherWorkingCapital', 'otherNonCashItems', 'netCashProvidedByOperatingActivities', 
    'investmentsInPropertyPlantAndEquipment', 'acquisitionsNet', 'purchasesOfInvestments', 
    'salesMaturitiesOfInvestments', 'otherInvestingActivites', 'netCashUsedForInvestingActivites', 
    'debtRepayment', 'commonStockIssued', 'commonStockRepurchased', 'dividendsPaid', 'otherFinancingActivites', 
    'netCashUsedProvidedByFinancingActivities', 'effectOfForexChangesOnCash', 'netChangeInCash', 
    'cashAtEndOfPeriod', 'cashAtBeginningOfPeriod', 'operatingCashFlow', 'capitalExpenditure', 
    'freeCashFlow', 'link', 'finalLink']	
         facs=full
    sym=sym.upper()
    
  
    url='https://financialmodelingprep.com/api/v3/cash-flow-statement/'+sym+'?period='+period+'&limit=400&apikey='+apikey
   
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    idx = [sub['date'] for sub in stuff]
    idx=pd.to_datetime(idx)

    df = pd.DataFrame([[sub[k] for k in facs] for sub in stuff], columns=facs, index=idx)
   
    return df.iloc[::-1]

#-----------------------------------------------------

#https://financialmodelingprep.com/api/v3/historical-chart/1min/BTCUSD?apikey=

def fmp_intra(sym, period='1hour'):
    """
    sym = single symbol as a string (not case sensitive)
    period = '1day' returns:  'adjClose', 'change', 'changeOverTime', 'changePercent', 'close','high', 'label', 'low', 'open', 'unadjustedVolume', 'volume', 'vwap'
    period = '1min', '5min', '15min', '30min', '1hour' returns:  'close', 'high', 'low', 'open', 'volume'

    """

    if period=='1day':
        url = "https://financialmodelingprep.com/api/v3/historical-price-full/"+sym.upper()+"?apikey="+apikey
        response = urlopen(url, cafile=certifi.where())
        data = response.read().decode("utf-8")
        return pd.DataFrame(json.loads(data)['historical']).set_index('date').sort_index(ascending=True)
    else:
        url = "https://financialmodelingprep.com/api/v3/historical-chart/"+period+"/"+sym.upper()+"?apikey="+apikey
        return pd.read_json(url).set_index('date').sort_index(ascending=True)
		
#-----------------------------------------------------

def fmp_plot_ts(ts, step=5, figsize=(10,7), title=''):
    """
    plot timeseries ignoring date gaps

    Params
    ------
    ts : pd.DataFrame or pd.Series
    step : int, display interval for ticks
    figsize : tuple, figure size
    title: str
    """

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(range(ts.dropna().shape[0]), ts.dropna())
    ax.set_title(title)
    ax.set_xticks(np.arange(len(ts.dropna())))
    ax.set_xticklabels(ts.dropna().index.tolist());

    # tick visibility, can be slow for 200,000+ ticks 
    xticklabels = ax.get_xticklabels() # generate list once to speed up function
    for i, label in enumerate(xticklabels):
        if not i%step==0:
            label.set_visible(False)  
    fig.autofmt_xdate()   
    ax.xaxis.grid(True, 'major')		
	
#-----------------------------------------------------

def fmp_search(searchterm):
    '''
    for exchange searches:  ETF | MUTUAL_FUND | COMMODITY | INDEX | CRYPTO | FOREX | TSX | AMEX | NASDAQ | NYSE | EURONEXT
    
    '''
    searchurl='https://financialmodelingprep.com/api/v3/search?query='+searchterm+'&limit=1000&apikey='+apikey
    response = urlopen(searchurl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    df= pd.DataFrame(stuff)[['symbol', 'name']]
    pd.set_option('display.max_rows', len(df)+1)
    df.sort_values('name',inplace=True)
    return df.set_index('symbol')	

        
#-------------------------------------------------------


def fmp_mergarb(syms, shar_fact=1, cash=0, start='1960-01-01', per=True):
    '''
    syms:  list of 2 symbols as strings.  acquirer first, acquired second.
           ex: ['CNI', 'KSU']
    shar_fact: float, number of shareds of acquirer that acquired is receiving
    cash: amount of cash per share acquired is recieving
    per: bool.  True returns spread as percentage of acquired,
                False returns spread as a float
    
    returns a df of acquirer price, acquired price, and Arb calculation with 
    columns sym1, sym2, and Arb
      
    
    '''
    df=fmp_multprice(syms, start, facs=['close'])
    if per==True:
        df['arb']= ((df.iloc[:,0]*shar_fact+cash)-df.iloc[:,1])/df.iloc[:,1]
    else:
        df['arb']= df.iloc[:,0]*shar_fact+cash-df.iloc[:,1]   
    return df	
	
#---------------------------------------------------------------------


def fmp_screen(**kwargs):
    """
    Uses the Financial Modeling Prep Screen API to filter companies based on criteria.

    Parameters:
        sector (str, optional): Sector to filter by.
        industry (str, optional): Industry to filter by.
        country (str, optional): Country to filter by.
            
    ex:  fmp_screen(county='US', marketCapMoreThan='1000000000 ', industry='Insurance—Life')
        
    Sectors and Industries
    
    Basic Materials:

Agricultural Inputs
Aluminum
Chemicals
Chemicals - Specialty
Construction Materials
Copper
Gold
Industrial Materials
Other Precious Metals
Paper, Lumber & Forest Products
Silver
Steel

Communication Services:

Advertising Agencies
Broadcasting
Entertainment
Internet Content & Information
Publishing
Telecommunications Services

Consumer Cyclical:

Apparel - Footwear & Accessories
Apparel - Manufacturers
Apparel - Retail
Auto - Dealerships
Auto - Manufacturers
Auto - Parts
Auto - Recreational Vehicles
Department Stores
Furnishings, Fixtures & Appliances
Gambling, Resorts & Casinos
Home Improvement
Leisure
Luxury Goods
Packaging & Containers
Personal Products & Services
Residential Construction
Restaurants
Specialty Retail
Travel Lodging
Travel Services

Consumer Defensive:

Agricultural Farm Products
Beverages - Alcoholic
Beverages - Non-Alcoholic
Beverages - Wineries & Distilleries
Discount Stores
Education & Training Services
Food Confectioners
Food Distribution
Grocery Stores
Household & Personal Products
Packaged Foods
Tobacco

Energy:

Coal
Energy
Oil & Gas Drilling
Oil & Gas Equipment & Services
Oil & Gas Exploration & Production
Oil & Gas Integrated
Oil & Gas Midstream
Oil & Gas Refining & Marketing
Solar
Uranium

Financial Services:

Asset Management
Asset Management - Bonds
Asset Management - Cryptocurrency
Asset Management - Global
Asset Management - Income
Asset Management - Leveraged
Banks
Banks - Diversified
Banks - Regional
Financial - Capital Markets
Financial - Conglomerates
Financial - Credit Services
Financial - Data & Stock Exchanges
Financial - Mortgages
Insurance - Brokers
Insurance - Diversified
Insurance - Life
Insurance - Property & Casualty
Insurance - Reinsurance
Insurance - Specialty
Investment - Banking & Investment Services
Shell Companies

Healthcare:

Biotechnology
Drug Manufacturers - General
Drug Manufacturers - Specialty & Generic
Healthcare
Medical - Care Facilities
Medical - Devices
Medical - Diagnostics & Research
Medical - Distribution
Medical - Equipment & Services
Medical - Healthcare Information Services
Medical - Healthcare Plans
Medical - Instruments & Supplies
Medical - Pharmaceuticals
Medical - Specialties

Industrials:

Aerospace & Defense
Agricultural - Machinery
Air Freight/Couriers
Airlines, Airports & Air Services
Business Equipment & Supplies
Conglomerates
Construction
Consulting Services
Electrical Equipment & Parts
Engineering & Construction
Industrial - Distribution
Industrial - Infrastructure Operations
Industrial - Machinery
Industrial - Pollution & Treatment Controls
Integrated Freight & Logistics
Manufacturing - Metal Fabrication
Manufacturing - Miscellaneous
Manufacturing - Tools & Accessories
Marine Shipping
Railroads
Rental & Leasing Services
Security & Protection Services
Specialty Business Services
Staffing & Employment Services
Trucking
Waste Management
Wholesale Distributors

Real Estate:

REIT - Diversified
REIT - Healthcare Facilities
REIT - Hotel & Motel
REIT - Industrial
REIT - Mortgage
REIT - Office
REIT - Residential
REIT - Retail
REIT - Specialty
Real Estate - Development
Real Estate - Diversified
Real Estate - General
Real Estate - Services

Technology:

Communication Equipment
Computer Hardware
Consumer Electronics
Electronic Gaming & Multimedia
Hardware, Equipment & Parts
Information Technology Services
Internet Software/Services
Semiconductors
Software - Application
Software - Infrastructure
Software - Services
Technology Distributors

Utilities:

Diversified Utilities
Independent Power Producers
Regulated Electric
Regulated Gas
Regulated Water
Renewable Utilities
    
    	Country:  'US', 'CN', 'TW', 'FR', 'CH', 'NL', 'CA', 'JP', 'DK', 'IE', 'AU',
           'GB', 'DE', 'SG', 'BE', 'IN', 'BR', 'ZA', 'AR', 'ES', 'NO', 'HK',
           'IT', 'MX', 'BM', 'LU', 'SE', 'FI', 'CO', 'KR', 'ID', 'JE', 'IL',
           'PT', 'UY', 'CL', 'MC', 'CY', 'MA', 'KY', 'RU', 'PR', 'PH', 'IS',
           'TR', 'IM', 'TH', 'PA', 'PE', 'GG', 'Peru', 'AE', 'NZ', 'GR', 'CR',
           'MY', 'BB', 'BS', 'GA', 'JO', 'VG', 'DO', 'ZM', 'MT', 'CK', 'MN',
           'LT', 'MO', 'AI'
           
    
        Returns:
            pd.DataFrame: A DataFrame with the filtered companies.
        """

    base_url = f"https://financialmodelingprep.com/api/v3/stock-screener"
    
    # Build query parameters dynamically based on provided filters
    params = {
        "apikey": apikey,
        "sector": kwargs.get("sector"),
        "industry": kwargs.get("industry"),
        "country": kwargs.get("country")
    }
    
    # Remove any parameters that are None
    params = {k: v for k, v in params.items() if v is not None}
    
    # Make the API request with the dynamic parameters
    response = requests.get(base_url, params=params)
    
    # Check if the request was successful
    if response.status_code != 200:
        print("Failed to retrieve data. Check your API key and internet connection.")
        return []
    
    data = response.json()
    
    if not data:
        print("No data fetched from the API with the provided filters.")
        return []
    
    print(f"Found {len(data)} stocks:")
    # Create DataFrame
    df = pd.DataFrame([ 
        [sub['symbol'], sub['companyName'], sub['sector'], sub['industry'], sub['country'], sub['marketCap'], sub['exchangeShortName']] 
        for sub in data
    ], columns=['symbol', 'companyName', 'sector', 'industry', 'country', 'marketCap', 'exchange'])

    # Convert market cap to millions without formatting it as a string initially
    df['marketCap(mil)'] = (df['marketCap'] / 1000000).round(0)

    # Sort by 'marketCap(mil)' in descending order while it is still numeric
    df.sort_values('marketCap(mil)', ascending=False, inplace=True)

    # Now format 'marketCap(mil)' with commas
    #df['marketCap(mil)'] = df['marketCap(mil)'].apply(lambda x: f"{int(x):,}")
    df['marketCap(mil)'] = df['marketCap(mil)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")

    # Drop the original 'marketCap' column
    df = df.drop('marketCap', axis=1)

    # Set 'symbol' as the index
    df.set_index('symbol', inplace=True)

    return df
    
    

#------------------------------------------------------------
def fmp_earnSym(sym, n=5):
    '''
    input: symbol as string
           n as int.  the number of quarters to return
    returns:  historical and future earnings dates, times and estimates
    '''
    url= f"https://financialmodelingprep.com/api/v3/historical/earning_calendar/{sym}?apikey={apikey}"
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data) 
    return pd.DataFrame(stuff).head(n).sort_values('date')
#------------------------------------------------------------------

def fmp_earnDateNext(sym):
    '''input (str) sym
       returns next earnings date as a string or 'NA' if there's a KeyError or no valid date'''
    
    try:
        df = fmp_earnSym(sym)
        # Convert 'date' column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter rows where 'eps' is NaN
        nan_eps_df = df[df['eps'].isna()]
        
        # Get the earliest 'date' where 'eps' is NaN
        earliest_date = nan_eps_df['date'].min()
        
        # Check if earliest_date is NaT (Not a Time)
        if pd.isna(earliest_date):
            return 'NA'
        
        return earliest_date.strftime('%Y-%m-%d')
    
    except KeyError:
        return 'NA'

#----------------------------------------------------------------------------------
def fmp_earnCal(start=str(dt.datetime.now().date()), end=str(dt.datetime.now().date())):
    '''
    input: start and end dates like 'XXXX-xx-xx'
    returns: a dataframe of symbols with date, time and estimates where available
    
    '''
    earnurl='https://financialmodelingprep.com/api/v3/earning_calendar?from='+start+'&to='+end+'&apikey='+apikey
    response = urlopen(earnurl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    df=pd.DataFrame(stuff).iloc[:,0:5]
    df.set_index('symbol', inplace=True)

####  having trouble concatting prof df and df  #######    
    
#    df.date=pd.to_datetime(df.date)
#    name = fmp_prof(df.index.tolist(), facs=['companyName', 'industry', 'mktCap'])
#    fin =  pd.concat([name,df], axis=1)
#    fin.sort_values(['date', 'time'], inplace=True, ascending=[True, False])
    return df
#----------------------------------------------------------------------------------

def fmp_earnEst(sym, period='quarter'):
    '''
    inputs: symbol as str
            period as string.  annual, quarter
            
    returns a dataframe with the following columns: 
    
            'RevLow', 'RevHigh', 'RevAvg', 
            'EbitdaLow', 'EbitdaHigh', 'EbitdaAvg', 'EbitLow', 
            'EbitHigh', 'EbitAvg', 'IncLow', 'IncHigh', 
            'IncAvg', 'SgaExpenseLow', 'SgaExpenseHigh', 
            'SgaExpenseAvg', 'EpsAvg', 'EpsHigh', 'EpsLow', 
            'NumAnalystRev', 'NumAnalystsEps'
    
    
    '''

    url= f"https://financialmodelingprep.com/api/v3/analyst-estimates/{sym}?period={period}&apikey={apikey}"
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data) 

    idx = [d['date'] for d in stuff]


    data = [{k: v for i, (k, v) in enumerate(item.items()) if 2 <= i < 22} for item in stuff]

    df=pd.DataFrame(data=data, index=idx)


    df.columns=columns=['RevLow', 'RevHigh', 'RevAvg', 
                       'EbitdaLow', 'EbitdaHigh', 'EbitdaAvg', 'EbitLow', 
                       'EbitHigh', 'EbitAvg', 'IncLow', 'IncHigh', 
                       'IncAvg', 'SgaExpenseLow', 'SgaExpenseHigh', 
                       'SgaExpenseAvg', 'EpsAvg', 'EpsHigh', 'EpsLow', 
                       'NumAnalystRev', 'NumAnalystsEps']
    return df
#--------------------------------------------------------------------------------------------

def fmp_ticker(sym):
    url = requote_uri('https://financialmodelingprep.com/api/v3/search-ticker?query='+sym+'&limit=1000&apikey='+apikey)
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    return stuff	
	
#---------------------------------------------------------------------------------------

def fmp_scaler(df, names=None):
    df_scaled=pd.DataFrame(StandardScaler().fit_transform(df), 
                columns=names, 
                index=df.index)
    return df_scaled         

#--------------------------------------------------------
def fmp_cumret(df):
    df=df.pct_change()
    df = (1 + df).cumprod() - 1
    df.iloc[0,:]=0
    return df
	
#-------------------------------------------------------------------------------------------

def fmp_cap(sym):
    '''
    Gross Cap is 4 quarters rolling sum of Revenue divided by current quarter Enterprise Value
    params sym: str
    returns: Series with date index and Gross Cap
    '''

    df=fmp_fund(sym, 'income-statement')['revenue']
    dff = fmp_fund(sym, 'enterprise-values')['enterpriseValue']
    condf=pd.concat([df,dff], axis=1)
    condf['cap'] = condf.revenue.rolling(4).sum()/condf.enterpriseValue
    return condf.cap	
#--------------------------------------------------------------------------------------------
def fmp_efficiency(sym):
    '''
    Gross Cap is 4 quarters rolling sum of G&A Exp  divided by current quarter Revenue
    params sym: str
    returns: Series with date index and Gross Cap
    '''

    df=fmp_fund(sym, 'income-statement')['revenue']
    dff = fmp_fund(sym, 'income-statement')["operatingIncome"]
    condf=pd.concat([df,dff], axis=1)
    condf['eff'] = condf.operatingIncome / condf.revenue
    return condf.eff
	
	
#-----------------------------------------------------------------------------------------

def fmp_div(sym, num=5):  
    '''
Declaration Date: This is the date on which the company's board of directors announces 
the upcoming dividend payment. It signifies the company's intention to pay a dividend.

Ex-Dividend Date: (Index)  The ex-dividend date is the first day following the declaration 
date on which a stock trades without the dividend included. If you purchase the stock on 
or after this date, you are not entitled to receive the dividend.

Record Date: The record date, also known as the ownership date, is the date on which the 
company determines the shareholders who are eligible to receive the dividend. You must be 
a registered shareholder on the record date to receive the dividend.

Payment Date: This is the date on which the dividend is actually paid to the eligible 
shareholders. It is the day when the dividend amount is credited to the shareholders' 
accounts or mailed out as physical checks.    

trailYield:  rolling last 4 dividends
currYield:  last dividend x 4
    '''

    url='https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/'+sym+'?apikey='+apikey

    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data) 
    df = pd.DataFrame(stuff['historical'])
    df = df.drop(columns=['label'])
    df = df.rename(columns={'date': 'exDate'})
    df.set_index('exDate', inplace=True)
    df.index = pd.to_datetime(df.index)
    df=df.sort_index()



    df['trail'] = df.adjDividend.rolling(window='359D').sum()
    price=fmp_price(sym, start=df.index[0].strftime('%Y-%m-%d'))
    price.index = pd.to_datetime(price.index)
    newdf = pd.concat([df,price.reindex(df.index)], axis=1)
    newdf['trailYield']= np.round(newdf.trail/newdf.close*100,2)

    num = df['dividend'].rolling(window='360D').count()[-1]

    newdf['curYield']= np.round(newdf.adjDividend*num/newdf.close*100,2)

    
    return newdf

#---------------------------------------------------------------------------------------	
def fmp_idx(syms, weights = None, rebal = 'once', fac= 'adjClose',start='1980-01-01',name='idx'):
    '''
	   syms: list of symbols
       weights: list of weights must = len(syms) and equal 1
       rebal:  'once', 'quarterly', or 'yearly' for rebalance period
       name: a label for the index, string
       returns: res.  The res object in the bt library is typically a bt.run.Result object, and it provides a variety of methods and attributes to 
       analyze the backtest results. Here is a list of some commonly used methods and attributes:

Methods
res.display()

Displays a summary of the performance statistics (e.g., total return, Sharpe ratio, max drawdown, etc.).
res.plot()

Plots the equity curve of the strategy and possibly other metrics depending on options passed.
res.prices

Returns the price series used in the backtest for each asset in the portfolio.
res.weights

Returns a DataFrame of the weights assigned to each asset over time.
res.stats

Returns a list of the performance statistics and other information related to the backtest.
res.get_transactions()

Returns a DataFrame with all the transactions executed during the backtest.
res.get_security_weights()

Returns a dictionary with weights for each security in the portfolio over time.
res.prices.plot()

Plots the price series (if you want to inspect the prices used in the backtest).
res.get_security_returns()

Returns the individual security returns.
Attributes
res.strategy

Provides access to the strategy used in the backtest, which allows you to inspect or modify it.
res.stats

The performance metrics of the strategy, often displayed in a summary format via display().
res.perf

The time series of the portfolio's performance over the backtest period.
res.assets

A list of assets that were included in the backtest.
res.rets

The portfolio's returns as a time series (returns from one time period to the next).
res.prices

The prices of the assets in the portfolio over time.
res.security_weights

A DataFrame showing the portfolio's weights in individual assets over time.
res.benchmark

If a benchmark was specified, this will contain benchmark performance data.
res.prices.index

The index (dates) corresponding to the price and portfolio values.
	            
    
    '''
    if weights == None:
        weights=[np.round(1 / len(syms),3)] * len(syms)
        
    rebal_mapping = {
        'once': bt.algos.RunOnce(),
        'quarterly': bt.algos.RunQuarterly(),
        'yearly': bt.algos.RunYearly(),
    }

    if rebal not in rebal_mapping:
        raise ValueError("Invalid value for rebal parameter. Use 'once', 'quarterly', or 'yearly'.")

    rebal_per = rebal_mapping[rebal]   
    
    px=fmp_priceLoop(syms, start=start, fac=fac).dropna()
    
    print ('First available data is '+str(px.index[0].date()))
    print('weights: '+str(dict(zip(syms, weights))))
    print('type:  '+fac)
    idx = bt.Strategy(name, [rebal_per,
                       bt.algos.SelectAll(),
                       bt.algos.WeighSpecified(**dict(zip(syms, weights))),
                       bt.algos.Rebalance()])
    print('Creating Index')
    t = bt.Backtest(idx, px)
    res = bt.run(t)
    print(res.prices.tail(1))
   
    return res
    
#--------------------------------------------------------------------------------------------
def fmp_13F(cik='0001067983', leng=40, date='2022-12-31'):
    
 
    
    '''
   
Inputs: cik# as a string
	    leng as a string = number of symbols to return
        date as string yyyy-mm-dd is one of 4 quarted end dates:  3/31, 6/30, 9/30, or 12/31.  will ususlly not be 
        availabe until AFTER 45 days from quarter end
Output: top 40 holdings df of date of report, symbol, position size in shares 
        and dollars, % of position, and calculated price
		and sorted by position percentage
        
    '''
    
    
    insurl='https://financialmodelingprep.com/api/v3/form-thirteen/'+cik+'?date='+date+'&apikey='+apikey
    response = urlopen(insurl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    stuff
    df=pd.DataFrame(stuff, index=[i['tickercusip'] for i in stuff])
    df['bps'] = np.round(df.value/df.value.sum(axis=0)*10000,0)
    df['bps']=df['bps'].astype(int)
    df['px'] = np.round(df.value/df.shares,2)
    df.sort_values(by='bps', ascending=False, inplace=True)
    return df[['date',	'acceptedDate', 'cusip', 
        'nameOfIssuer',	'titleOfClass','shares', 'px', 'value',	 'bps']].head(leng)
		
#--------------------------------------------------------------------------------------------
def fmp_13Fcik(cik):
    '''
Input:  cik number as a string
Output: Entity name as a string
    
    '''

    url = 'https://financialmodelingprep.com/api/v3/cik/'+cik+'?apikey='+apikey

    # Send request to Financial Modeling Prep API
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    stuff=stuff[0]
    return stuff['name']
#--------------------------------------------------------------------------------------
def fmp_13Fentity(entity='berkshire'):
    
    '''
   
Inputs: entity name as string
	    
Output: dataframe of enbtity name matches and cik # 
    
    '''
       
    insurl='https://financialmodelingprep.com/api/v3/cik-search/'+entity+'?apikey='+apikey
    response = urlopen(insurl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    df=pd.DataFrame(stuff)
    return df.loc[:, ['name','cik']].sort_values(by='name')
    


#--------------------------------------------------------------------------------------
def fmp_const(sym, tickersOnly=False):
    '''
    Input:  sym:str --input an etf or mutual fund
    tickersOnly: bool, returns a list of tickers.  default is False
    Output: returns a df of the following columns:
            'name', 'pct', 'price', 'country', 'updated'
    '''
    sym=sym.upper()
    insurl= f'https://financialmodelingprep.com/api/v3/etf-holder/{sym}?apikey={apikey}'
    response = urlopen(insurl)
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    df=pd.DataFrame(stuff)
    
    ##extracts 2 letter country code from the front of isin #
    df['country'] = df['isin'].apply(lambda x: re.split('[^a-zA-Z]', x)[0])
    if tickersOnly:
         return df.asset.tolist()
    df = df.loc[:,['asset', 'name', 'weightPercentage', 'country','updated']].set_index('asset', drop=True)
    df.columns=['name', 'pct', 'country', 'updated']
    return df		
	
#-----------------------------------------------------------------------------------------------

def fmp_shares(sym='aapl'):
    '''
    input:symbol
    output: list : float, oustanding, percent float
    '''
    sym=sym.upper()
    floaturl=r'https://financialmodelingprep.com/api/v4/shares_float?symbol='+sym+'&apikey='+apikey
    response = urlopen(floaturl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    
    return [stuff[0]['floatShares'],stuff[0]['outstandingShares'], np.round(stuff[0]['floatShares']/stuff[0]['outstandingShares'],3)] 
	
#-------------------------------------------------------------------------------------------------



def fmp_close(sym,lbk=1000):  
    ####when mkt trading lbk=2 is prev day####
    
    '''returns a 2xn list of dicts {date: date,  close:close} with default length of 1000
	    leng = last n closing prices
	    '''
    #sym=sym.upper()
    closeurl='https://financialmodelingprep.com/api/v3/historical-price-full/'+sym+'?serietype=line&timeseries='+str(lbk)+'&apikey='+apikey
    response = urlopen(closeurl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    l=stuff['historical'] 
    l.reverse()
    return l
#-------------------------------------------------------------------------------------------------
	
# def fmpw_returns(syms, lbk=63):
    # '''returns simple return and anual hv of a symbol(s) for a given lookback in days  0
       # syms: list of a single symbol or multiple symbols
       # lkbk: positive int for market days to lookback.  1 yr = 252, 1 mo = 21.
             # most recent quote is a realtime quote during mkt hours so oneday is lkbk=1
             # after market hours for a 1 day return lkbk=1'''
    
    # b=[]  #list of lookback prices for return calc
    # d=[]  #list of hv per symbol
    # e=[]  # modified list of working symbols for next section
    # print('Running Lbk and HV Loop')
    # for i in notebook.tqdm(syms):
        # try:
            # b.append(fmp_close(i, lbk)[-lbk]['close'])
            # d.append(fmpw_hv(i, lbk))
            # e.append(i)
        # except KeyError:
            # print('Symbol '+i+' is not available')
            # continue
        # except IndexError:
            # print('Not enough history available for symbol '+i )
            # continue
    # d=pd.DataFrame(d, index=e, columns=['hv'])    
    # c=[] #list of current prices for return calculation
    # print('Running Most Recent Close Loop')
    # for i in notebook.tqdm(e):
        # c.append(fmp_rt(i))    
    # df=pd.DataFrame(list(zip(c,b)), index=e)
    # df[str(lbk)+'Ret']=np.round(((df.iloc[:,0]/df.iloc[:,1])-1)*100,2)
    # df=df[str(lbk)+'Ret']
    # df=pd.concat([df, d], axis=1)
    # df['sharp'] = np.round(df.iloc[:,0]/df.iloc[:,1],2)
    # return df

#----------------------------------------------------------------------------------------




#---------------------------------------------------------------------------------------

    
#------------------------------------------------------------------------------------
    
def fmp_corr(sym1, sym2, lbk=60):
    '''input sy1, sy2 and lbk 
    outputs corr coefficient'''
    X=[sub['close'] for sub in fmp_close(sym1, lbk)]
    Xr=np.diff(np.log(X))
    Y=[sub['close'] for sub in fmp_close(sym2, lbk)]
    Yr=np.diff(np.log(Y))
    return np.round(np.corrcoef(Xr,Yr)[0,1],3)
    
    

#---------------------------------------------------


    
#-----------------------------------------------------------------------------

def fmp_cormatrix(syms, start=60):
    
    df=fmp_priceLoop(syms,start = utils.ddelt(start+2))
    log_returns_df = np.log(df).diff().dropna()

    if len(syms)>2:
        
        # Compute the correlation matrix using pandas
        corr_matrix = pd.DataFrame(log_returns_df.corr())
        styled_df = corr_matrix.style.background_gradient(cmap='Greys').format('{:.2f}')
        return styled_df
    else:
        return log_returns_df.corr().iloc[0,1]
          
    
    
#------------------------------------------------------------------------------    


    
#---------------------------------------------------------------------------------
    


def fmp_filings(sym, limit=20):
    url = f"https://financialmodelingprep.com/api/v3/sec_filings/{sym}?page=0&limit={limit}&apikey={apikey}"
    df = pd.read_json(url)
    try:
       df = df[['acceptedDate', 'cik', 'type', 'link']]
    except KeyError:
        print("No Filings Available")
        return None
    
    def make_clickable(val):
        return f'<a target="_blank" href="{val}">{val}</a>'
    
    return df.style.format({'link': make_clickable})
  
    
#-----------------------------------------------------------------------------------------

def fmp_prof(syms, facs=['companyName','sector', 'industry', 'mktCap'] ):
    '''   
    returns dataframe for a symbol or list of symbols
    facs = facs = 'symbol', 'price', 'beta', 'volAvg', 'mktCap', 'lastDiv', 'range', 
       'changes', 'companyName', 'currency', 'cik', 'isin', 'cusip', 'exchange', 
       'exchangeShortName', 'industry', 'website', 'description', 'ceo', 'sector', 
       'country', 'fullTimeEmployees', 'phone', 'address', 'city', 'state', 'zip', 
       'dcfDiff', 'dcf', 'image', 'ipoDate', 'defaultImage', 'isEtf', 
       'isActivelyTrading' 
        '''
    
    if isinstance(syms,str):
        syms=syms
    else:    
        syms=tuple(syms)
        syms=','.join(syms)
    profurl=requote_uri('https://financialmodelingprep.com/api/v3/profile/'+syms+'?apikey='+apikey)
    response = urlopen(profurl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    idx = [sub['symbol'] for sub in stuff]

    #facs=['companyName', 'beta', 'volAvg', 'mktCap', 'cik']
    df = pd.DataFrame([[sub[k] for k in facs ] for sub in stuff], 
                  columns= facs, index=idx)
    if 'volAvg' in facs:
        df.volAvg = np.round(df.volAvg/1000000,0)
    if 'mktCap' in facs:
        df.mktCap = np.round(df.mktCap/1000000,0)
   
    return df

#-------------------------------------------------------

def fmp_profF(sym, facs=None ):
    '''  
       Returns the full profile of a single symbol
       facs = 'symbol', 'price', 'beta', 'volAvg', 'mktCap', 'lastDiv', 'range', 
       'changes', 'companyName', 'currency', 'cik', 'isin', 'cusip', 'exchange', 
       'exchangeShortName', 'industry', 'website', 'description', 'ceo', 'sector', 
       'country', 'fullTimeEmployees', 'phone', 'address', 'city', 'state', 'zip', 
       'dcfDiff', 'dcf', 'image', 'ipoDate', 'defaultImage', 'isEtf', 
       'isActivelyTrading'   '''
    if facs==None:
        full=['symbol', 'companyName', 'price', 'beta', 'volAvg', 'mktCap', 'lastDiv',  
			'changes', 'companyName', 'currency', 'cik', 'isin', 'cusip',  
			'exchangeShortName', 'industry',  'sector', 'country', 
			'ipoDate', 'isEtf', 'isActivelyTrading' , 'description'  ]	
        facs=full
    profurl=requote_uri('https://financialmodelingprep.com/api/v3/profile/'+sym+'?apikey='+apikey)
    response = urlopen(profurl, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)
    try:
        stuff= stuff[0]
    except IndexError:
        d=dict.fromkeys(facs)
        d.update(symbol=sym)
        return d
    return dict((k, stuff[k]) for k in facs)
#---------------------------------------------------------------------------------------------------

######Check monthly with return flag=True
def fmp_2SymReg(sym_a, sym_b, start='1960-01-01', end=str(dt.datetime.now().date()), ret=True):
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    
    # Retrieve data once
    data = fmp_priceLoop([sym_a, sym_b], start=start, end=end, fac='close').dropna()

    # Daily regression
    if ret:
        log_returns = np.log(data / data.shift()).dropna()
        X_daily = log_returns.iloc[:, 0].to_numpy().reshape(-1, 1)
        Y_daily = log_returns.iloc[:, 1].to_numpy().reshape(-1, 1)
    else:
        X_daily = data.iloc[:, 0].to_numpy().reshape(-1, 1)
        Y_daily = data.iloc[:, 1].to_numpy().reshape(-1, 1)
    
    lin_regr = LinearRegression()
    lin_regr.fit(X_daily, Y_daily)
    Y_pred_daily = lin_regr.predict(X_daily)

    alpha_daily = lin_regr.intercept_[0]
    beta_daily = lin_regr.coef_[0, 0]
    r_squared_daily = np.round(r2_score(Y_daily, Y_pred_daily), 3)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title("Daily:  Alpha: " + str(round(alpha_daily, 5)) + ", Beta: " + str(round(beta_daily, 3)) + "  R²: " + str(r_squared_daily))
    ax.scatter(X_daily, Y_daily)
    ax.plot(X_daily, Y_pred_daily, c='r')
    ax.set_xlabel(sym_a)
    ax.set_ylabel(sym_b)

    # Monthly regression
    data_monthly = data.resample('M').last().dropna()
    if ret:
        log_returns_monthly = np.log(data_monthly / data_monthly.shift()).dropna()
        X_monthly = log_returns_monthly.iloc[:, 0].to_numpy().reshape(-1, 1)
        Y_monthly = log_returns_monthly.iloc[:, 1].to_numpy().reshape(-1, 1)
    else:
        X_monthly = data_monthly.iloc[:, 0].to_numpy().reshape(-1, 1)
        Y_monthly = data_monthly.iloc[:, 1].to_numpy().reshape(-1, 1)

    lin_regr.fit(X_monthly, Y_monthly)
    Y_pred_monthly = lin_regr.predict(X_monthly)

    alpha_monthly = lin_regr.intercept_[0]
    beta_monthly = lin_regr.coef_[0, 0]
    r_squared_monthly = np.round(r2_score(Y_monthly, Y_pred_monthly), 3)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title("Monthly:  Alpha: " + str(round(alpha_monthly, 5)) + ", Beta: " + str(round(beta_monthly, 3)) + "  R²: " + str(r_squared_monthly))
    ax.scatter(X_monthly, Y_monthly)
    ax.plot(X_monthly, Y_pred_monthly, c='r')
    ax.set_xlabel(sym_a)
    ax.set_ylabel(sym_b)
#-----------------------------------------------------------------------------------------------------

def fmp_stoch(sym,length=8, smooth=3):
    df=fmp_price(sym, facs=['low', 'high', 'close'], start=tdelt(length+3))
    df['highest'] = df.high.rolling(length).max()
    df['lowest'] = df.low.rolling(length).min()
    df['k'] = 100*(df.close-df.lowest) / (df.highest-df.lowest)
    df['k_smooth'] = df.k.rolling(smooth).mean()
    return np.round(df.k_smooth[-1],2)

#------------------------------------------------------------------------------------------------------
def fmp_rsi(sym, periods = 3, watch=True, start='1990-01-01'):
    """
    Returns a pd.Series with the relative strength index.
    """
    if watch:
        df=fmp_price(sym, facs=['close'], start=utils.ddelt(periods+5))
    
        close_delta = df.diff()

        # Make two series: one for lower closes and one for higher closes
        up = close_delta.clip(lower=0)
        down = -1 * close_delta.clip(upper=0)
    

        # Use exponential moving average
        ma_up = up.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
        ma_down = down.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
 
        
        rsi = ma_up / ma_down
        rsi = 100 - (100/(1 + rsi))
       

        return np.round(rsi.close[-1],2)
    
    else:
        df=fmp_price(sym, facs=['close'], start=start)
    
        close_delta = df.diff()

        # Make two series: one for lower closes and one for higher closes
        up = close_delta.clip(lower=0)
        down = -1 * close_delta.clip(upper=0)
    

        # Use exponential moving average
        ma_up = up.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
        ma_down = down.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
 
        
        rsi = ma_up / ma_down
        rsi = 100 - (100/(1 + rsi))
       

        return np.round(rsi.close,2)
    
#-----------------------------------------------------------------------------------

def fmp_peers(sym):
    '''
    Input: Symbol or list of symbols
    Returns:  sym plus a list of peer symbols
    '''
    sym=sym.upper()
    insurl=f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={sym}&apikey={apikey}"
    response = urlopen(insurl)
    data = response.read().decode("utf-8")
    stuff=json.loads(data)

    lst = stuff[0]['peersList']
    lst.insert(0,sym)
    df=pd.DataFrame([fmp_profF(i, facs=['companyName', 'mktCap', 'sector', 'industry', 
                                        'country', 'exchangeShortName']) for i in lst], index=lst)
    df['mktCap']=(df.mktCap/1000000).round(2)
    df.rename(columns={'mktCap': 'mktCap(M)'}, inplace=True)
    df.sort_values(by='mktCap(M)', ascending=False, inplace=True)
    return df

#---------------------------------------------------------------------------

def fmp_plotFin(data, title=None):
    ''' parameters are data and title'''
    
    if title==None:
        title = data.columns[0]
    else:
        title = str(title)
    ddata=data.iloc[:,0]    
    plt.rcParams.update({
        "lines.color": "white",
        "patch.edgecolor": "lightgray",
        "text.color": "orange",
        "axes.facecolor": "black",
        "axes.edgecolor": "lightgray",
        "axes.labelcolor": "orange",
        "xtick.color": "lightgray",
        "xtick.labelsize":16,
        "ytick.color": "lightgray",
        "ytick.labelsize":16,
        "grid.color": "lightgray",
        "figure.facecolor": "black",
        "figure.edgecolor": "lightgray",
        "savefig.facecolor": "black",
        "savefig.edgecolor": "black"})
    fig,ax= plt.subplots(figsize=(14, 8))    
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    plt.plot(data, color='limegreen')
    plt.title(title, loc='left',fontdict={'family': 'serif', 
                    'color' : 'orange',
                    'weight': 'bold',
                    'size': 20})
    ax.grid(linestyle=':')
    ax.tick_params(axis='x', labelrotation=45)
    plt.show()
    
#------------------------------------------------------------------------
def fmp_plotFinMult(data, title='Multi-Symbol Chart'):
    ''' parameters are data and title'''
    
    
    title = str(title)
    plt.rcParams.update({
        "lines.color": "white",
        "patch.edgecolor": "lightgray",
        "text.color": "orange",
        "axes.facecolor": "black",
        "axes.edgecolor": "lightgray",
        "axes.labelcolor": "orange",
        "xtick.color": "lightgray",
        "xtick.labelsize":16,
        "ytick.color": "lightgray",
        "ytick.labelsize":16,
        "grid.color": "lightgray",
        "figure.facecolor": "black",
        "figure.edgecolor": "lightgray",
        "savefig.facecolor": "black",
        "savefig.edgecolor": "black"})
    fig,ax= plt.subplots(figsize=(14, 8))    
    ax.yaxis.tick_right()
    plt.plot(data)
    plt.legend(data.columns, loc='lower right')
    plt.title(title, loc='left',fontdict={'family': 'serif', 
                    'color' : 'orange',
                    'weight': 'bold',
                    'size': 20})
    ax.grid(linestyle=':')
    plt.show()	
    
##------------------------------------------------

def fmp_plotBarRetts(data): 
    """
    Plots a bar chart of returns over time, converting dates to categorical labels
    to avoid gaps for non-trading days.
    
    Parameters:
    -----------
    data : pandas.DataFrame
        A DataFrame with a datetime index and a single column of return values.
    
    Returns:
    --------
    None
        Displays the plotted bar chart.
    """
    # Drop NaN values
    data = data.dropna()

    # Extract values
    values = data.iloc[:, 0].to_numpy().flatten()
    colors = np.where(values >= 0, 'g', 'r')  # Assign green for positive, red for negative

    # Convert dates to string labels (so they are treated as categorical)
    date_labels = data.index.strftime('%m/%d/%Y')  # Format: MM/DD

    # Create the figure
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.grid()

    # Use range as x-values to plot without gaps
    ax.bar(range(len(data)), values, color=colors)

    # Replace x-ticks with date labels
    ax.set_xticks(range(len(data)))
    ax.set_xticklabels(date_labels, rotation=45)

    plt.show()

#----------------------------------------------------------------
import matplotlib.pyplot as plt
import pandas as pd


def fmp_plotDualAxis(df, left_cols=None, right_cols=None, left_label=None, right_label=None):
    """
Plots the given DataFrame using dual y-axes.

:param df: The DataFrame to plot. 
:param left_cols: A column name or a list of column names as strings to plot on the left y-axis.
:param right_cols: A column or a list of column names ast strings to plot on the right y-axis.
:param left_label: The label for the left y-axis as a string.
:param right_label: The label for the right y-axis as a string.
    """

    if left_cols is None and right_cols is None:
        raise ValueError("At least one of left_cols or right_cols must be specified")

    fig, ax1 = plt.subplots(figsize=(12,7))
    ax2 = ax1.twinx()

    if left_cols:
        if isinstance(left_cols, str):
            left_cols = [left_cols]
        for i, col in enumerate(left_cols):
            color = None if i > 0 else 'C0'
           
            if col in df.columns:
                if i == 0:
                    ax1.plot(df.index, df[col], label=left_label or col, color=color, linewidth=3.0)
                else:
                    ax1.plot(df.index, df[col], label=left_label or col, color=color)
        ax1.set_ylabel(left_label or ', '.join(left_cols), color='black')
        ax1.spines['left'].set_color('black')

    if right_cols:
        if isinstance(right_cols, str):
            right_cols = [right_cols]
        for i, col in enumerate(right_cols):
            color = plt.cm.tab10(i+len(left_cols)) if left_cols else plt.cm.tab10(i)
            if col in df.columns:
                ax2.plot(df.index, df[col], label=right_label or col, color=color)
        ax2.set_ylabel(right_label or ', '.join(right_cols), color='black')
        ax2.spines['right'].set_color('black')
        ax2.tick_params(axis='y', labelcolor='black')

    # set legend for left axis
    if left_cols:
        lines, labels = ax1.get_legend_handles_labels()
        ax1.legend(lines, labels, loc="upper left")

    # set legend for right axis
    if right_cols:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines2, labels2, loc="upper right")

    # remove xlabel if no data for left axis
    if not left_cols:
        ax1.set_xlabel('')

    # remove ylabel if no data for left axis
    if not right_cols:
        ax2.set_ylabel('')

    # add gridlines if data is present
    if left_cols and right_cols:
        ax1.grid(True, linestyle='--', linewidth=0.5, color='grey', alpha=0.5)
    elif right_cols:
        ax2.grid(True, linestyle='--', linewidth=0.5, color='grey', alpha=0.5)

#---------------------------------------------------------------

def fmp_plotStackedRet(retSyms, lineSym, start=utils.ddelt(63)):
    '''
This function plots 3 stacked Return plots over a Line plot.

Inputs:
    retSyms is a list of exactly 3 symbols.  default is 'SPY', 'QQQ', 'IWM'
    lineSym is a string of a single symbol. defaul is '^TNX' (10Y Treas)
    start is a string 'YYYY-mm-dd'. default is 3 Months
Returns:
    4 vertically stacked plots with the first three being vertical bar plots of price returns
    and the last being a line plot of price
    
    
    
    '''
    
    lineSym=[lineSym]
    syms=retSyms+lineSym

    import pandas as pd
    import matplotlib.pyplot as plt


    df=fmp_priceMult(syms,start=start)

    df.iloc[:, :3] = df.iloc[:, :3].pct_change()
    df=df.dropna()



    # create a figure with subplots
    fig, axs = plt.subplots(4, 1, figsize=(8.5, 11), sharex=True)

    # create the bar plots for the top 3 subplots
    for i, col in enumerate(df.columns[:3]):
        axs[i].bar(range(len(df)), df[col], color=['green' if val>0 else 'red' for val in df[col]])
        axs[i].set_ylabel(col)
        axs[i].grid(True)
        if i == 0:
            axs[i].set_title('Returns Over '+df.columns[3])  # Add title to the first plot

    # create the line plot for the bottom subplot
    axs[3].plot(range(len(df)), df.iloc[:, 3], 'k-', linewidth=2)
    axs[3].set_ylabel(df.columns[3])
    axs[3].grid(True)

    # set the tick positions and labels
    first_date = df.index[0]
    last_date = df.index[-1]
    tick_positions = np.linspace(df.index.get_loc(first_date), df.index.get_loc(last_date), num=10, dtype=int)
    tick_labels = df.index[tick_positions].strftime('%Y-%m-%d')

    # set the tick positions and labels for the x-axis
    plt.xticks(tick_positions, tick_labels, rotation=45)

    # adjust subplot spacing
    plt.subplots_adjust(hspace=0.1)

    # save the figure as a PDF file
    #plt.savefig('my_plot.pdf', bbox_inches='tight')


#---------------------------------------------------------------
def get_sectors():
    """Retrieve the list of sectors using FMP API."""
    url = f"https://financialmodelingprep.com/api/v3/sectors-list?apikey={apikey}"
    response = requests.get(url)
    return response.json()

def get_industries_by_sector(sector):
    """Retrieve the list of industries for a given sector using FMP API."""
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?sector={sector}&apikey={apikey}"
    response = requests.get(url)
    data = response.json()
    
    # Extract unique industries from the response
    industries = {item['industry'] for item in data if 'industry' in item}
    return sorted(industries)  # Alphabetize industries

def build_sector_industry_map():
    """Build a complete dictionary mapping sectors to industries."""
    sectors = get_sectors()
    sector_industry_map = defaultdict(list)

    # Loop through each sector and fetch its industries
    for sector in sectors:
        industries = get_industries_by_sector(sector)
        sector_industry_map[sector] = industries

    return sector_industry_map

def fmp_sectInd():
    """Display the sector-industry mapping in Markdown format with alphabetical order."""
    sector_industry_map = build_sector_industry_map()

    # Print each sector and its industries using Markdown formatting
    for sector, industries in sector_industry_map.items():
        display(Markdown(f"**{sector}:**"))
        for industry in industries:
            display(Markdown(f"- {industry}"))


#----------------------------------------------------------------------------------------
def fmp_plotMult(sym = 'COIN', start=utils.ddelt(504)):
    df=fmp_price(sym, start=start)
    df['rsi'] = fmp_rsi(sym,periods=3, watch=False)

    df['max'] = df.close.rolling(42).max()
    df['min'] = df.close.rolling(42).min()
    df['mid'] = (df['max'] + df['min'])/2


    df['indx']=(df['close'] - df['min']) / (df['max'] - df['min'])

    df['width'] = (df['max'] - df['min']) / df['close']

    max_val = df['close'].expanding().max()

    # create a new column 'max_col' with the maximum value repeated for each row
    df['max_col'] = max_val

    df['dd'] = (df['close']-df['max_col']) / df['max_col']

    fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, sharex=True , gridspec_kw={'height_ratios': [4, 1, 1, 2,1]}, figsize=(12,13))

    # plot the 'close' column on the first subplot
    df[['close', 'max', 'min', 'mid']].plot(ax=ax1, grid=True, color = ['blue', 'gray', 'gray', 'orange'])
    ax1.legend().set_visible(False)
    ax1.set_title(sym)

    ax1.yaxis.tick_right()
    ax1.yaxis.set_label_position('right')

    # plot the 'volume' column on the second subplot
    df['indx'].plot(ax=ax2, grid=True)
    ax2.legend()
    ax2.axhline(y=.5, color='red', linestyle='--')

    ax2.yaxis.tick_right()
    ax2.yaxis.set_label_position('right')

    # plot the 'volume' column on the second subplot
    df['width'].plot(ax=ax3, grid=True)
    ax3.legend()

    ax3.yaxis.tick_right()
    ax3.yaxis.set_label_position('right')

    # plot the 'volume' column on the second subplot
    df['rsi'].plot(ax=ax4, grid=True)
    ax4.legend()

    ax4.yaxis.tick_right()
    ax4.yaxis.set_label_position('right')

    ax4.axhline(y=85, color='red', linestyle='--')
    ax4.axhline(y=15, color='red', linestyle='--')


    # plot the 'volume' column on the second subplot
    df['dd'].plot(ax=ax5, grid=True)
    ax5.fill_between(df.index, 0,df['dd'], color='blue', alpha=0.2)
    ax5.legend()

    ax5.yaxis.tick_right()
    ax5.yaxis.set_label_position('right')

#------------------------------------------------------------------------------

def fmp_plotPiv(sym='SPY', start=utils.ddelt(252*2)):
    df=fmp_price(sym, start=start)

    window=30
    volLength=21
    # Calculate log returns 
    log_returns = np.log(df / df.shift())

    # Calculate rolling window standard deviation
    rolling_std = log_returns.rolling(window).std()

    # Multiply by square root of volLength
    result = rolling_std * np.sqrt(volLength)

    result = result.fillna(method='bfill')
    result = result.rename(columns={'close': 'hv'})

    PEAK, VALLEY = 1, -1

    def _identify_initial_pivot(X, init_thresh):
        """Quickly identify the X[0] as a peak or valley."""
        x_0 = X[0]
        max_x = x_0
        max_t = 0
        min_x = x_0
        min_t = 0
        up_thresh = 1
        down_thresh = 1

        for t in range(1, len(X)):
            x_t = X[t]

            if x_t / min_x >= init_thresh:
                return VALLEY if min_t == 0 else PEAK

            if x_t / max_x <= -init_thresh:
                return PEAK if max_t == 0 else VALLEY

            if x_t > max_x:
                max_x = x_t
                max_t = t

            if x_t < min_x:
                min_x = x_t
                min_t = t

        t_n = len(X)-1
        return VALLEY if x_0 < X[t_n] else PEAK



    initial_pivot=_identify_initial_pivot(df.close, init_thresh=result.hv[0])



    ##--------------------------------------------------------------------------------------------
    close = df.close


    """
    Finds the peaks and valleys of a series of HLC (open is not necessary).
    TR: This is modified peak_valley_pivots function in order to find peaks and valleys for OHLC.
    Parameters
    ----------
    close : This is series with closes prices.
    up_thresh : The minimum relative change necessary to define a peak.
    down_thesh : The minimum relative change necessary to define a valley.
    Returns
    -------
    an array with 0 indicating no pivot and -1 and 1 indicating valley and peak
    respectively
    Using Pandas
    ------------
    For the most part, close may be a pandas series. However, the index must
    either be [0,n) or a DateTimeIndex. Why? This function does X[t] to access
    each element where t is in [0,n).
    The First and Last Elements
    ---------------------------
    The first and last elements are guaranteed to be annotated as peak or
    valley even if the segments formed do not have the necessary relative
    changes. This is a tradeoff between technical correctness and the
    propensity to make mistakes in data analysis. The possible mistake is
    ignoring data outside the fully realized segments, which may bias analysis.
    """

    up_thresh = result.hv
    down_thresh = -result.hv

    if down_thresh[0] > 0:
        raise ValueError('The down_thresh must be negative.')


    t_n = len(close)
    pivots = np.zeros(t_n, dtype='i1')
    pivots[0] = initial_pivot

    # Adding one to the relative change thresholds saves operations. Instead
    # of computing relative change at each point as x_j / x_i - 1, it is
    # computed as x_j / x_1. Then, this value is compared to the threshold + 1.
    # This saves (t_n - 1) subtractions.
    up_thresh += 1
    down_thresh += 1

    trend = -initial_pivot

    last_pivot_t = 0
    last_pivot_x = close[0]
    for t in range(1, len(close)):

        if trend == -1:
            x = close[t]

            r = x / last_pivot_x


            if r >= up_thresh[t]:
                pivots[last_pivot_t] = trend#
                trend = 1
                #last_pivot_x = x
                last_pivot_x = close[t]
                last_pivot_t = t
            elif x < last_pivot_x:
                last_pivot_x = x
                last_pivot_t = t
        else:
            x = close[t]

            r = x / last_pivot_x

            if r <= down_thresh[t]:
                pivots[last_pivot_t] = trend
                trend = -1
                #last_pivot_x = x
                last_pivot_x = close[t]
                last_pivot_t = t
            elif x > last_pivot_x:
                last_pivot_x = x
                last_pivot_t = t


    if last_pivot_t == t_n-1:
        pivots[last_pivot_t] = trend
    elif pivots[t_n-1] == 0:
        pivots[t_n-1] = trend
    ar= pd.DataFrame(pivots, index=df.index, columns=['pivot'])    
    df=pd.concat([df,ar, result], axis=1)

    df['count'] = range(1, len(df)+1)

    dfp=df[df['pivot']!=0]


    dfp['dur'] = dfp['count'].diff().fillna(0).astype(int)

    dfp['chg']=np.round(dfp.close.pct_change(),3)

    dfp['ave'] = np.round(dfp.chg / dfp.dur,4)


    conditions = [
        (dfp['pivot'] == 1) & (dfp['close'] > dfp['close'].shift(2)),
        (dfp['pivot'] == 1) & (dfp['close'] < dfp['close'].shift(2)),
        (dfp['pivot'] == -1) & (dfp['close'] > dfp['close'].shift(2)),
        (dfp['pivot'] == -1) & (dfp['close'] < dfp['close'].shift(2))
    ]

    choices = ['HH', 'LH', 'HL', 'LL']

    dfp['pivot2'] = np.select(conditions, choices, default=np.nan)

    # create two subsets of the data based on the pivot column
    subset_up = dfp[dfp['pivot'] > 0][['pivot2', 'dur', 'chg']]
    subset_dn = dfp[dfp['pivot'] < 0][['pivot2', 'dur', 'chg']]

    # get the pivot points for each subset
    pivot_up = dfp[dfp['pivot'] > 0]['close'].tolist()
    pivot_dn = dfp[dfp['pivot'] < 0]['close'].tolist()

    # plot the DataFrame and pivot points
    fig, ax = plt.subplots(figsize=(15,9))

    df['close'].plot(ax=ax)

    ax.plot(df.loc[df['pivot'] != 0, 'close'], '--', color='r')

    # annotate the first subset
    for i in range(len(subset_up)):
        text = f"{  subset_up.iloc[i]['pivot2']}\n{subset_up.iloc[i]['dur']}\n{subset_up.iloc[i]['chg']}"
        ax.annotate(text, xy=(subset_up.index[i], pivot_up[i]), xytext=(-20, 15), textcoords='offset pixels')

    # annotate the second subset    
    for i in range(len(subset_dn)):
        text = f"{  subset_dn.iloc[i]['pivot2']}\n{subset_dn.iloc[i]['dur']}\n{subset_dn.iloc[i]['chg']}"
        ax.annotate(text, xy=(subset_dn.index[i], pivot_dn[i]), xytext=(-20, -45), textcoords='offset pixels')

    # set axis labels and title
    ax.set_xlabel('Date')
    ax.set_ylabel('Close Price')
    ax.set_title(sym)
    ax.grid()
    plt.show()

#------------------------------------------------------------------------------------------
def fmp_newsdict(sym=None, limit='50'):
    '''
    syms= symbols in the form of: 'KSHB,GNLN,PBL,NBN,SKT' .  Max 5 symbol limit by FMP
    convert list of strings by: ','.join(['KSHB', 'GNLN', 'PBL'])
    returns a dict
    '''
    
    if sym:
        sym=sym.upper()
        symnewsurl = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={sym}&limit={limit}&apikey={apikey}"
        response = urlopen(symnewsurl, cafile=certifi.where())
        data = response.read().decode("utf-8")
        stuff=json.loads(data)
        
        
            
    else:
        allnewsurl = f"https://financialmodelingprep.com/api/v3/stock_news?limit={limit}&apikey={apikey}"
        response = urlopen(allnewsurl, cafile=certifi.where())
        data = response.read().decode("utf-8")
        stuff=json.loads(data)
        
    return stuff    
        
#--------------------------------
	
def fmp_news(sym=None, limit='50'):
    '''
    Retrieve and display stock news from Financial Modeling Prep API.

    Parameters:
    -----------
    sym : str, optional
        Stock ticker symbol(s) to query. Can be a single symbol (e.g., 'AAPL') 
        or multiple symbols as a comma-separated string (e.g., 'AAPL,MSFT,GOOGL').
        If None, returns general stock news not specific to any symbol.
        Default is None.
    limit : str, optional
        Maximum number of news articles to retrieve, as a string.
        Default is '50'.

    Returns:
    --------
    None
        Displays formatted HTML output in Jupyter notebook showing:
        - Stock symbol and publication date (bold)
        - News source site (italicized)
        - News text content
        - Clickable URL to original article

    Examples:
    ---------
    >>> fmp_news('AAPL')  # Get news for Apple
    >>> fmp_news('AAPL,MSFT', limit='25')  # Get 25 news items for Apple and Microsoft
    >>> fmp_news()  # Get general stock market news
    
    Notes:
    ------
    - Requires an API key stored in variable 'apikey'
    - Uses Financial Modeling Prep API (https://financialmodelingprep.com/api/v3/stock_news)
    - Must be run in a Jupyter notebook environment for HTML display
    - Requires internet connection and imported dependencies: urlopen, certifi, json
    - Symbols are automatically converted to uppercase
    
    Raises:
    -------
    Depends on API response - may raise exceptions if:
        - API key is invalid
        - Network connection fails
        - Invalid ticker symbols provided
    '''
    
    if sym:
        sym = sym.upper()
        symnewsurl = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={sym}&limit={limit}&apikey={apikey}"
        response = urlopen(symnewsurl, cafile=certifi.where())
        data = response.read().decode("utf-8")
        stuff = json.loads(data)
        for i in stuff:
            display(HTML(f"<p style='font-size:20px; font-weight:bold;'>{i['symbol']} - {i['publishedDate']}</p>"))
            display(HTML(f"<p style='font-style:italic;'>{i['site']}</p>"))
            display(HTML(f"<p>{i['text']}</p>"))
            display(HTML(f"<a href='{i['url']}' target='_blank'>{i['url']}</a>"))
            display(HTML("<br>"))
            
    else:
        allnewsurl = f"https://financialmodelingprep.com/api/v3/stock_news?limit={limit}&apikey={apikey}"
        response = urlopen(allnewsurl, cafile=certifi.where())
        data = response.read().decode("utf-8")
        stuff = json.loads(data)
        for i in stuff:
            display(HTML(f"<p style='font-size:20px; font-weight:bold;'>{i['symbol']} - {i['publishedDate']}</p>"))
            display(HTML(f"<p style='font-style:italic;'>{i['site']}</p>"))
            display(HTML(f"<p>{i['text']}</p>"))
            display(HTML(f"<a href='{i['url']}' target='_blank'>{i['url']}</a>"))
            display(HTML("<br>"))
#-------------------------------------------------------
def fmp_divHist(sym):
    '''
    input: symbol as string
    returns:  DataFrame of dividend $/share with ex-date as the index
    '''
    url= f"https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/{sym}?apikey={apikey}"
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff=json.loads(data)['historical']
    
    df = pd.DataFrame(stuff)
    df=df.set_index('date')['dividend'].to_frame().sort_index(ascending=True)
    df.index = pd.to_datetime(df.index)
    return df

#-------------------------------------------------------

def fmp_perfStats(s):
    '''
    input: Series or Datframe of prices
    outputs: ab object displaying performance stats
    uses ffn package
    '''
    stats = ffn.calc_stats(s)

# Display performance metrics
    stats.display()
#----------------------------------------------------------

def fmp_ratios(symbol, facs=['currentRatio', 'quickRatio', 'cashRatio',
       'daysOfSalesOutstanding', 'daysOfInventoryOutstanding',
       'operatingCycle', 'daysOfPayablesOutstanding', 'cashConversionCycle',
       'grossProfitMargin', 'operatingProfitMargin', 'pretaxProfitMargin',
       'netProfitMargin', 'effectiveTaxRate', 'returnOnAssets',
       'returnOnEquity', 'returnOnCapitalEmployed', 'netIncomePerEBT',
       'ebtPerEbit', 'ebitPerRevenue', 'debtRatio', 'debtEquityRatio',
       'longTermDebtToCapitalization', 'totalDebtToCapitalization',
       'interestCoverage', 'cashFlowToDebtRatio', 'companyEquityMultiplier',
       'receivablesTurnover', 'payablesTurnover', 'inventoryTurnover',
       'fixedAssetTurnover', 'assetTurnover', 'operatingCashFlowPerShare',
       'freeCashFlowPerShare', 'cashPerShare', 'payoutRatio',
       'operatingCashFlowSalesRatio', 'freeCashFlowOperatingCashFlowRatio',
       'cashFlowCoverageRatios', 'shortTermCoverageRatios',
       'capitalExpenditureCoverageRatio', 'dividendPaidAndCapexCoverageRatio',
       'dividendPayoutRatio', 'priceBookValueRatio', 'priceToBookRatio',
       'priceToSalesRatio', 'priceEarningsRatio', 'priceToFreeCashFlowsRatio',
       'priceToOperatingCashFlowsRatio', 'priceCashFlowRatio',
       'priceEarningsToGrowthRatio', 'priceSalesRatio', 'dividendYield',
       'enterpriseValueMultiple', 'priceFairValue']):
    '''
       factors=['currentRatio', 'quickRatio', 'cashRatio',
       'daysOfSalesOutstanding', 'daysOfInventoryOutstanding',
       'operatingCycle', 'daysOfPayablesOutstanding', 'cashConversionCycle',
       'grossProfitMargin', 'operatingProfitMargin', 'pretaxProfitMargin',
       'netProfitMargin', 'effectiveTaxRate', 'returnOnAssets',
       'returnOnEquity', 'returnOnCapitalEmployed', 'netIncomePerEBT',
       'ebtPerEbit', 'ebitPerRevenue', 'debtRatio', 'debtEquityRatio',
       'longTermDebtToCapitalization', 'totalDebtToCapitalization',
       'interestCoverage', 'cashFlowToDebtRatio', 'companyEquityMultiplier',
       'receivablesTurnover', 'payablesTurnover', 'inventoryTurnover',
       'fixedAssetTurnover', 'assetTurnover', 'operatingCashFlowPerShare',
       'freeCashFlowPerShare', 'cashPerShare', 'payoutRatio',
       'operatingCashFlowSalesRatio', 'freeCashFlowOperatingCashFlowRatio',
       'cashFlowCoverageRatios', 'shortTermCoverageRatios',
       'capitalExpenditureCoverageRatio', 'dividendPaidAndCapexCoverageRatio',
       'dividendPayoutRatio', 'priceBookValueRatio', 'priceToBookRatio',
       'priceToSalesRatio', 'priceEarningsRatio', 'priceToFreeCashFlowsRatio',
       'priceToOperatingCashFlowsRatio', 'priceCashFlowRatio',
       'priceEarningsToGrowthRatio', 'priceSalesRatio', 'dividendYield',
       'enterpriseValueMultiple', 'priceFairValue']
    '''
    
  
    facs=['date']+facs
    url=f'https://financialmodelingprep.com/api/v3/ratios/{symbol}?period=quarter&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff = json.loads(data)
 
    df=pd.DataFrame([{key: value for key, value in item.items() if key in facs} for item in stuff])
    df['date'] = pd.to_datetime(df.date)
    df.set_index('date', inplace=True)
    return df.sort_index()
    
#--------------------------------------------------------------------------

def fmp_ratiosttm(symbol, facs=['dividendYielTTM','dividendYielPercentageTTM','peRatioTTM',
       'pegRatioTTM','payoutRatioTTM','currentRatioTTM','quickRatioTTM',
       'cashRatioTTM','daysOfSalesOutstandingTTM','daysOfInventoryOutstandingTTM',
       'operatingCycleTTM','daysOfPayablesOutstandingTTM','cashConversionCycleTTM',
       'grossProfitMarginTTM','operatingProfitMarginTTM','pretaxProfitMarginTTM',
       'netProfitMarginTTM','effectiveTaxRateTTM','returnOnAssetsTTM',
       'returnOnEquityTTM','returnOnCapitalEmployedTTM','netIncomePerEBTTTM',
       'ebtPerEbitTTM','ebitPerRevenueTTM','debtRatioTTM','debtEquityRatioTTM',
       'longTermDebtToCapitalizationTTM','totalDebtToCapitalizationTTM','interestCoverageTTM',
       'cashFlowToDebtRatioTTM','companyEquityMultiplierTTM','receivablesTurnoverTTM',
       'payablesTurnoverTTM','inventoryTurnoverTTM','fixedAssetTurnoverTTM',
       'assetTurnoverTTM','operatingCashFlowPerShareTTM','freeCashFlowPerShareTTM',
       'cashPerShareTTM','operatingCashFlowSalesRatioTTM','freeCashFlowOperatingCashFlowRatioTTM',
       'cashFlowCoverageRatiosTTM','shortTermCoverageRatiosTTM','capitalExpenditureCoverageRatioTTM',
       'dividendPaidAndCapexCoverageRatioTTM','priceBookValueRatioTTM','priceToBookRatioTTM',
       'priceToSalesRatioTTM','priceEarningsRatioTTM','priceToFreeCashFlowsRatioTTM',
       'priceToOperatingCashFlowsRatioTTM','priceCashFlowRatioTTM','priceEarningsToGrowthRatioTTM',
       'priceSalesRatioTTM','enterpriseValueMultipleTTM','priceFairValueTTM','dividendPerShareTTM']):
    '''
       facs=['dividendYielTTM','dividendYielPercentageTTM','peRatioTTM',
       'pegRatioTTM','payoutRatioTTM','currentRatioTTM','quickRatioTTM',
       'cashRatioTTM','daysOfSalesOutstandingTTM','daysOfInventoryOutstandingTTM',
       'operatingCycleTTM','daysOfPayablesOutstandingTTM','cashConversionCycleTTM',
       'grossProfitMarginTTM','operatingProfitMarginTTM','pretaxProfitMarginTTM',
       'netProfitMarginTTM','effectiveTaxRateTTM','returnOnAssetsTTM',
       'returnOnEquityTTM','returnOnCapitalEmployedTTM','netIncomePerEBTTTM',
       'ebtPerEbitTTM','ebitPerRevenueTTM','debtRatioTTM','debtEquityRatioTTM',
       'longTermDebtToCapitalizationTTM','totalDebtToCapitalizationTTM','interestCoverageTTM',
       'cashFlowToDebtRatioTTM','companyEquityMultiplierTTM','receivablesTurnoverTTM',
       'payablesTurnoverTTM','inventoryTurnoverTTM','fixedAssetTurnoverTTM',
       'assetTurnoverTTM','operatingCashFlowPerShareTTM','freeCashFlowPerShareTTM',
       'cashPerShareTTM','operatingCashFlowSalesRatioTTM','freeCashFlowOperatingCashFlowRatioTTM',
       'cashFlowCoverageRatiosTTM','shortTermCoverageRatiosTTM','capitalExpenditureCoverageRatioTTM',
       'dividendPaidAndCapexCoverageRatioTTM','priceBookValueRatioTTM','priceToBookRatioTTM',
       'priceToSalesRatioTTM','priceEarningsRatioTTM','priceToFreeCashFlowsRatioTTM',
       'priceToOperatingCashFlowsRatioTTM','priceCashFlowRatioTTM','priceEarningsToGrowthRatioTTM',
       'priceSalesRatioTTM','enterpriseValueMultipleTTM','priceFairValueTTM','dividendPerShareTTM']
    '''
    
  
    
    url=f'https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?period=quarter&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff = json.loads(data)
    stuff = stuff[0]
    
    
    return pd.Series({key: value for key, value in stuff.items() if key in facs}).T

#--------------------------------------------------------------
def fmp_keyMetrics(symbol, facs=['revenuePerShare','netIncomePerShare','operatingCashFlowPerShare',
             'freeCashFlowPerShare','cashPerShare','bookValuePerShare',
             'tangibleBookValuePerShare','shareholdersEquityPerShare',
             'interestDebtPerShare','marketCap','enterpriseValue','peRatio',
             'priceToSalesRatio' 'pocfratio','pfcfRatio','pbRatio','ptbRatio',
             'evToSales','enterpriseValueOverEBITDA','evToOperatingCashFlow',
             'evToFreeCashFlow','earningsYield','freeCashFlowYield',
             'debtToEquity','debtToAssets','netDebtToEBITDA','currentRatio',
             'interestCoverage','incomeQuality','dividendYield','payoutRatio',
             'salesGeneralAndAdministrativeToRevenue','researchAndDdevelopementToRevenue',
             'intangiblesToTotalAssets','capexToOperatingCashFlow','capexToRevenue',
             'capexToDepreciation','stockBasedCompensationToRevenue','grahamNumber',
             'roic','returnOnTangibleAssets','grahamNetNet','workingCapital',
             'tangibleAssetValue', 'netCurrentAssetValue','investedCapital',
             'averageReceivables','averagePayables','averageInventory',
             'daysSalesOutstanding','daysPayablesOutstanding','daysOfInventoryOnHand',
             'receivablesTurnover', 'payablesTurnover', 'inventoryTurnover',
             'roe','capexPerShare']):
    '''
       facs=['revenuePerShare','netIncomePerShare','operatingCashFlowPerShare',
             'freeCashFlowPerShare','cashPerShare','bookValuePerShare',
             'tangibleBookValuePerShare','shareholdersEquityPerShare',
             'interestDebtPerShare','marketCap','enterpriseValue','peRatio',
             'priceToSalesRatio' 'pocfratio','pfcfRatio','pbRatio','ptbRatio',
             'evToSales','enterpriseValueOverEBITDA','evToOperatingCashFlow',
             'evToFreeCashFlow','earningsYield','freeCashFlowYield',
             'debtToEquity','debtToAssets','netDebtToEBITDA','currentRatio',
             'interestCoverage','incomeQuality','dividendYield','payoutRatio',
             'salesGeneralAndAdministrativeToRevenue','researchAndDdevelopementToRevenue',
             'intangiblesToTotalAssets','capexToOperatingCashFlow','capexToRevenue',
             'capexToDepreciation','stockBasedCompensationToRevenue','grahamNumber',
             'roic','returnOnTangibleAssets','grahamNetNet','workingCapital',
             'tangibleAssetValue', 'netCurrentAssetValue','investedCapital',
             'averageReceivables','averagePayables','averageInventory',
             'daysSalesOutstanding','daysPayablesOutstanding','daysOfInventoryOnHand',
             'receivablesTurnover', 'payablesTurnover', 'inventoryTurnover',
             'roe','capexPerShare']
    '''
    
  
    facs=['date']+facs
    url=f'https://financialmodelingprep.com/api/v3/key-metrics/{symbol}?period=quarter&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff = json.loads(data)
    df=pd.DataFrame([{key: value for key, value in item.items() if key in facs} for item in stuff])
    df['date'] = pd.to_datetime(df.date)
    df.set_index('date', inplace=True)
    return df.sort_index()
 
#-------------------------------------------------------------------


#-----------------------------------------------------------------------------------------------------

def fmp_earnEst(sym, period='annual'):
    '''
    input:  sym:  as string
            period: as string 'annual' or 'quarter'
    returns: DatFrame wiyh columns  'RevLow','RevHigh','RevAvg','EbitdaLow','EbitdaHigh','EbitdaAvg','EbitLow', 'EbitHigh',
               'EbitAvg','NetIncLow','NetIncHigh','NetIncAvg','SgaExpLow','SgaExpHigh','SgaExpAvg',
            'EpsAvg','EpsHigh','EpsLow','numRev','numEps'        
    '''
    url=f"https://financialmodelingprep.com/api/v3/analyst-estimates/{sym}?&period={period}&apikey={apikey}"
    df=pd.read_json(url)
    df.set_index('date', inplace=True)
    abbreviations = [
    'sym',
    'RevLow',
    'RevHigh',
    'RevAvg',
    'EbitdaLow',
    'EbitdaHigh',
    'EbitdaAvg',
    'EbitLow',
    'EbitHigh',
    'EbitAvg',
    'NetIncLow',
    'NetIncHigh',
    'NetIncAvg',
    'SgaExpLow',
    'SgaExpHigh',
    'SgaExpAvg',
    'EpsAvg',
    'EpsHigh',
    'EpsLow',
    'numRev',
    'numEps'
]
    df.columns=abbreviations
    return df.sort_index()
#--------------------------------------------------------


def fmp_plotyc():
    # Initialize TvDatafeed
    tv = TvDatafeed()
    
    xlst = ['1M','3M','6M','1Y','2Y','3Y','5Y','7Y','10Y','20Y','30Y']
    symlst = ['US01MY', 'US03MY', 'US06MY', 'US01Y', 'US02Y', 'US03Y', 'US05Y', 'US07Y', 'US10Y', 'US20Y', 'US30Y']
    
    # Initialize empty DataFrame
    df = pd.DataFrame()
    
    # Collect historical data
    for i in symlst:
        data = tv.get_hist(i, 'TVC', n_bars=260)
        if data is not None and 'close' in data.columns:
            df[i] = data['close']
    
    # Check if df is empty before proceeding
    if df.empty:
        raise ValueError("DataFrame is empty. Check if 'tv.get_hist' is returning data.")
    
    # Ensure lookback indices are within DataFrame bounds
    lookback = [1, 130, -21, -2]
    df_length = len(df)
    valid_lookback = [idx for idx in lookback if -df_length <= idx < df_length]
    
    # If no valid indices, raise an error
    if not valid_lookback:
        raise IndexError("No valid indices in lookback range.")
    
    # Slice DataFrame with valid lookback indices
    dff = df.iloc[valid_lookback].T
    
    # # Convert column names to dates
    # dff.columns = pd.to_datetime(dff.columns, errors='coerce').strftime('%Y-%m-%d')
    
    # # Drop any columns that could not be converted to dates
    # dff = dff.loc[:, ~dff.columns.str.contains('NaT', na=False)]
    
    # # Debugging: Print lengths and contents
    # print(f"Length of xlst: {len(xlst)}")
    # print(f"Columns in dff: {dff.columns.tolist()}")
    
    # # Ensure length of xlst matches number of dff columns
    # if len(xlst) != len(dff.columns):
    #     raise ValueError("Mismatch between x-axis labels and DataFrame columns.")
    
    # # Plot the data
    # fig, ax = plt.subplots(figsize=(12, 8))
    # for column in dff.columns:
    #     ax.plot(xlst, dff[column], label=column)
    
    # ax.yaxis.set_label_position("right")
    # ax.yaxis.tick_right()
    # plt.grid(True, which='both', linestyle=':', linewidth='0.5', color='lightgrey')
    # plt.legend(title='Symbols')
    # plt.show()
    return dff

#-------------------------------------------------------------------------------------------------------------------------

def fmp_plotShYield(sym, output='plot', quarters=40):
    """
    Compute and visualize the Shareholder Yield (SH Yield) for a given stock symbol.
    
    The function retrieves financial data for the specified symbol, calculates the dividend yield,
    buyback yield, and total shareholder yield, and either plots the data or returns it as a DataFrame.
    
    Parameters:
    sym (str): Stock ticker symbol.
    output (str, optional): Determines the function output. Default is 'plot'.
        - 'plot': Displays a plot of the shareholder yield components.
        - 'df': Returns a DataFrame containing the yield calculations.
        - 'quarters': is the number of quarters to plot.  Default is 10 years or 40 quarters
    
    Returns:
    None or pd.DataFrame: 
        - Returns None if output='plot' (displays a plot).
        - Returns a DataFrame if output='df'.
    """
    # Fetch financial data
    cf = fmp_cashfts(sym, facs=['commonStockIssued', 'commonStockRepurchased', 'dividendsPaid'])
    cf=cf.rolling(4).sum()
    mc = fmp_mcap(sym)
    
    # Merge data
    sy = pd.concat([cf, mc], axis=1, join='inner')
    
    # Compute yields
    sy['divYield'] = -sy['dividendsPaid'] / sy['mktCap']
    sy['bbYield'] = (-sy['commonStockRepurchased'] - sy['commonStockIssued']) / sy['mktCap']
    sy['shYield'] = np.round((-sy['dividendsPaid'] - sy['commonStockRepurchased'] - sy['commonStockIssued']) / sy['mktCap'], 4)
    
    if output == 'df':
        return sy
    sy=sy[-quarters:]    
    
    # Plot the shareholder yield components
    plt.figure(figsize=(10, 6))
    plt.plot(sy.index, sy['divYield'], label='Dividend Yield', color='blue')
    plt.plot(sy.index, sy['divYield'] + sy['bbYield'], label='Shareholder Yield', color='green')
    plt.fill_between(sy.index, sy['divYield'], sy['divYield'] + sy['bbYield'], color='green', alpha=0.5)
    plt.fill_between(sy.index, 0, sy['divYield'], color='blue', alpha=0.5)
    plt.grid()
    plt.title(f'Shareholder Yield for {sym}')
    plt.legend()
    plt.show()


#-------------------------------------------------------------------------------------------------------------------------------


def fmp_growth(sym,facs=[ "fiveYOperatingCFGrowthPerShare"]):
    ''' "revenueGrowth",
    "grossProfitGrowth",
    "ebitgrowth",
    "operatingIncomeGrowth",
    "netIncomeGrowth",
    "epsgrowth",
    "epsdilutedGrowth",
    "weightedAverageSharesGrowth",
    "weightedAverageSharesDilutedGrowth",
    "dividendsperShareGrowth",
    "operatingCashFlowGrowth",
    "freeCashFlowGrowth",
    "tenYRevenueGrowthPerShare",
    "fiveYRevenueGrowthPerShare",
    "threeYRevenueGrowthPerShare",
    "tenYOperatingCFGrowthPerShare",
    "fiveYOperatingCFGrowthPerShare",
    "threeYOperatingCFGrowthPerShare",
    "tenYNetIncomeGrowthPerShare",
    "fiveYNetIncomeGrowthPerShare",
    "threeYNetIncomeGrowthPerShare",
    "tenYShareholdersEquityGrowthPerShare",
    "fiveYShareholdersEquityGrowthPerShare",
    "threeYShareholdersEquityGrowthPerShare",
    "tenYDividendperShareGrowthPerShare",
    "fiveYDividendperShareGrowthPerShare",
    "threeYDividendperShareGrowthPerShare",
    "receivablesGrowth",
    "inventoryGrowth",
    "assetGrowth",
    "bookValueperShareGrowth",
    "debtGrowth",
    "rdexpenseGrowth",
    "sgaexpensesGrowth"'''
    url=f'https://financialmodelingprep.com/api/v3/financial-growth/{sym}?period=annual&apikey={apikey}'
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    stuff = json.loads(data)
    stuff = stuff[0]
    
    
    return pd.Series({key: value for key, value in stuff.items() if key in facs}).T


#--------------------------------------------------------------

def fmp_isActive(syms):
    """Check if stock symbols are actively trading using FMP profile data.
    
    Args:
        syms (str or list): A single stock symbol as a string or a list of stock symbols.
    
    Returns:
        None: This function does not return a value. It prints the symbol and its status
              if the symbol is not actively trading or not found in the FMP system.
    
    Prints:
        str: For each symbol that is not actively trading:
            - "<symbol> False" if the symbol exists but is not actively trading
            - "<symbol> Possible Bad Symbol" if the symbol is not found or has no status
    
    Example:
        >>> fmp_isActive('AAPL')
        # No output if AAPL is actively trading
        >>> fmp_isActive(['AAPL', 'INVALID', 'XYZ'])
        INVALID Possible Bad Symbol
        XYZ Possible Bad Symbol
        # Assuming INVALID and XYZ are not valid/active symbols
    
    Notes:
        - Requires the `fmp_profF` function to fetch profile data from Financial Modeling Prep.
        - Depends on the FMP API returning a dictionary with 'isActivelyTrading' key.
        
    """
    all_active = True
    
    # Ensure syms is a list, even if a single string is provided
    if isinstance(syms, str):
        syms = [syms]

    for sym in syms:
        status = fmp_profF(sym).get('isActivelyTrading')   
        if status is not True:
            all_active = False  # Set flag to False if any symbol is inactive or bad
            if status is None:
                print(sym, 'Possible Bad Symbol')
            else:
                print(sym, status)

    if all_active:
        print("All Symbols are Active on the FMP System")