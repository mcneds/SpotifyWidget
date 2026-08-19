import os
import sys
import time
import threading
from io import BytesIO
from pathlib import Path
import importlib.util

import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QSize,
    QRectF,
    QByteArray,
    QPoint,
    QEvent,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QFontMetrics,
    QPainter,
    QColor,
    QCursor,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSizePolicy,
)
from PyQt6.QtSvg import QSvgRenderer

try:
    from requests_negotiate_sspi import HttpNegotiateAuth
except ImportError:
    HttpNegotiateAuth = None


# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent


# -----------------------------------------------------------------------------
# Credentials
# -----------------------------------------------------------------------------
local_credentials_path = BASE_DIR / "credentials.py"
if not local_credentials_path.exists():
    raise RuntimeError("Missing credentials.py beside main.py")

spec = importlib.util.spec_from_file_location("local_credentials", local_credentials_path)
local_credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_credentials)

CLIENT_ID = getattr(local_credentials, "CLIENT_ID", None)
CLIENT_SECRET = getattr(local_credentials, "CLIENT_SECRET", None)
REDIRECT_URI = getattr(
    local_credentials,
    "REDIRECT_URI",
    "http://127.0.0.1:25566/callback",
)

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("credentials.py must contain CLIENT_ID and CLIENT_SECRET")


# -----------------------------------------------------------------------------
# Proxy behavior
# -----------------------------------------------------------------------------
USE_PX_PROXY = True
PX_PROXY_URL = "http://localhost:3128"

existing_no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
needed_no_proxy = ["localhost", "127.0.0.1"]
merged_no_proxy = existing_no_proxy
for item in needed_no_proxy:
    if item not in merged_no_proxy:
        merged_no_proxy = f"{merged_no_proxy},{item}" if merged_no_proxy else item

os.environ["NO_PROXY"] = merged_no_proxy
os.environ["no_proxy"] = merged_no_proxy


# -----------------------------------------------------------------------------
# Desktop icon grid sizing
# -----------------------------------------------------------------------------
def twips_to_pixels(twips):
    return abs(twips) // 15


icon_spacing_twips = -1140
icon_vertical_spacing_twips = -1136

icon_width = twips_to_pixels(icon_spacing_twips)
icon_height = twips_to_pixels(icon_vertical_spacing_twips)

widget_width = icon_width * 3
widget_height = 270

album_size = 104
button_height = 34
button_icon_size = 18


# -----------------------------------------------------------------------------
# Spotify auth/client
# -----------------------------------------------------------------------------
def make_spotify_client():
    session = requests.Session()

    if USE_PX_PROXY:
        session.trust_env = False
        session.proxies = {
            "http": PX_PROXY_URL,
            "https": PX_PROXY_URL,
        }
    else:
        session.trust_env = True
        if HttpNegotiateAuth is not None:
            session.auth = HttpNegotiateAuth()

    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-playback-state,user-modify-playback-state,user-read-currently-playing",
        open_browser=True,
        cache_path=str(BASE_DIR / ".spotify_cache"),
        requests_session=session,
    )

    return spotipy.Spotify(
        auth_manager=auth_manager,
        requests_session=session,
        requests_timeout=15,
    )


sp = make_spotify_client()


# -----------------------------------------------------------------------------
# Helper widgets
# -----------------------------------------------------------------------------
class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.full_text = text
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setText(self, text):
        self.full_text = text or ""
        self.update_elided_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elided_text()

    def update_elided_text(self):
        metrics = QFontMetrics(self.font())
        usable_width = max(10, self.width() - 14)
        QLabel.setText(
            self,
            metrics.elidedText(
                self.full_text,
                Qt.TextElideMode.ElideRight,
                usable_width,
            ),
        )


class CloseCircleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Close")
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect().adjusted(0, 0, -1, -1)

        if self.isDown():
            bg = QColor(255, 40, 40, 225)
            fg = QColor(255, 255, 255)
        elif self.underMouse():
            bg = QColor(255, 80, 80, 185)
            fg = QColor(255, 255, 255)
        else:
            bg = QColor(255, 255, 255, 22)
            fg = QColor(255, 255, 255, 220)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawEllipse(rect)

        pen = QPen(fg)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = 4.0

        painter.drawLine(int(cx - r), int(cy - r), int(cx + r), int(cy + r))
        painter.drawLine(int(cx + r), int(cy - r), int(cx - r), int(cy + r))
        painter.end()


