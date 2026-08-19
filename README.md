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
- Optional Px proxy support for restricted/corporate networks

## Requirements

- Windows
- Python 3
- A Spotify account with access to the Spotify Web API
- A Spotify Developer application

Python packages used by the widget:

```text
PyQt6
requests
spotipy
```

For the included corporate-network launcher, the environment also uses:

```text
px-proxy
requests-negotiate-sspi
```

## 1. Clone the repository

```powershell
git clone https://github.com/mcneds/SpotifyWidget.git
cd SpotifyWidget
```

## 2. Create a Spotify application

1. Open the Spotify Developer Dashboard.
2. Create an application.
3. Copy its **Client ID** and **Client Secret**.
4. Add the following redirect URI to the application's allowed redirect URIs:

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
.\MediaWidget\Scripts\python.exe -m pip install PyQt6 requests spotipy
```

### Normal network / personal computer

`main.py` currently has Px proxy support enabled by default:

```python
USE_PX_PROXY = True
```

If you are **not** using the Px proxy setup described below, change it to:

```python
USE_PX_PROXY = False
```

Then run the widget directly:

```powershell
.\MediaWidget\Scripts\python.exe .\main.py
```

On first launch, Spotify authentication opens in your browser. After authorization, Spotify redirects back to the local callback address and the token is cached locally.

## Corporate / Px proxy setup

The repository also contains `run_mediawidget.ps1` and `MediaWidget.bat` for a Px-based corporate proxy setup.

Install the additional packages into the same virtual environment:

```powershell
.\MediaWidget\Scripts\python.exe -m pip install px-proxy requests-negotiate-sspi
```

The current launcher is configured to start Px on `127.0.0.1:3128` and forward through:

```text
rb-proxy-de.bosch.com:8080
```

`main.py` then sends Spotify/API traffic through:

```text
http://localhost:3128
```

With that setup, launch using:

```powershell
.\MediaWidget.bat
```

or:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\run_mediawidget.ps1
```

If you are on another corporate network, change the proxy address in `run_mediawidget.ps1` to match your environment.

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
main.py                 Main PyQt6 widget and Spotify integration
credentials.py          Spotify application credentials/configuration
run_mediawidget.ps1     Windows launcher with Px proxy startup
MediaWidget.bat         Hidden PowerShell launcher
MediaWidget.ico         Application icon
play.svg                Play icon
skip-backward.svg       Previous-track icon
skip-forward.svg        Next-track icon
MediaWidget.lnk         Windows shortcut
```

The `MediaWidget/` virtual environment itself is created locally and should not be committed.

## Troubleshooting

### `Spotify auth error`

Check that:

- `CLIENT_ID` and `CLIENT_SECRET` are correct.
- `http://127.0.0.1:25566/callback` is registered as a redirect URI for your Spotify application.
- The values in `credentials.py` do not still contain the placeholder text.

### Widget says `Nothing playing`

Start playback on Spotify first. The widget reads the currently active Spotify playback session/device.

### Connection errors outside the corporate network

Set:

```python
USE_PX_PROXY = False
```

and run `main.py` directly instead of using the Px-specific launcher.

### `pythonw.exe not found`

The launcher expects this path:

```text
MediaWidget\Scripts\pythonw.exe
```

Create the virtual environment using the setup commands above and keep the name `MediaWidget`.

### `px.exe not found`

Install Px into the virtual environment:

```powershell
.\MediaWidget\Scripts\python.exe -m pip install px-proxy
```

## Notes

This project is an independent Spotify Web API client and is not affiliated with or endorsed by Spotify.
