@echo off
setlocal EnableDelayedExpansion
:: Rhino MCP remote stop: undo rhino3d_mcpstart.bat
:: (stop proxy + remove firewall rule + close Rhino)

set "RULE_NAME=Rhino MCP Remote"
set "CLOSE_WAIT=30"

:: --- Re-launch as Administrator if needed (firewall rule needs it) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator permission...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: --- 1. Stop proxy ---
echo [1/4] Stopping Rhino MCP proxy...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*rhino3d_mcp_proxy.py*' }; if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('    stopped PID ' + $_.ProcessId) } } else { Write-Host '    proxy was not running' }"

:: --- 2. Remove firewall rule (all rules with this name) ---
echo [2/4] Removing firewall rule "%RULE_NAME%"...
netsh advfirewall firewall delete rule name="%RULE_NAME%" >nul 2>&1 && echo     removed || echo     rule not found

:: --- 3. Clean up old netsh portproxy entry, if any ---
echo [3/4] Cleaning up old port proxy entry...
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=10500 >nul 2>&1 && echo     removed || echo     none

:: --- 4. Close Rhino (normal close first, so Rhino can ask to save) ---
echo [4/4] Closing Rhino...
call :rhino_running
if "!RUNNING!"=="0" (
    echo     Rhino was not running
    goto done
)
powershell -NoProfile -Command "Get-Process Rhino -ErrorAction SilentlyContinue | ForEach-Object { [void]$_.CloseMainWindow() }"
echo     Asked Rhino to close. Answer its save dialog if one appears (waiting up to %CLOSE_WAIT% s)...
set /a WAITED=0
:wait_close
call :rhino_running
if "!RUNNING!"=="0" (
    echo     Rhino closed
    goto done
)
if !WAITED! geq %CLOSE_WAIT% goto force_close
timeout /t 1 /nobreak >nul
set /a WAITED+=1
goto wait_close

:force_close
echo     Rhino is still running (a save dialog may be open).
choice /C YN /M "    Force-close Rhino? Unsaved changes will be lost"
if errorlevel 2 (
    echo     Left Rhino running
    goto done
)
taskkill /F /IM Rhino.exe >nul 2>&1 && echo     Rhino force-closed || echo     could not close Rhino

:done
echo.
echo Rhino MCP remote access is off (proxy stopped, firewall rule removed).
pause
exit /b 0

:: --- Subroutines ---
:rhino_running
set "RUNNING=0"
tasklist /FI "IMAGENAME eq Rhino.exe" | find /I "Rhino.exe" >nul && set "RUNNING=1"
exit /b 0
