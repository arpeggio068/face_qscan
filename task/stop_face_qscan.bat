@echo off
setlocal

set "PORT=8000"
set "SERVER_TITLE=FACE_QUEUE_PYTHON_SERVER"

echo Process using port %PORT%:
netstat -ano | findstr /R /C:":%PORT% .*LISTENING"

echo.
echo Stopping server...

for /f "tokens=5" %%a in (
    'netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"'
) do (
    echo Killing PID %%a...
    taskkill /PID %%a /T /F >nul 2>&1
)

timeout /t 1 /nobreak >nul

echo Closing server console...

powershell.exe -NoProfile -Command ^
  "Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*%SERVER_TITLE%*' } | Stop-Process -Force"

echo Done.
timeout /t 2 /nobreak >nul

endlocal
exit /b