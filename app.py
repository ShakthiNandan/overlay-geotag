import sys, io, json, requests
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSystemTrayIcon, QMenu, QAction, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPixmap, QPainterPath, QPainter, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer, QSize

from geopy.geocoders import Nominatim
from PIL import Image
from PIL import ImageQt


# --- CONFIG ---
NGROK_ENDPOINT = "http://localhost:5000/location"  # Change to your ngrok URL
UPDATE_INTERVAL_MS = 6000  # check every 3 sec


def get_static_map(lat, lon, zoom=14, size="200,200"):
    url = f"https://static-maps.yandex.ru/1.x/?ll={lon},{lat}&z={zoom}&size={size}&l=sat,skl&pt={lon},{lat},pm2rdm"
    response = requests.get(url)
    if response.status_code != 200:
        print("Map fetch error", response.status_code)
        return None
    try:
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        print("Image error:", e)
        return None


class GeoOverlayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(400, 180)
        self.is_edit_mode = False

        self.lat, self.lon = 0.0, 0.0
        self.address_parts = ["Waiting...", "", ""]
        self.map_label = QLabel()
        self.info_labels = []

        self.initUI()
        self.setup_tray()
        self.fetch_location()
        self.setup_timer()

    def initUI(self):
        self.bg = QWidget(self)
        self.bg.setStyleSheet("background-color: white; border-radius: 30px;")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.bg.setGraphicsEffect(shadow)

        self.layout = QHBoxLayout(self.bg)
        self.layout.setContentsMargins(20, 20, 20, 20)

        self.map_label.setFixedSize(160, 160)
        self.layout.addWidget(self.map_label)

        self.info_layout = QVBoxLayout()
        self.layout.addLayout(self.info_layout)

        for _ in range(3):
            lbl = QLabel("Loading...")
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet("color: #333;")
            lbl.setTextFormat(Qt.RichText)
            self.info_labels.append(lbl)
            self.info_layout.addWidget(lbl)

        # Buttons
        self.toggle_btn = QPushButton("Toggle", self)
        self.edit_btn = QPushButton("Edit", self)
        self.toggle_btn.setGeometry(20, 160, 60, 25)
        self.edit_btn.setGeometry(90, 160, 60, 25)
        self.toggle_btn.clicked.connect(self.hide_to_tray)
        self.edit_btn.clicked.connect(self.toggle_edit)

    def resizeEvent(self, event):
        self.bg.setGeometry(0, 0, self.width(), self.height())

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_location)
        self.timer.start(UPDATE_INTERVAL_MS)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(QIcon(), self)
        self.tray.setIcon(QIcon())  # Set your own icon here
        self.tray.setVisible(True)

        menu = QMenu()
        restore_action = QAction("Show Overlay", self)
        restore_action.triggered.connect(self.show_from_tray)
        menu.addAction(restore_action)

        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

    def hide_to_tray(self):
        self.hide()

    def show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_edit(self):
        self.is_edit_mode = not self.is_edit_mode
        if self.is_edit_mode:
            self.setWindowFlags(Qt.Window)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.show()

    def fetch_location(self):
        try:
            r = requests.get(NGROK_ENDPOINT, timeout=3)
            if r.status_code == 200:
                data = r.json()
                self.lat, self.lon = float(data['lat']), float(data['lon'])
                self.update_overlay()
        except Exception as e:
            print("Error getting location:", e)

    def update_overlay(self):
        # Geocode
        try:
            location = Nominatim(user_agent="geo_overlay").reverse((self.lat, self.lon), timeout=5)
            self.address_parts = location.address.split(",") if location else ["Unknown", "", ""]
        except:
            self.address_parts = ["Unknown", "", ""]

        # Date/Time
        date_now = datetime.now().strftime("%d %b %Y")
        time_now = datetime.now().strftime("%I:%M %p")

        # Map
        img = get_static_map(self.lat, self.lon)
        if img:
            map_qt = ImageQt.toqpixmap(img.convert("RGBA")).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            masked = QPixmap(160, 160)
            masked.fill(Qt.transparent)
            painter = QPainter(masked)
            path = QPainterPath()
            path.addEllipse(0, 0, 160, 160)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, map_qt)
            painter.end()
            self.map_label.setPixmap(masked)

        # Info
        self.info_labels[0].setText(f"<b>{self.address_parts[0]}</b><br>{self.address_parts[1]}<br>{self.address_parts[2]}")
        self.info_labels[1].setText(f"<b>Lat</b> {self.lat:.6f} &nbsp;&nbsp; <b>Long</b> {self.lon:.6f}")
        self.info_labels[2].setText(f"<b>Date</b> {date_now} &nbsp;&nbsp; <b>Time</b> {time_now}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = GeoOverlayWidget()
    overlay.show()
    sys.exit(app.exec_())