# -----------------------------------------------------------------------------
# Main widget
# -----------------------------------------------------------------------------
class SpotifyWidget(QWidget):
    refresh_requested = pyqtSignal()
    error_requested = pyqtSignal(str, str)
    track_loaded = pyqtSignal(object, object, object)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Spotify Widget")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(widget_width, widget_height)
        self.setObjectName("root")

        self.setStyleSheet(
            """
            QWidget#root {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 52);
                border-radius: 12px;
            }

            QLabel {
                color: white;
                background: transparent;
            }

            QWidget#grabArea {
                background: transparent;
                border: none;
            }

            QWidget#grabVisual {
                background-color: rgba(255, 255, 255, 120);
                border-radius: 999px;
            }

            QWidget#grabVisual[hovered="true"] {
                background-color: rgba(255, 255, 255, 190);
            }

            QWidget#grabVisual[pressed="true"] {
                background-color: rgba(29, 185, 84, 220);
            }

            QPushButton {
                background-color: #1DB954;
                border: none;
                border-radius: 12px;
                padding: 2px;
                color: black;
                font-size: 17px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #25d366;
            }

            QPushButton:pressed {
                background-color: #169c46;
            }
            """
        )

        self.dragging = False
        self.drag_offset = QPoint()

        self.auth_failed = False
        self.is_playing = False
        self.loading = False
        self.active_device_id = None
        self.current_artist_text = "Starting..."

        root = QVBoxLayout()
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(5)
        root.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(root)

        # ---------------------------------------------------------------------
        # Header row: centered grab bar + top-right close button.
        # ---------------------------------------------------------------------
        self.grab_area = QWidget()
        self.grab_area.setObjectName("grabArea")
        self.grab_area.setFixedHeight(24)
        self.grab_area.setCursor(Qt.CursorShape.ArrowCursor)
        self.grab_area.installEventFilter(self)

        grab_row = QHBoxLayout()
        grab_row.setContentsMargins(0, 0, 0, 0)
        grab_row.setSpacing(0)
        self.grab_area.setLayout(grab_row)

        self.left_header_spacer = QWidget()
        self.left_header_spacer.setFixedSize(22, 22)
        self.left_header_spacer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        grab_row.addWidget(self.left_header_spacer)

        grab_row.addStretch(1)

        self.grab_visual = QWidget()
        self.grab_visual.setObjectName("grabVisual")
        self.grab_visual.setFixedSize(54, 6)
        self.grab_visual.setProperty("hovered", False)
        self.grab_visual.setProperty("pressed", False)
        self.grab_visual.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        grab_row.addWidget(self.grab_visual, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.grab_animation = QPropertyAnimation(self.grab_visual, b"minimumWidth", self)
        self.grab_animation.setDuration(120)
        self.grab_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        grab_row.addStretch(1)

        self.close_button = CloseCircleButton()
        self.close_button.clicked.connect(QApplication.instance().quit)
        grab_row.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        root.addWidget(self.grab_area)

        # ---------------------------------------------------------------------
        # Album art
        # ---------------------------------------------------------------------
        self.album_art_label = QLabel()
        self.album_art_label.setFixedSize(album_size, album_size)
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_label.setStyleSheet(
            "background-color: rgba(255, 255, 255, 10); border-radius: 8px;"
        )
        root.addWidget(self.album_art_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ---------------------------------------------------------------------
        # Song / artist labels
        # ---------------------------------------------------------------------
        self.song_title_label = ElidedLabel("Spotify Widget")
        self.song_title_label.setFixedHeight(32)
        self.song_title_label.setMinimumWidth(widget_width - 56)
        self.song_title_label.setStyleSheet(
            """
            font-size: 15px;
            font-weight: 700;
            color: white;
            background-color: rgba(0, 0, 0, 115);
            border-radius: 7px;
            padding: 2px 9px;
            """
        )
        root.addWidget(self.song_title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.artist_label = ElidedLabel("Starting...")
        self.artist_label.setFixedHeight(28)
        self.artist_label.setMinimumWidth(widget_width - 56)
        self.artist_label.setStyleSheet(
            """
            font-size: 12px;
            color: rgba(255, 255, 255, 230);
            background-color: rgba(0, 0, 0, 100);
            border-radius: 6px;
            padding: 2px 9px;
            """
        )
        root.addWidget(self.artist_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ---------------------------------------------------------------------
        # Transport buttons
        # ---------------------------------------------------------------------
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(4, 6, 4, 0)
        button_layout.setSpacing(8)

        self.prev_button = self.make_button("skip-backward.svg", fallback_text="⏮")
        self.play_icon = self.load_svg_icon("play.svg")
        self.pause_icon = self.make_pause_icon()
        self.play_button = self.make_button(icon=self.play_icon, fallback_text="▶")
        self.next_button = self.make_button("skip-forward.svg", fallback_text="⏭")

        self.prev_button.clicked.connect(self.previous_song)
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button.clicked.connect(self.next_song)

        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.next_button)

        root.addLayout(button_layout)

        # ---------------------------------------------------------------------
        # Drag timer
        # ---------------------------------------------------------------------
        self.drag_timer = QTimer(self)
        self.drag_timer.setInterval(8)
        self.drag_timer.timeout.connect(self.drag_tick)

        # ---------------------------------------------------------------------
        # Refresh / signals
        # ---------------------------------------------------------------------
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.request_update_song_info)

        self.refresh_requested.connect(self.request_update_song_info)
        self.error_requested.connect(self.show_error)
        self.track_loaded.connect(self.apply_track_state)

        self.set_play_icon(False)

        QTimer.singleShot(750, self.request_update_song_info)
        QTimer.singleShot(1500, lambda: self.timer.start(5000))

    # -------------------------------------------------------------------------
    # Icon helpers
    # -------------------------------------------------------------------------
    def load_svg_icon(self, filename, size=button_icon_size):
        svg_path = BASE_DIR / filename
        if not svg_path.exists():
            return QIcon()

        try:
            svg_text = svg_path.read_text(encoding="utf-8")

            renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
            if not renderer.isValid():
                return QIcon()

            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()

            return QIcon(pixmap)

        except Exception:
            return QIcon()

    def make_pause_icon(self, size=button_icon_size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor("black"))
        painter.setPen(Qt.PenStyle.NoPen)

        bar_width = max(3, size // 5)
        gap = max(3, size // 6)
        total_width = bar_width * 2 + gap
        x0 = (size - total_width) // 2
        y0 = max(2, size // 8)
        h = size - 2 * y0

        painter.drawRoundedRect(x0, y0, bar_width, h, 1.5, 1.5)
        painter.drawRoundedRect(x0 + bar_width + gap, y0, bar_width, h, 1.5, 1.5)
        painter.end()

        return QIcon(pixmap)

    def make_button(self, icon=None, fallback_text=""):
        button = QPushButton()
        button.setFixedHeight(button_height)
        button.setMinimumWidth(44)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        loaded_icon = QIcon()
        if isinstance(icon, str):
            loaded_icon = self.load_svg_icon(icon)
        elif isinstance(icon, QIcon):
            loaded_icon = icon

        if loaded_icon.isNull():
            button.setText(fallback_text)
        else:
            button.setText("")
            button.setIcon(loaded_icon)
            button.setIconSize(QSize(button_icon_size, button_icon_size))

        return button

    def set_play_icon(self, is_playing):
        self.is_playing = is_playing
        icon = self.pause_icon if is_playing else self.play_icon
        fallback_text = "⏸" if is_playing else "▶"

        if icon.isNull():
            self.play_button.setIcon(QIcon())
            self.play_button.setText(fallback_text)
        else:
            self.play_button.setText("")
            self.play_button.setIcon(icon)
            self.play_button.setIconSize(QSize(button_icon_size, button_icon_size))

    # -------------------------------------------------------------------------
    # UI state
    # -------------------------------------------------------------------------
    def show_error(self, title, message):
        self.auth_failed = True
        self.loading = False
        self.timer.stop()
        self.album_art_label.clear()
        self.song_title_label.setText(title)
        self.artist_label.setText(message)
        print(title)
        print(message)

    def show_soft_error(self, title, message):
        # Temporary network/API errors should not brick the widget or clear the
        # current album art. Keep the last good state and just log the problem.
        self.loading = False
        print(title)
        print(message)

        if not self.song_title_label.full_text or self.song_title_label.full_text in (
            "Spotify Widget",
            "Starting...",
            "Nothing playing",
        ):
            self.song_title_label.setText(title)
            self.artist_label.setText(message[:80])

    def set_hint(self, title, subtitle=""):
        self.song_title_label.setText(title)
        self.artist_label.setText(subtitle)

    # -------------------------------------------------------------------------
    # Grab handle visual state
    # -------------------------------------------------------------------------
    def set_grab_state(self, hovered=False, pressed=False):
        self.grab_visual.setProperty("hovered", bool(hovered))
        self.grab_visual.setProperty("pressed", bool(pressed))
        self.grab_visual.style().unpolish(self.grab_visual)
        self.grab_visual.style().polish(self.grab_visual)
        self.grab_visual.update()

        target_width = 78 if pressed else 68 if hovered else 54
        current_width = self.grab_visual.minimumWidth()

        self.grab_animation.stop()
        self.grab_animation.setStartValue(current_width)
        self.grab_animation.setEndValue(target_width)
        self.grab_visual.setMaximumWidth(target_width)
        self.grab_animation.start()

    # -------------------------------------------------------------------------
    # Dragging
    # -------------------------------------------------------------------------
    def begin_drag(self, global_pos):
        self.dragging = True
        self.drag_offset = global_pos - self.frameGeometry().topLeft()
        if not self.drag_timer.isActive():
            self.drag_timer.start()

    def continue_drag(self, global_pos):
        if self.dragging:
            self.move(global_pos - self.drag_offset)

    def drag_tick(self):
        if not self.dragging:
            self.drag_timer.stop()
            return

        if not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self.end_drag()
            return

        self.move(QCursor.pos() - self.drag_offset)

    def end_drag(self):
        if self.dragging:
            self.dragging = False
            self.drag_timer.stop()
            self.snap_to_grid()

    def eventFilter(self, source, event):
        if source is self.grab_area:
            if event.type() == QEvent.Type.Enter:
                self.set_grab_state(hovered=True, pressed=False)
                return False

            if event.type() == QEvent.Type.Leave:
                if not self.dragging:
                    self.set_grab_state(hovered=False, pressed=False)
                return False

            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.set_grab_state(hovered=True, pressed=True)
                    self.begin_drag(event.globalPosition().toPoint())
                    event.accept()
                    return True

            if event.type() == QEvent.Type.MouseMove:
                if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
                    self.continue_drag(event.globalPosition().toPoint())
                    event.accept()
                    return True

            if event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.end_drag()
                    self.set_grab_state(hovered=self.grab_area.underMouse(), pressed=False)
                    event.accept()
                    return True

        return super().eventFilter(source, event)

    def snap_to_grid(self):
        x = round(self.x() / icon_width) * icon_width
        y = round(self.y() / icon_height) * icon_height
        self.move(x, y)

    # -------------------------------------------------------------------------
    # Async helpers
    # -------------------------------------------------------------------------
    def run_background(self, task, refresh_after=True, fatal_errors=True):
        def worker():
            try:
                task()
            except Exception as exc:
                print("Spotify command error")
                print(str(exc))

                if fatal_errors:
                    self.error_requested.emit("Spotify error", str(exc))
                elif refresh_after:
                    self.refresh_requested.emit()
                return

            if refresh_after:
                self.refresh_requested.emit()

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Spotify
    # -------------------------------------------------------------------------
    def request_update_song_info(self):
        if self.auth_failed or self.loading:
            return

        self.loading = True

        def worker():
            try:
                current_track = sp.current_playback()
                image_bytes = None

                if current_track and current_track.get("item"):
                    track = current_track["item"]
                    images = track.get("album", {}).get("images", [])
                    album_art_url = images[0].get("url") if images else None

                    if album_art_url:
                        try:
                            response = requests.get(
                                album_art_url,
                                proxies={"http": PX_PROXY_URL, "https": PX_PROXY_URL}
                                if USE_PX_PROXY
                                else None,
                                timeout=5,
                            )
                            response.raise_for_status()
                            image_bytes = response.content
                        except Exception as image_exc:
                            # Album art failure should not count as playback failure.
                            print("Album art fetch error")
                            print(str(image_exc))
                            image_bytes = None

                self.track_loaded.emit(current_track, image_bytes, None)

            except Exception as exc:
                self.track_loaded.emit(None, None, exc)

        threading.Thread(target=worker, daemon=True).start()

    def apply_track_state(self, current_track, image_bytes, error):
        self.loading = False

        if error is not None:
            message = str(error)
            lower_message = message.lower()

            auth_like_error = (
                "invalid_grant" in lower_message
                or "invalid client" in lower_message
                or "unauthorized" in lower_message
                or "forbidden" in lower_message and "restriction" not in lower_message
            )

            if auth_like_error:
                self.show_error("Spotify auth error", message)
            else:
                self.show_soft_error("Spotify connection issue", message)

            return

        if not current_track or not current_track.get("item"):
            self.song_title_label.setText("Nothing playing")
            self.current_artist_text = "Start Spotify on your phone"
            self.artist_label.setText(self.current_artist_text)
            self.set_play_icon(False)
            self.album_art_label.clear()
            self.active_device_id = None
            return

        track = current_track["item"]
        self.song_title_label.setText(track.get("name", "Unknown track"))

        self.current_artist_text = ", ".join(
            artist.get("name", "Unknown artist")
            for artist in track.get("artists", [])
        )
        self.artist_label.setText(self.current_artist_text)

        self.set_play_icon(bool(current_track.get("is_playing")))

        device = current_track.get("device") or {}
        self.active_device_id = device.get("id")

        if not image_bytes:
            self.album_art_label.clear()
            return

        pixmap = QPixmap()
        pixmap.loadFromData(BytesIO(image_bytes).read())
        self.album_art_label.setPixmap(
            pixmap.scaled(
                album_size,
                album_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def toggle_playback(self):
        if self.auth_failed:
            return

        requested_play_state = not self.is_playing
        self.set_play_icon(requested_play_state)

        def task():
            playback = sp.current_playback()
            actual_is_playing = bool((playback or {}).get("is_playing"))
            device = (playback or {}).get("device") or {}
            device_id = device.get("id") or self.active_device_id

            # Use the actual Spotify state, not only the optimistic UI state.
            # This avoids sending pause again when the UI says play but Spotify
            # still reports the phone as playing for a moment.
            if actual_is_playing:
                try:
                    sp.pause_playback()
                except Exception as first_exc:
                    # Some devices behave differently with/without device_id.
                    # Try the explicit device once, then let the caller log it.
                    if device_id:
                        print("Pause without device_id failed, trying active device_id")
                        print(str(first_exc))
                        sp.pause_playback(device_id=device_id)
                    else:
                        raise
            else:
                if device_id:
                    sp.start_playback(device_id=device_id)
                else:
                    sp.start_playback()

        self.run_background(task, refresh_after=True, fatal_errors=False)

    def next_song(self):
        if self.auth_failed:
            return

        self.set_hint("Skipping...", "Next track")
        if self.active_device_id:
            self.run_background(lambda: sp.next_track(device_id=self.active_device_id), refresh_after=True, fatal_errors=False)
        else:
            self.run_background(lambda: sp.next_track(), refresh_after=True, fatal_errors=False)

    def previous_song(self):
        if self.auth_failed:
            return

        self.set_hint("Skipping...", "Previous track")
        if self.active_device_id:
            self.run_background(lambda: sp.previous_track(device_id=self.active_device_id), refresh_after=True, fatal_errors=False)
        else:
            self.run_background(lambda: sp.previous_track(), refresh_after=True, fatal_errors=False)

    # -------------------------------------------------------------------------
    # Key handling
    # -------------------------------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            QApplication.instance().quit()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Q and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            QApplication.instance().quit()
            event.accept()
            return

        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = SpotifyWidget()
    widget.move(300, 300)
    widget.show()
    sys.exit(app.exec())
