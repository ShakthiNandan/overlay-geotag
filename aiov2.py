import sys, io, json, requests, threading
from flask import Flask, request, jsonify
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSystemTrayIcon, QMenu, QAction, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPixmap, QPainterPath, QPainter, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from geopy.geocoders import Nominatim
from datetime import datetime
from PIL import Image
from PIL.ImageQt import toqpixmap

# --------------------- Flask Server (GPS Logger) --------------------- #
app = Flask(__name__)
latest = {"lat": None, "lon": None, "time": None, "speed": None}

@app.route('/log', methods=['GET', 'POST'])
def log_location():
    data = request.args.to_dict()
    if request.method == 'POST':
        json_body = request.get_json(silent=True) or {}
        data.update({k: v for k, v in json_body.items() if k in ['lat', 'lon', 'longitude', 'time', 's', 'speed']})
    
    lat = data.get('lat')
    lon = data.get('longitude') or data.get('lon')
    if not lat or not lon:
        return jsonify({"error": "missing lat/lon", "received": data}), 400

    latest.update({
        "lat": float(lat),
        "lon": float(lon),
        "time": data.get('time'),
        "speed": data.get('s') or data.get('speed')
    })
    return jsonify({"status": "logged"}), 200

@app.route('/location', methods=['GET'])
def get_location():
    return jsonify(latest) if latest["lat"] else (jsonify({"error": "no data"}), 404)

def run_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True)

# --------------------- PyQt Overlay --------------------- #
def get_static_map(lat, lon):
    url = f"https://static-maps.yandex.ru/1.x/?ll={lon},{lat}&z=14&size=200,200&l=sat,skl&pt={lon},{lat},pm2rdm"
    try:
        r = requests.get(url, timeout=4)
        return Image.open(io.BytesIO(r.content)) if r.status_code == 200 else None
    except:
        return None

class MapFetcher(QThread):
    image_fetched = pyqtSignal(QPixmap)
    def __init__(self, lat, lon):
        super().__init__()
        self.lat, self.lon = lat, lon
    def run(self):
        img = get_static_map(self.lat, self.lon)
        if img:
            pix = toqpixmap(img.convert("RGBA")).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_fetched.emit(pix)

class GeoOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(500, 200)
        self.lat = self.lon = 0.0
        self.cached_coords = (None, None)
        self.address = ["Waiting...", "", ""]
        self.geocoder = Nominatim(user_agent="geo_overlay")
        self.initUI()
        self.setupTray()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_location)
        self.timer.start(10000)
        self.fetch_location()

    def initUI(self):
        self.bg = QWidget(self)
        self.bg.setStyleSheet("background: white; border-radius: 30px;")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.bg.setGraphicsEffect(shadow)
        layout = QHBoxLayout(self.bg)
        layout.setContentsMargins(20, 20, 20, 20)

        self.map_label = QLabel(); self.map_label.setFixedSize(160, 160)
        layout.addWidget(self.map_label)

        self.info_layout = QVBoxLayout()
        self.info_labels = [QLabel() for _ in range(3)]
        for lbl in self.info_labels:
            lbl.setFont(QFont("Segoe UI", 10)); lbl.setStyleSheet("color: #333;")
            self.info_layout.addWidget(lbl)
        layout.addLayout(self.info_layout)

        self.btn_layout = QVBoxLayout()
        self.toggle_btn = QPushButton("❌"); self.edit_btn = QPushButton("✏️")
        for btn in (self.toggle_btn, self.edit_btn):
            btn.setFixedSize(40, 40); btn.setStyleSheet("font-size: 18px;")
        self.toggle_btn.clicked.connect(self.hide)
        self.edit_btn.clicked.connect(self.toggle_edit)
        self.btn_layout.addWidget(self.toggle_btn)
        self.btn_layout.addWidget(self.edit_btn)
        layout.addLayout(self.btn_layout)

    def resizeEvent(self, _): self.bg.setGeometry(0, 0, self.width(), self.height())

    def setupTray(self):
        self.tray = QSystemTrayIcon(QIcon(), self)
        self.tray.setIcon(QIcon("icon.png"))
        self.tray.setVisible(True)
        menu = QMenu()
        menu.addAction("Show Overlay", self.show)
        menu.addAction("Exit", QApplication.quit)
        self.tray.setContextMenu(menu)

    def toggle_edit(self):
        flags = self.windowFlags()
        self.setWindowFlags(Qt.Window if self.windowFlags() & Qt.FramelessWindowHint else Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.show()

    def fetch_location(self):
        try:
            r = requests.get("http://localhost:5000/location", timeout=3)
            if r.status_code == 200:
                data = r.json()
                lat, lon = float(data["lat"]), float(data["lon"])
                if (lat, lon) != (self.lat, self.lon):
                    self.lat, self.lon = lat, lon
                    self.update_overlay()
        except Exception as e:
            print("Fetch error:", e)

    def update_overlay(self):
        if (self.lat, self.lon) != self.cached_coords:
            try:
                loc = self.geocoder.reverse((self.lat, self.lon), timeout=5)
                self.address = loc.address.split(",")[:3] if loc else ["Unknown", "", ""]
                self.cached_coords = (self.lat, self.lon)
            except:
                self.address = ["Unknown", "", ""]

        now = datetime.now()
        self.info_labels[0].setText(f"<b>{self.address[0]}</b><br>{self.address[1]}<br>{self.address[2]}")
        self.info_labels[1].setText(f"<b>Lat</b> {self.lat:.6f} &nbsp;&nbsp; <b>Lon</b> {self.lon:.6f}")
        self.info_labels[2].setText(f"<b>Date</b> {now.strftime('%d %b %Y')} &nbsp;&nbsp; <b>Time</b> {now.strftime('%I:%M %p')}")

        self.fetcher = MapFetcher(self.lat, self.lon)
        self.fetcher.image_fetched.connect(self.set_map)
        self.fetcher.start()

    def set_map(self, pixmap):
        masked = QPixmap(160, 160); masked.fill(Qt.transparent)
        painter = QPainter(masked)
        path = QPainterPath(); path.addEllipse(0, 0, 160, 160)
        painter.setClipPath(path); painter.drawPixmap(0, 0, pixmap); painter.end()
        self.map_label.setPixmap(masked)

# --------------------- Main --------------------- #
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    app_qt = QApplication(sys.argv)
    geo_overlay = GeoOverlay()
    geo_overlay.show()
    sys.exit(app_qt.exec_())
