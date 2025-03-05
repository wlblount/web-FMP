@echo off
echo Starting FMP Web Tool...
echo Please wait while the server starts...

:: Start Flask in the background
start /B python app.py

:: Wait for 3 seconds to allow Flask to start
timeout /t 3 /nobreak

:: Open the browser
start http://localhost:5000

:: Keep the window open to show any error messages
pause 