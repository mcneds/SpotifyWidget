$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectDir "MediaWidget\Scripts\pythonw.exe"
$MainPy = Join-Path $ProjectDir "main.py"
$VenvPxExe = Join-Path $ProjectDir "MediaWidget\Scripts\px.exe"
$ConfigPath = Join-Path $ProjectDir "mediawidget_config.ps1"

$PxHost = "127.0.0.1"
$PxPort = 3128

# Proxy modes:
#   auto   - let Px discover Windows/system proxy settings; direct if none exist
#   direct - force Px to bypass all upstream proxies
#   proxy  - force the upstream proxy specified by $PxProxy
$PxMode = "auto"
$PxProxy = ""

# Optional per-machine configuration. This file is intentionally gitignored.
if (Test-Path $ConfigPath) {
    . $ConfigPath
}

# Environment variables override the local config file.
if ($env:MEDIAWIDGET_PROXY_MODE) {
    $PxMode = $env:MEDIAWIDGET_PROXY_MODE
}

if ($env:MEDIAWIDGET_UPSTREAM_PROXY) {
    $PxProxy = $env:MEDIAWIDGET_UPSTREAM_PROXY
}

$PxMode = "$PxMode".Trim().ToLowerInvariant()
$PxProxy = "$PxProxy".Trim()

function Show-LauncherError {
    param (
        [string]$Message
    )

    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Message, "MediaWidget launcher") | Out-Null
}

function Test-PortOpen {
    param (
        [string]$HostName,
        [int]$Port
    )

    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $success = $async.AsyncWaitHandle.WaitOne(300, $false)

        if ($success) {
            $client.EndConnect($async)
            $client.Close()
            return $true
        }

        $client.Close()
        return $false
    }
    catch {
        return $false
    }
}

Set-Location $ProjectDir

if (-not (Test-Path $PythonExe)) {
    Show-LauncherError "pythonw.exe not found:`n$PythonExe`n`nCreate the virtual environment with:`npython -m venv MediaWidget"
    exit 1
}

if (-not (Test-Path $MainPy)) {
    Show-LauncherError "main.py not found:`n$MainPy"
    exit 1
}

if (-not (Test-Path $VenvPxExe)) {
    Show-LauncherError "px.exe not found in the virtual environment:`n$VenvPxExe`n`nInstall the project dependencies with:`n.\MediaWidget\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

if ($PxMode -notin @("auto", "direct", "proxy")) {
    Show-LauncherError "Invalid proxy mode '$PxMode'.`n`nUse auto, direct, or proxy in mediawidget_config.ps1 or MEDIAWIDGET_PROXY_MODE."
    exit 1
}

if ($PxMode -eq "proxy" -and [string]::IsNullOrWhiteSpace($PxProxy)) {
    Show-LauncherError "Proxy mode is set to 'proxy', but no upstream proxy was supplied.`n`nSet `$PxProxy in mediawidget_config.ps1 or set MEDIAWIDGET_UPSTREAM_PROXY."
    exit 1
}

$PxArgs = @()

switch ($PxMode) {
    "direct" {
        # Px remains the local endpoint expected by main.py, but all destinations
        # bypass any configured upstream proxy.
        $PxArgs = @("--noproxy=0.0.0.0/0")
    }

    "proxy" {
        $PxArgs = @("--proxy=$PxProxy")
    }

    "auto" {
        # If an upstream was explicitly supplied, use it even in auto mode.
        # Otherwise Px discovers Internet Options/environment proxy settings and
        # connects directly when no upstream proxy is configured.
        if (-not [string]::IsNullOrWhiteSpace($PxProxy)) {
            $PxArgs = @("--proxy=$PxProxy")
        }
    }
}

$pxReady = Test-PortOpen -HostName $PxHost -Port $PxPort

if (-not $pxReady) {
    $startParams = @{
        FilePath = $VenvPxExe
        WorkingDirectory = $ProjectDir
        WindowStyle = "Hidden"
    }

    if ($PxArgs.Count -gt 0) {
        $startParams.ArgumentList = $PxArgs
    }

    Start-Process @startParams

    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500

        if (Test-PortOpen -HostName $PxHost -Port $PxPort) {
            $pxReady = $true
            break
        }
    }
}

if (-not $pxReady) {
    $manualCommand = ".\MediaWidget\Scripts\px.exe"
    if ($PxArgs.Count -gt 0) {
        $manualCommand += " " + ($PxArgs -join " ")
    }

    Show-LauncherError "Px did not start on ${PxHost}:${PxPort}.`n`nProxy mode: $PxMode`n`nRun this manually to see the real error:`ncd `"$ProjectDir`"`n$manualCommand"
    exit 1
}

Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "`"$MainPy`"" `
    -WorkingDirectory $ProjectDir `
    -WindowStyle Hidden

exit 0
