# SpotifyWidget

A small always-on-top Spotify desktop widget for Windows, built with Python and PyQt6.

SpotifyWidget shows the currently playing track and album art and provides previous, play/pause, and next controls in a compact frameless window. The widget can be dragged from the top handle and snaps to a desktop-icon-style grid when released.

## Features

- Current track title and artist
- Album artwork
- Previous, play/pause, and next controls
- Frameless, translucent, always-on-top window
- Draggable top handle
- Snaps to a desktop-style grid after dragging
- Spotify OAuth login with a local callback
- Refreshes playback state automatically
- Remembers Spotify authentication in a local `.spotify_cache` file
- Automatic Windows/system proxy detection through Px
- Optional per-machine proxy overrides without editing tracked source files

## Requirements

- Windows
- Python 3.10 or newer
- A Spotify account with access to the Spotify Web API
- A Spotify Developer application

## 1. Clone the repository

```powershell
git clone https://github.com/mcneds/SpotifyWidget.git
cd SpotifyWidget
```

## 2. Create a Spotify application

1. Open the Spotify Developer Dashboard.
2. Create an application.
3. Copy its **Client ID** and **Client Secret**.
4. Add this redirect URI to the application's allowed redirect URIs:

```text
http://127.0.0.1:25566/callback
```

## 3. Configure credentials

Open `credentials.py` and replace the placeholder values:

```python
CLIENT_ID = "your client ID"
CLIENT_SECRET = "your client secret"
REDIRECT_URI = "http://127.0.0.1:25566/callback"
```

Do not commit your real credentials to a public repository.

## 4. Create the Python environment

The included launcher expects the virtual environment to be named `MediaWidget`:

```powershell
python -m venv MediaWidget
.\MediaWidget\Scripts\python.exe -m pip install --upgrade pip
.\MediaWidget\Scripts\python.exe -m pip install -r requirements.txt
```

## 5. Launch

Use:

```powershell
.\MediaWidget.bat
```

or:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\run_mediawidget.ps1
```

On first launch, Spotify authentication opens in your browser. After authorization, Spotify redirects back to the local callback address and the token is cached locally.

## Automatic proxy behavior

`main.py` always talks to the local Px endpoint at:

```text
http://localhost:3128
```

The launcher starts Px automatically if it is not already running.

The default proxy mode is:

```text
auto
```

In auto mode, Px uses proxy definitions from Windows Internet Options or proxy environment variables when present. If no upstream proxy is configured, Px connects directly. This means the same launcher can normally be used on a home network and on a corporate network without changing `main.py`.

### Per-machine configuration

If automatic detection is not enough, copy the example configuration:

```powershell
Copy-Item .\mediawidget_config.example.ps1 .\mediawidget_config.ps1
```

`mediawidget_config.ps1` is gitignored, so machine-specific proxy information will not be committed.

Available modes:

```powershell
$PxMode = "auto"
```

Automatically discover the Windows/system proxy, or connect directly if none exists.

```powershell
$PxMode = "direct"
```

Force all traffic through Px to connect directly without an upstream proxy.

```powershell
$PxMode = "proxy"
$PxProxy = "proxy.example.com:8080"
```

Force a particular upstream proxy.

### Environment-variable overrides

Environment variables take priority over `mediawidget_config.ps1`:

```powershell
$env:MEDIAWIDGET_PROXY_MODE = "proxy"
$env:MEDIAWIDGET_UPSTREAM_PROXY = "proxy.example.com:8080"
.\MediaWidget.bat
```

Valid values for `MEDIAWIDGET_PROXY_MODE` are:

```text
auto
direct
proxy
```

This is useful for temporary overrides without editing any files.

## Controls

| Action | Control |
|---|---|
| Move widget | Drag the handle at the top |
| Previous track | Left transport button |
| Play / pause | Center transport button |
| Next track | Right transport button |
| Close | `X` in the upper-right |
| Close from keyboard | `Esc` or `Ctrl+Q` |

The widget polls Spotify approximately every five seconds to refresh the current playback state.

## Project files

```text
main.py                         Main PyQt6 widget and Spotify integration
credentials.py                  Spotify application credentials/configuration
run_mediawidget.ps1             Windows launcher and automatic Px setup
MediaWidget.bat                 Hidden PowerShell launcher
mediawidget_config.example.ps1  Optional local proxy configuration template
requirements.txt                Python dependencies
MediaWidget.ico                 Application icon
play.svg                        Play icon
skip-backward.svg               Previous-track icon
skip-forward.svg                Next-track icon
MediaWidget.lnk                 Windows shortcut
```

Locally generated files such as the `MediaWidget/` virtual environment, `.spotify_cache`, `__pycache__`, and `mediawidget_config.ps1` are ignored by Git.

## Troubleshooting

### `Spotify auth error`

Check that:

- `CLIENT_ID` and `CLIENT_SECRET` are correct.
- `http://127.0.0.1:25566/callback` is registered as a redirect URI for your Spotify application.
- The values in `credentials.py` do not still contain the placeholder text.

### Widget says `Nothing playing`

Start playback on Spotify first. The widget reads the currently active Spotify playback session/device.

### Px starts but cannot reach Spotify

Try forcing direct mode temporarily:

```powershell
$env:MEDIAWIDGET_PROXY_MODE = "direct"
.\MediaWidget.bat
```

If your network requires a specific proxy, create `mediawidget_config.ps1` and use:

```powershell
$PxMode = "proxy"
$PxProxy = "proxy.example.com:8080"
```

### `pythonw.exe not found`

The launcher expects:

```text
MediaWidget\Scripts\pythonw.exe
```

Create the virtual environment using the setup commands above and keep the name `MediaWidget`.

### `px.exe not found`

Install the project dependencies:

```powershell
.\MediaWidget\Scripts\python.exe -m pip install -r requirements.txt
```

## Notes

This project is an independent Spotify Web API client and is not affiliated with or endorsed by Spotify.
