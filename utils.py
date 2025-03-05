##edited 2/17/25  modified cagr and added cagrTS, added dateSlice

from datetime import datetime 
from io import StringIO
from pandas.tseries.holiday import (
    AbstractHolidayCalendar,
    Holiday,
    nearest_workday,
    USFederalHolidayCalendar
)
from pandas.tseries.offsets import CustomBusinessDay
import csv
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz
##an assortment of utilities 1/30/25    http://localhost:8888/files/utils2.py?_xsrf=2%7C99db802f%7C89f4b4ca8ca6b51ddb8ecd532175eec7%7C1735847160
#-------------------------------------------------------------------

def renCol(df, a):
    """
inputs:  df is a Series (single column dataframe)
         a is a string for new column name
         
outputs:  a new df with the new column name         
    
    """
    df = df.rename(columns={df.columns[0]: a})
    return df

def symlistConv(syms):
    """takes a list of symbols ['A', 'B', 'C'] and converts to
    a fmp multisymbol string format for their API call urls like 'A,B,C'
    """
    syms = tuple(syms)
    return ','.join(syms)

def ddelt(d, start=pd.Timestamp.today()):
    """
    input: d = number of days as an int 
           start= reference date as str 'YYYY-mm-dd'
           returns the date of d days prior to start as str 'YYYY-mm-dd'
         
    
    """
    trading_calendar = USFederalHolidayCalendar()
    bday_us = CustomBusinessDay(calendar=trading_calendar)
    today = start
    last_business_days = pd.date_range(end=today, periods=15000, freq=bday_us)
    holidays_last_days = trading_calendar.holidays(start=last_business_days[0], end=last_business_days[-1])
    for holiday in holidays_last_days:
        last_business_days = last_business_days[last_business_days != holiday]
    return last_business_days[-d].strftime('%Y-%m-%d')

def ytd(today=pd.Timestamp.today()):
    """
    input: date as a string 'YYYY-mm-dd' default is today
    returns:  trading day of that year as int
    
    """
    if isinstance(today, str):
        today = pd.to_datetime(today)
    trading_calendar = USFederalHolidayCalendar()
    bday_us = CustomBusinessDay(calendar=trading_calendar)
    last_year_end = pd.Timestamp(year=today.year - 1, month=12, day=31)
    last_year_bdays = pd.date_range(start=last_year_end, end=today, freq=bday_us)
    holidays_last_year = trading_calendar.holidays(start=last_year_end, end=today)
    for holiday in holidays_last_year:
        last_year_bdays = last_year_bdays[last_year_bdays != holiday]
    return len(last_year_bdays)

def listFrSht(sName='Sectors', fpath='helperfiles/tickerLists.xlsx'):
    """
    sheet names:  'Sectors','ITB','RE-Retail','RE-Residential','SAAS','RE - Hotel','meme','RE - Office','RE - Ind',
                  'RE - Mort','Reg Banks','agXLI','agXLP','Ag Inputs','XHB','Trucking','Restaurants','ARKK',
                  'Leisure','Int FrtLogist','Travel','Lodg','GDX','XRT','Pot', 'position', 'SPAC', 'SHORT'
    """
    return pd.read_excel(fpath, sheet_name=sName, header=None).loc[:, 0].tolist()

def tvsymexp(fpath='helperfiles/Macro.txt'):
    """enter path and file of txt file exported from trading view
       helperfiles/Macro.txt"""
    with open(fpath) as f:
        lines = f.readlines()
    return [i.split(':')[1] for i in lines[0].split(',')]

def get_trading_close_holidays(year=datetime.today().year):
    """
    inputs:  year as int. 
    returns: a datetime index of holiday dates
    """
    inst = USTradingCalendar()
    return inst.holidays(dt.datetime(year - 1, 12, 31), dt.datetime(year, 12, 31))

