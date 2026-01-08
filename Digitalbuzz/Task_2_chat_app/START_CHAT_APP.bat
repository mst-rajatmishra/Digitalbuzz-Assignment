@echo off
echo ========================================
echo    Starting Real-Time Chat Application
echo ========================================
echo.
echo Server will start on: http://127.0.0.1:5000
echo.
echo To test real-time chat:
echo 1. Open multiple browser tabs/windows
echo 2. Go to: http://127.0.0.1:5000
echo 3. Login with different names in each tab
echo 4. Join the same room
echo 5. Start chatting!
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

cd /d "%~dp0"
"C:\Users\RAJAT\AppData\Local\Programs\Python\Python313\python.exe" app.py
