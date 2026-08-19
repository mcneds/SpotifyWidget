$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectDir "MediaWidget\Scripts\pythonw.exe"
$MainPy = Join-Path $ProjectDir "main.py"
$VenvPxExe = Join-Path $ProjectDir "MediaWidget\Scripts\px.exe"

$PxHost = "127.0.0.1"
$PxPort = 3128
$BoschProxy = "rb-proxy-de.bosch.com:8080"

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
    Show-LauncherError "pythonw.exe not found:`n$PythonExe"
    exit 1
}

if (-not (Test-Path $MainPy)) {
    Show-LauncherError "main.py not found:`n$MainPy"
    exit 1
}

if (-not (Test-Path $VenvPxExe)) {
    Show-LauncherError "px.exe not found in the virtual environment:`n$VenvPxExe`n`nInstall it with:`n.\MediaWidget\Scripts\python.exe -m pip install px-proxy"
    exit 1
}

$pxReady = Test-PortOpen -HostName $PxHost -Port $PxPort

if (-not $pxReady) {
    # This matches the manual command that works:
    # .\MediaWidget\Scripts\px.exe --proxy=rb-proxy-de.bosch.com:8080
    #
    # Px listens on 127.0.0.1:3128 by default, matching main.py:
    # PX_PROXY_URL = "http://localhost:3128"
    Start-Process `
        -FilePath $VenvPxExe `
        -ArgumentList "--proxy=$BoschProxy" `
        -WorkingDirectory $ProjectDir `
        -WindowStyle Hidden

    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500

        if (Test-PortOpen -HostName $PxHost -Port $PxPort) {
            $pxReady = $true
            break
        }
    }
}

if (-not $pxReady) {
    Show-LauncherError "Px did not start on ${PxHost}:${PxPort}.`n`nTry this manually to see the real error:`ncd `"$ProjectDir`"`n.\MediaWidget\Scripts\px.exe --proxy=$BoschProxy"
    exit 1
}

Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "`"$MainPy`"" `
    -WorkingDirectory $ProjectDir `
    -WindowStyle Hidden

exit 0
