import os

api_key = os.getenv('FMP_API_KEY')
if api_key:
    print("FMP_API_KEY is set!")
    print(f"First few characters of the key: {api_key[:4]}...")
else:
    print("FMP_API_KEY is not set!") 