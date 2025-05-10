from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

latest_location = {"lat": 0.0, "lon": 0.0}

@app.route('/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    if data and 'lat' in data and 'lon' in data:
        latest_location['lat'] = data['lat']
        latest_location['lon'] = data['lon']
        return jsonify({"status": "received"}), 200
    return jsonify({"error": "invalid"}), 400

@app.route('/location', methods=['GET'])
def send_location():
    return jsonify(latest_location)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