def impxl(file_path, index_column, other_columns, sheet_name='Sheet1', header=0):
    """
    Import specified columns from an Excel sheet into a pandas DataFrame.

    Parameters
    ----------
    file_path : str
        The path to the Excel file to be read.
    index_column : str
        The name of the column to be used as the index.
    other_columns : list of str
        A list of column names to be imported along with the index column.
    sheet_name : str, optional
        The name of the sheet to read data from. Defaults to 'Sheet1'.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the specified columns, with the index column set as the DataFrame's index.
    
    Example
    -------
    >>> file_path = "C:/path/to/your/file.xlsx"
    >>> index_column = 'nameOfIndexCol'
    >>> other_columns = ['nameOfOtherColumn1', 'nameOfOtherColumn2']
    >>> sheet_name = 'nameOfTheSheet'
    >>> df = impxl(file_path, index_column, other_columns, sheet_name)
    >>> print(df.head())
    """
    columns_to_read = [index_column] + other_columns
    df = pd.read_excel(file_path, sheet_name=sheet_name, usecols=columns_to_read, header=header)
    df.set_index(index_column, inplace=True)
    return df

def make_clickable(val):
    return f'<a target="_blank" href="{val}">{val}</a>'

def lr(X, Y, _print=True):
    """
General Linear Regression function

inputs
    X: series or dataframe columns for the independent variable
    Y: series or dataframe columns for the dependent variable
    _print: (Bool) True returns a printout of the regression coefficients and the coefficients
                   False only returns the coefficients: slope, intercept, r_value, p_value, std_err
                   
outputs: slope, intercept, r_value, p_value, std_err                   
    
    """
    from scipy.stats import linregress
    slope, intercept, r_value, p_value, std_err = linregress(X, Y)
    if _print:
        print(f'eq:  y = {slope: .3f}x + {intercept:.3f}')
        print(f'std er:  {std_err: .3f}')
        print(f'r value:  {r_value:.3f}')
        print(f'p value: {p_value: .3f}')
    return (slope, intercept, r_value, p_value, std_err)

def remove_chars(lst):
    """
cleans up FMP symbols from screen.  remove symbols with "." (foreigh stocks)
and symboils with "-" (preferred stocks)
    """
    return [item for item in lst if '-' not in item and '.' not in item]

from datetime import datetime

def cagr(start_date, end_date, start_value, end_value):
    """
    Calculate the Compound Annual Growth Rate (CAGR).

    CAGR is the rate at which an investment grows annually over a specified period, 
    assuming compounding occurs at a constant rate.

    Parameters:
        start_date (str): The start date in the format 'YYYY-MM-DD'.
        end_date (str): The end date in the format 'YYYY-MM-DD'.
        start_value (float): The initial value of the investment or metric.
        end_value (float): The final value of the investment or metric.

    Returns:
        float: The CAGR as a decimal (e.g., 0.10 for 10%).

    Raises:
        ValueError: If `start_value` is zero (to prevent division errors).
        ValueError: If the number of years between `start_date` and `end_date` is zero.

    Example:
        >>> cagr('2015-01-01', '2020-01-01', 1000, 2000)
        0.1487  # (14.87% annual growth)
    """
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    num_years = (end_date - start_date).days / 365.25  # Account for leap years

    if start_value == 0 or num_years == 0:
        raise ValueError('Start value and number of years must be non-zero')

    cagr = (end_value / start_value) ** (1 / num_years) - 1
    return cagr


def cagrTS(data):
    """
    Calculate CAGR (Compound Annual Growth Rate) for a given Pandas Series or all columns in a DataFrame.
    
    Parameters:
        data (pd.Series or pd.DataFrame): A time-series Pandas Series or DataFrame with a datetime index.

    Returns:
        float (if Series) or pd.Series (if DataFrame) with CAGR values.
    """
    data = data.dropna()  # Ensure no missing values
    if data.empty or len(data) < 2:
        return None  # Not enough data points to calculate CAGR
    
    # Calculate number of years
    n_years = (data.index[-1] - data.index[0]).days / 365.25  # Account for leap years
    
    if isinstance(data, pd.Series):
        # If input is a Series, calculate CAGR for that Series
        V_i, V_f = data.iloc[0], data.iloc[-1]
        return (V_f / V_i) ** (1 / n_years) - 1 if V_i > 0 else None
    
    elif isinstance(data, pd.DataFrame):
        # If input is a DataFrame, calculate CAGR for each column
        cagr_dict = {}
        for col in data.columns:
            col_data = data[col].dropna()
            if len(col_data) < 2:
                cagr_dict[col] = None
            else:
                V_i, V_f = col_data.iloc[0], col_data.iloc[-1]
                cagr_dict[col] = (V_f / V_i) ** (1 / n_years) - 1 if V_i > 0 else None
        return pd.Series(cagr_dict)

