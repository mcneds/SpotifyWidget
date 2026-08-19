# Copy this file to mediawidget_config.ps1 to override proxy behaviour locally.
# mediawidget_config.ps1 is gitignored.

# Valid values: auto, direct, proxy
$PxMode = "auto"

# Only needed for proxy mode, or to explicitly override auto mode.
# Example:
# $PxProxy = "proxy.example.com:8080"
$PxProxy = ""
