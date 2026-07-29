@echo off
setlocal

echo Closing Chrome...
taskkill /IM chrome.exe /T /F >nul 2>&1

echo Closing Microsoft Edge...
taskkill /IM msedge.exe /T /F >nul 2>&1

echo Stopping Face Queue Server...
call "%~stop_face_qscan.bat"

timeout /t 3 /nobreak >nul

echo Entering sleep mode...
powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend',$false,$false)"

endlocal
exit /b