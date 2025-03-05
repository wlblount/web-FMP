from flask import Flask, render_template, request, jsonify
import fmp
import pandas as pd
from tabulate import tabulate
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data', methods=['POST'])
def get_data():
    try:
        function_type = request.form.get('function_type')
        symbol = request.form.get('symbol', '').upper()
        period = request.form.get('period', '30min')
        
        logger.info(f"Processing request for {function_type} with symbol {symbol}")
        
        if function_type == "Intraday Data":
            df = fmp.fmp_intra(symbol, period=period)
            if not df.empty:
                df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float).round(3).applymap(lambda x: f"{x:.3f}")
                df['volume'] = df['volume'].apply(lambda x: f"{int(x):,}").str.rjust(15)
                result = tabulate(df, headers='keys', tablefmt='fancy_grid', numalign='left', stralign='left')
                return jsonify({'success': True, 'data': result})
            return jsonify({'success': False, 'error': 'No intraday data found for the given symbol.'})

        elif function_type == "Company Profile":
            data = fmp.fmp_profF(symbol)
            if data:
                table_data = [(key, f"{value:,}" if key == 'mktCap' else value) 
                             for key, value in data.items() if key != 'description']
                result = tabulate(table_data, headers=['Field', 'Value'], 
                                tablefmt='fancy_grid', numalign='left', stralign='left')
                description = data.get('description', '')
                return jsonify({
                    'success': True, 
                    'data': result,
                    'description': description
                })
            return jsonify({'success': False, 'error': 'No profile data found for the given symbol.'})

        elif function_type == "Search Data":
            df = fmp.fmp_search(symbol)
            if not df.empty:
                result = tabulate(df, headers='keys', tablefmt='fancy_grid', 
                                numalign='left', stralign='left')
                return jsonify({'success': True, 'data': result})
            return jsonify({'success': False, 'error': 'No search results found for the given term.'})

        elif function_type == "Earnings Dates":
            df = fmp.fmp_earnSym(symbol)
            if not df.empty:
                df_modified = df.drop(columns=['symbol']).reset_index(drop=True)
                df_modified.rename(columns={
                    'epsEstimated': 'epsEst',
                    'revenue': 'rev (mil)',
                    'revenueEstimated': 'revEst (mil)',
                    'fiscalDateEnding': 'fiscal',
                    'updatedFromDate': 'updated',
                }, inplace=True)
                
                df_modified['rev (mil)'] = df_modified['rev (mil)'].div(1_000_000).round(0).fillna(0).apply(
                    lambda x: f"{int(x):,}" if not pd.isna(x) else "N/A")
                df_modified['revEst (mil)'] = df_modified['revEst (mil)'].div(1_000_000).round(0).fillna(0).apply(
                    lambda x: f"{int(x):,}" if not pd.isna(x) else "N/A")
                df_modified = df_modified[['date', 'time', 'eps', 'epsEst', 'rev (mil)', 'revEst (mil)', 'fiscal', 'updated']]
                result = tabulate(df_modified, headers='keys', tablefmt='fancy_grid', 
                                numalign='left', stralign='left')
                return jsonify({'success': True, 'data': result})
            return jsonify({'success': False, 'error': 'No earnings data found for the given symbol.'})

        elif function_type == "Dividends":
            df = fmp.fmp_div(symbol).tail(10)
            if not df.empty:
                df_modified = df.drop(columns=['adjDividend'])
                df_modified.index = pd.to_datetime(df_modified.index).strftime("%m-%d-%y")
                df_modified.rename(columns={
                    'recordDate': 'recDate',
                    'paymentDate': 'payDate',
                    'declarationDate': 'decDate',
                    'trailYield': 'yieldttm',
                    'curYield': 'yield',
                }, inplace=True)
                date_columns = ["recDate", 'payDate', "decDate"]
                for col in date_columns:
                    df_modified[col] = pd.to_datetime(df_modified[col]).dt.strftime("%m-%d-%y")
                result = tabulate(df_modified, headers='keys', tablefmt='fancy_grid', 
                                numalign='left', stralign='left')
                return jsonify({'success': True, 'data': result})
            return jsonify({'success': False, 'error': 'No dividend data found for the given symbol.'})

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 