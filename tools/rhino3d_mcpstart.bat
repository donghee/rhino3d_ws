@echo off
setlocal EnableDelayedExpansion
:: Rhino MCP remote start: firewall + Rhino + Host-rewriting proxy + connection info

set "RHINO_EXE=C:\Program Files\Rhino 9\System\Rhino.exe"
set "RHINO_PORT=10500"
set "REMOTE_PORT=10501"
set "RULE_NAME=Rhino MCP Remote"
set "PROXY=%~dp0rhino3d_mcp_proxy.py"

:: --- Re-launch as Administrator if needed (firewall rule needs it) ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator permission...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

:: --- 1. Firewall rule (recreate to avoid duplicates) ---
echo [1/4] Firewall rule for TCP %REMOTE_PORT%
netsh advfirewall firewall delete rule name="%RULE_NAME%" >nul 2>&1
netsh advfirewall firewall add rule name="%RULE_NAME%" dir=in action=allow protocol=TCP localport=%REMOTE_PORT% >nul

:: --- 2. Start Rhino (running MCPStart on launch) if not running ---
tasklist /FI "IMAGENAME eq Rhino.exe" | find /I "Rhino.exe" >nul
if %errorlevel% neq 0 (
    echo [2/4] Starting Rhino with MCPStart on port %RHINO_PORT%...
    rem In a Rhino script a space acts as Enter: "_MCPStart 10500" answers the port prompt
    start "" "%RHINO_EXE%" /runscript="_MCPStart %RHINO_PORT%"
) else (
    echo [2/4] Rhino is already running
    call :ping_mcp
    if not "!CODE!"=="200" call :send_mcpstart
)

:: --- 3. Wait for Rhino MCP on 127.0.0.1:%RHINO_PORT% (max ~3 min) ---
echo [3/4] Waiting for Rhino MCP on port %RHINO_PORT%...
set /a TRIES=0
:wait_mcp
call :ping_mcp
if "!CODE!"=="200" goto mcp_ready
set /a TRIES+=1
:: Retry MCPStart every ~30 s in case Rhino was still loading the first time
set /a RETRY=TRIES %% 10
if !RETRY!==0 call :send_mcpstart
if !TRIES! geq 60 (
    echo     Rhino MCP did not respond. Check that Rhino finished loading, then run this again.
    pause
    exit /b 1
)
timeout /t 3 /nobreak >nul
goto wait_mcp
:mcp_ready
echo     Rhino MCP is ready.

:: --- 4. Start proxy (0.0.0.0:%REMOTE_PORT% -> 127.0.0.1:%RHINO_PORT%) if not running ---
netstat -ano | findstr /R /C:"0.0.0.0:%REMOTE_PORT% .*LISTENING" >nul
if %errorlevel% neq 0 (
    echo [4/4] Starting proxy on port %REMOTE_PORT%...
    start "Rhino MCP Proxy" /MIN python "%PROXY%" %REMOTE_PORT% %RHINO_PORT%
    timeout /t 2 /nobreak >nul
) else (
    echo [4/4] Proxy is already running on port %REMOTE_PORT%
)

:: --- Connection info ---
echo.
echo ==================================================
echo  Rhino MCP connection info
echo ==================================================
echo  Local  : http://127.0.0.1:%RHINO_PORT%/
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | ForEach-Object { $_.IPAddress }"`) do (
    echo  Remote : http://%%i:%REMOTE_PORT%/
)
echo.
echo  Transport: HTTP (Streamable HTTP / JSON-RPC)
echo  Claude Code example:
echo    claude mcp add --transport http rhino http://^<IP^>:%REMOTE_PORT%/
echo.
echo  Proxy runs in the minimized "Rhino MCP Proxy" window.
echo  Close that window to stop remote access.
echo ==================================================
pause
exit /b 0

:: --- Subroutines ---
:ping_mcp
set "CODE="
for /f %%c in ('curl -s -o nul -m 3 -w "%%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}" http://127.0.0.1:%RHINO_PORT%/ 2^>nul') do set "CODE=%%c"
exit /b 0

:send_mcpstart
:: Focus the Rhino window and type "MCPStart <port>" into its command line
echo     Sending MCPStart %RHINO_PORT% to Rhino command line...
powershell -NoProfile -Command "$w = New-Object -ComObject WScript.Shell; $p = Get-Process Rhino -ErrorAction SilentlyContinue | Select-Object -First 1; if ($p -and $w.AppActivate($p.Id)) { Start-Sleep -Milliseconds 500; $w.SendKeys('{ESC}{ESC}_MCPStart{ENTER}'); Start-Sleep -Milliseconds 500; $w.SendKeys('%RHINO_PORT%{ENTER}'); Write-Host '    sent' } else { Write-Host '    could not focus Rhino window - type MCPStart %RHINO_PORT% in Rhino manually' }"
exit /b 0
