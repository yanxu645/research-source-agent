param(
    [ValidateRange(1024, 65515)][int]$Port = 8502,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
$pythonPath = Join-Path $projectDir '.venv\Scripts\python.exe'
$appPath = Join-Path $projectDir 'app.py'
$runtimeDir = Join-Path $projectDir '.runtime'
$statePath = Join-Path $runtimeDir 'server.json'
$launchLock = $null

function Test-ServerHealth([int]$ServerPort) {
    $response = $null
    $reader = $null
    try {
        $request = [System.Net.WebRequest]::Create("http://127.0.0.1:$ServerPort/_stcore/health")
        $request.Proxy = $null
        $request.Timeout = 2000
        $request.ReadWriteTimeout = 2000
        $response = $request.GetResponse()
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        return ($response.StatusCode -eq 200 -and $reader.ReadToEnd().Trim() -eq 'ok')
    } catch { return $false }
    finally {
        if ($reader) { $reader.Dispose() }
        if ($response) { $response.Dispose() }
    }
}

function Test-FreePort([int]$ServerPort) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $ServerPort)
    try {
        $listener.Server.ExclusiveAddressUse = $true
        $listener.Start()
        return $true
    } catch { return $false }
    finally { $listener.Stop() }
}

function Open-ResearchPage([int]$ServerPort) {
    $url = "http://127.0.0.1:$ServerPort"
    @(
        'Research Source Agent - local access'
        "URL: $url"
        "Last successful health check: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
        ''
        'Open this URL on the computer running the app.'
        'If it refuses connections, double-click start_app.cmd to start the app again.'
        'The launcher updates this file with the actual port, even if it is not 8502.'
        'This file records the last check; it is not a live service status.'
        'Detailed logs: .runtime/streamlit.log and .runtime/streamlit-error.log'
    ) | Set-Content -LiteralPath (Join-Path $projectDir 'streamlit-8502.log') -Encoding utf8
    Write-Output "READY $url"
    if (-not $NoBrowser) { Start-Process $url }
}

try {
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    # Serialize double clicks so two launchers cannot start competing servers.
    $lockDeadline = (Get-Date).AddSeconds(75)
    while (-not $launchLock) {
        try {
            $launchLock = [System.IO.File]::Open(
                (Join-Path $runtimeDir 'start.lock'),
                [System.IO.FileMode]::OpenOrCreate,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
        } catch [System.IO.IOException] {
            if ((Get-Date) -ge $lockDeadline) { throw 'Another launcher is still starting. Please retry shortly.' }
            Start-Sleep -Milliseconds 250
        }
    }

    if (Test-Path -LiteralPath $statePath) {
        try {
            $saved = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
            $existing = Get-Process -Id $saved.pid -ErrorAction Stop
            $sameProcess = $existing.StartTime.ToUniversalTime().Ticks.ToString() -eq $saved.startedUtcTicks
            if ($sameProcess -and $saved.appPath -eq $appPath) {
                if (Test-ServerHealth $saved.port) {
                    Open-ResearchPage $saved.port
                    exit 0
                }
                throw 'The saved server is running but is not responding. Check .runtime logs before restarting it.'
            }
        } catch {
            if ($_.Exception.Message -like 'The saved server*') { throw }
            # Missing processes and damaged state files are recovered by a new launch.
        }
    }

    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Project Python is missing. Restore .venv and install requirements.txt.'
    }
    Push-Location (Split-Path -Parent $projectDir)
    try {
        & $pythonPath -c 'import streamlit; from research_source_agent.agent import ResearchSourceAgent' 2>&1 |
            Out-File -LiteralPath (Join-Path $runtimeDir 'preflight.log') -Encoding utf8
        if ($LASTEXITCODE -ne 0) { throw 'Python dependency check failed. See .runtime/preflight.log.' }
    } finally { Pop-Location }

    $selectedPort = $null
    foreach ($candidate in $Port..($Port + 20)) {
        if (Test-FreePort $candidate) { $selectedPort = $candidate; break }
    }
    if ($null -eq $selectedPort) { throw 'No available local port in the requested range.' }
    if ($selectedPort -ne $Port) { Write-Output "Port $Port is occupied; using $selectedPort." }

    $arguments = @(
        '-m', 'streamlit', 'run', ('"' + $appPath + '"'),
        '--server.address', '127.0.0.1', '--server.port', "$selectedPort",
        '--server.headless', 'true', '--browser.gatherUsageStats', 'false'
    )
    # On Windows this server continues after the launching terminal exits.
    $server = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectDir `
        -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'streamlit.log') `
        -RedirectStandardError (Join-Path $runtimeDir 'streamlit-error.log') -PassThru
    $serverStartedTicks = $server.StartTime.ToUniversalTime().Ticks.ToString()
    $deadline = (Get-Date).AddSeconds(60)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        $server.Refresh()
        if ($server.HasExited) { throw "Streamlit exited ($($server.ExitCode)). See .runtime/streamlit-error.log." }
        if (Test-ServerHealth $selectedPort) { $ready = $true; break }
        Start-Sleep -Milliseconds 300
    }
    if (-not $ready) { throw 'Startup timed out. See .runtime/streamlit-error.log.' }

    @{
        pid = $server.Id
        startedUtcTicks = $serverStartedTicks
        appPath = $appPath
        port = $selectedPort
        url = "http://127.0.0.1:$selectedPort"
    } | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
    Open-ResearchPage $selectedPort
} catch {
    Write-Output "START FAILED: $($_.Exception.Message)"
    Write-Output "Logs: $runtimeDir"
    exit 1
} finally {
    if ($launchLock) { $launchLock.Dispose() }
}
