@echo off

cd /d "D:\Nodejs_Project\face_qscan"

start "FACE_QUEUE_PYTHON_SERVER" cmd /k ".venv\Scripts\python.exe app.py"

timeout /t 3 /nobreak >nul

start "" "http://127.0.0.1:8000"

exit /b