from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory storage of last location
latest = {
    "lat": None,
    "lon": None,
    "time": None,
    "speed": None
}

@app.route('/log', methods=['GET', 'POST'])
def log_location():
    # Accept GET with query-string OR POST with query-string
    lat   = request.args.get('lat')
    lon   = request.args.get('longitude')
    t     = request.args.get('time')
    speed = request.args.get('s')

    # If POST with JSON body (optional)
    if request.method == 'POST':
        json_body = request.get_json(silent=True) or {}
        lat   = lat   or json_body.get('lat')
        lon   = lon   or json_body.get('longitude') or json_body.get('lon')
        t     = t     or json_body.get('time')
        speed = speed or json_body.get('s') or json_body.get('speed')

    # Validate
    if not lat or not lon:
        return jsonify({"error": "missing lat or longitude", "received_args": request.args.to_dict()}), 400

    # Store
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
