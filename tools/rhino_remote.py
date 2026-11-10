#!/usr/bin/env python3
"""Run tools/rhino3d_mcpstart.bat / tools/rhino3d_mcpstop.bat on the Rhino PC over SSH.

  rhino_remote.py start [--wait SEC]   run rhino3d_mcpstart.bat, wait until MCP answers
  rhino_remote.py stop                 run rhino3d_mcpstop.bat (closes Rhino; it may ask on the PC)
  rhino_remote.py status               Rhino/proxy processes, listening ports, MCP ping

The .bat files start GUI programs (Rhino), so they must run in the logged-in
user's desktop session, not in the SSH session (session 0, invisible). The tool
registers a scheduled task (interactive logon, highest run level) and starts it;
the .bat window shows up on the Rhino PC's desktop.

Needs: `ssh norang.lan` with key login (remote shell: Windows PowerShell 5.1,
admin user) and the user logged on at the Rhino PC.
"""
import base64, json, subprocess, sys, time, urllib.request

HOST = "norang.lan"
WIN_ROOT = r"D:\rhino3d_ws"
MCP_URL = "http://norang.lan:10501/"
TASKS = {"start": "rhino3d_mcpstart.bat", "stop": "rhino3d_mcpstop.bat"}


def ps(script, timeout=60):
    """Run a PowerShell script on the Rhino PC; return (exit code, output)."""
    script = "[Console]::OutputEncoding=[Text.Encoding]::UTF8\n$ProgressPreference='SilentlyContinue'\n" + script
    enc = base64.b64encode(script.encode("utf-16-le")).decode()
    r = subprocess.run(["ssh", "-x", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST,
                        "powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc],
                       capture_output=True, timeout=timeout)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r.returncode, out.strip()


def run_bat(which):
    bat = TASKS[which]
    name = f"RhinoMCP-{which}"
    code, out = ps(f"""
$bat = '{WIN_ROOT}\\tools\\{bat}'
if (-not (Test-Path $bat)) {{ Write-Output "missing $bat"; exit 2 }}
$user = (Get-CimInstance Win32_ComputerSystem).UserName
if (-not $user) {{ Write-Output 'nobody is logged on at the Rhino PC'; exit 3 }}
$a = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "' + $bat + '"') -WorkingDirectory '{WIN_ROOT}'
$p = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName '{name}' -Action $a -Principal $p -Force | Out-Null
Start-ScheduledTask -TaskName '{name}'
Write-Output "started {bat} as $user (task {name})"
""")
    print(out)
    if code != 0:
        raise SystemExit(code)


def mcp_ping():
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "rhino_remote", "version": "1"}}})
    req = urllib.request.Request(MCP_URL, data=body.encode(), headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=5).read())
        info = r["result"]["serverInfo"]
        return f"{info['name']} {info['version']}"
    except Exception as e:  # noqa: BLE001 - any failure means "not ready"
        return None if not isinstance(e, KeyError) else None


def status():
    _, out = ps("""
Get-Process Rhino -ErrorAction SilentlyContinue | ForEach-Object { "Rhino  PID $($_.Id) session $($_.SessionId) started $($_.StartTime)" }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*rhino3d_mcp_proxy.py*' } | ForEach-Object { "proxy  PID $($_.ProcessId)" }
Get-NetTCPConnection -LocalPort 10500,10501 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { "listen $($_.LocalAddress):$($_.LocalPort) PID $($_.OwningProcess)" }
""")
    print(out or "(no Rhino, no proxy, no listening port)")
    srv = mcp_ping()
    print(f"MCP {MCP_URL}: " + (f"ready ({srv})" if srv else "not answering"))
    return srv


def main(argv):
    if not argv or argv[0] not in ("start", "stop", "status"):
        print(__doc__)
        return 1
    cmd = argv[0]
    if cmd == "status":
        return 0 if status() else 1
    run_bat(cmd)
    if cmd == "stop":
        print("rhino3d_mcpstop.bat is running on the Rhino PC (answer its prompts there if any).")
        return 0
    wait = int(argv[argv.index("--wait") + 1]) if "--wait" in argv else 240
    t0 = time.time()
    while time.time() - t0 < wait:
        srv = mcp_ping()
        if srv:
            print(f"MCP ready after {time.time() - t0:.0f}s: {srv}")
            return 0
        time.sleep(5)
    print(f"MCP did not answer within {wait}s; check the rhino3d_mcpstart.bat window on the Rhino PC.")
    status()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