def string_to_csv(input_string, csv_file_path):
    """
    ****Only works on text****
    1 - copy a column of text from a spreadsheet and paste into a notebook
    2 - surround text with triple quotes and name...  'text=pasted text
    3 - input: 'text' output: 'text.csv'
    
    """
    fake_file = StringIO(input_string)
    with open(csv_file_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerows([[line.strip()] for line in fake_file])

def parse_multi_line_string(input_string):
    return input_string.strip().split('\n')

def csv_to_list(csv_file_path):
    """
    input: csv file path to a one column csv
    ouput: a list
    """
    result_list = []
    with open(csv_file_path, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            result_list.append(row[0])
    return result_list

def tsConvert(timestamp_ms):
    """converts a ts object like 1677790926832 into
    a datetime object"""
    timestamp_s = timestamp_ms / 1000
    datetime_obj = datetime.fromtimestamp(timestamp_s)
    return datetime_obj

def splitSymWeights(varForData):
    """For importing citrindex from excel into a notebook 
       and converting 
       input:  a 2 column paste from excel like
           WMS	0.17%
           ACM	0.06%
           ALFA	0.18%
           ATMU	0.15%
           BMI	0.33%
       returns:  a tuple of 2 lists... string:symbols and float:weights 
    
        """
    lines = data.strip().split('\n')
    symbols = []
    weights = []
    for line in lines:
        symbol_part, weight_part = line.split()
        symbols.append(symbol_part)
        weights.append(float(weight_part.strip('%')))
    return (symbols, weights)

def histVol(ser, lbk=60):
    """
    input: a series of  prices
    lbk: the number of days to calculate
    returns:  annualized hist vol from a price series using:
    (np.std(np.log(ser/ser.shift()), axis=0)*252**.5
    which is sdt of log returns multiplied by the sqrt of 252
    
    """
    ser = ser[-lbk:]
    return np.round(np.std(np.log(ser / ser.shift()), axis=0) * 252 ** 0.5 * 100, 1)

def beta(df, mkt='SPY', lbk=100):
    """
    inputs:
    df: a single column dataframe of prices
    mkt: str symbol
    lbk: int days
    returns: float"""
    dff = fmp_price(mkt, start=utils.ddelt(len(df) + 1))
    newdf = pd.concat([df, dff], axis=1).dropna()
    x = newdf.iloc[:, 1].tolist()[-(lbk + 1):]
    y = newdf.iloc[:, 0].tolist()[-(lbk + 1):]
    df = pd.DataFrame(list(zip(x, y)), columns=['x', 'y'])
    df = np.log(df / df.shift()).dropna()
    cov = df.cov()
    var = df['x'].var()
    m = cov / var
    print('lookback = ', len(df))
    return np.round(m.iloc[0, 1], 2)

def y_fmt(y, pos):
    if y == 0:
        return '0'
    exp = int(np.log10(abs(y)))
    if exp >= 9:
        return '{:.1f}B'.format(y / 1000000000.0)
    elif exp >= 6:
        return '{:.1f}M'.format(y / 1000000.0)
    elif exp >= 3:
        return '{:.1f}K'.format(y / 1000.0)
    else:
        return '{:.0f}'.format(y)

def myPlot(data, kind='line'):
    fig, ax = plt.subplots(figsize=(10, 6))
    data.plot(kind=kind, ax=ax)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(y_fmt))
    plt.legend()
    plt.grid(alpha=0.5, linestyle='--')



def dateSlice(df, years=5):
    
    """
    Slice a datetime-indexed DataFrame to keep only the most recent `years` of data.

    Parameters:
        df (pd.DataFrame): A Pandas DataFrame with a DatetimeIndex.
        years (int, optional): Number of years to keep (default is 5).

    Returns:
        pd.DataFrame: A DataFrame containing only the most recent `years` of data.
    """
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("The DataFrame must have a DatetimeIndex and cannot be empty.")

    # Determine the most recent date in the DataFrame
    latest_date = df.index.max()
    
    # Calculate the cutoff date
    cutoff_date = latest_date - pd.DateOffset(years=years)

    # Slice the DataFrame to keep only data from the last `years`
    return df[df.index >= cutoff_date]
