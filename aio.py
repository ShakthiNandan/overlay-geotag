import sys, io, json, requests, threading
from flask import Flask, request, jsonify
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSystemTrayIcon, QMenu, QAction, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPixmap, QPainterPath, QPainter, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal
from geopy.geocoders import Nominatim
from PIL import Image
from PIL.ImageQt import toqpixmap

# --------------------- FLASK SERVER ---------------------

app = Flask(__name__)
latest = {
    "lat": None,
    "lon": None,
    "time": None,
    "speed": None
}

@app.route('/log', methods=['GET', 'POST'])
def log_location():
    lat   = request.args.get('lat')
    lon   = request.args.get('longitude')
    t     = request.args.get('time')
    speed = request.args.get('s')

    if request.method == 'POST':
        json_body = request.get_json(silent=True) or {}
        lat   = lat   or json_body.get('lat')
        lon   = lon   or json_body.get('longitude') or json_body.get('lon')
        t     = t     or json_body.get('time')
        speed = speed or json_body.get('s') or json_body.get('speed')

    if not lat or not lon:
        return jsonify({"error": "missing lat or longitude"}), 400

    latest.update({
        "lat": float(lat),
        "lon": float(lon),
        "time": t,
        "speed": speed
    })
    print(f"📥 Logged → {latest}")
    return jsonify({"status": "logged"}), 200

@app.route('/location', methods=['GET'])
def get_location():
    if latest["lat"] is None:
        return jsonify({"error": "no data yet"}), 404
    return jsonify(latest), 200

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

# --------------------- PYQT5 OVERLAY ---------------------

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

class MapFetcher(QThread):
    image_fetched = pyqtSignal(QPixmap)
    def __init__(self, lat, lon):
        super().__init__()
        self.lat = lat
        self.lon = lon

    def run(self):
        img = get_static_map(self.lat, self.lon)
        if img:
            map_qt = toqpixmap(img.convert("RGBA")).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_fetched.emit(map_qt)

class GeoOverlayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(600, 200)
        self.is_edit_mode = False
        self.lat, self.lon = 0.0, 0.0
        self.address_parts = ["Waiting...", "", ""]
        self.map_label = QLabel()
        self.info_labels = []
        self.cached_address = (None, None)
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
        self.timer.start(10000)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(QIcon(), self)
        self.tray.setIcon(QIcon("icon.png"))
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
        self.setWindowFlags(Qt.Window if self.is_edit_mode else Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.show()

    def fetch_location(self):
        try:
            r = requests.get("http://localhost:5000/location", timeout=3)
            if r.status_code == 200:
                data = r.json()
                new_lat, new_lon = float(data['lat']), float(data['lon'])
                if (new_lat, new_lon) != (self.lat, self.lon):
                    self.lat, self.lon = new_lat, new_lon
                    self.update_overlay()
        except Exception as e:
            print("Error getting location:", e)

    def update_overlay(self):
        if (self.lat, self.lon) != self.cached_address:
            try:
                location = Nominatim(user_agent="geo_overlay").reverse((self.lat, self.lon), timeout=5)
                self.address_parts = location.address.split(",") if location else ["Unknown", "", ""]
                self.cached_address = (self.lat, self.lon)
            except:
                self.address_parts = ["Unknown", "", ""]

        now = datetime.now()
        self.map_fetcher = MapFetcher(self.lat, self.lon)
        self.map_fetcher.image_fetched.connect(self.set_map)
        self.map_fetcher.start()

        self.info_labels[0].setText(f"<b>{self.address_parts[0]}</b><br>{self.address_parts[1]}<br>{self.address_parts[2]}")
        self.info_labels[1].setText(f"<b>Lat</b> {self.lat:.6f} &nbsp;&nbsp; <b>Long</b> {self.lon:.6f}")
        self.info_labels[2].setText(f"<b>Date</b> {now.strftime('%d %b %Y')} &nbsp;&nbsp; <b>Time</b> {now.strftime('%I:%M %p')}")

    def set_map(self, map_qt):
        masked = QPixmap(160, 160)
        masked.fill(Qt.transparent)
        painter = QPainter(masked)
        path = QPainterPath()
        path.addEllipse(0, 0, 160, 160)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, map_qt)
        painter.end()
        self.map_label.setPixmap(masked)

# --------------------- MAIN ENTRY ---------------------

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    app = QApplication(sys.argv)
    overlay = GeoOverlayWidget()
    overlay.show()
    sys.exit(app.exec_())
