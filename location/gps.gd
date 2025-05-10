extends Node

var http_server := HTTPServer.new()
var port := 5050

func _ready():
	var err = http_server.listen(port)
	if err != OK:
		push_error("❌ HTTP server failed to start on port %d" % port)
	else:
		print("✅ HTTP server listening on port %d" % port)

func _process(_delta):
	http_server.poll()
	while http_server.is_request_pending():
		var rid = http_server.get_request_id()
		var method = http_server.get_http_method(rid)
		var path = http_server.get_request_path(rid)

		if method == HTTPServer.METHOD_POST and path == "/location":
			# Read the raw body bytes and convert to string
			var body_bytes = http_server.read_request_body(rid)
			var body_str = body_bytes.get_string_from_utf8()
			var parsed = JSON.parse(body_str)
			if parsed.error == OK and parsed.result is Dictionary:
				var data = parsed.result
				# Now you have your sent data:
				var lat = float(data.get("lat", 0.0))
				var lon = float(data.get("lon", 0.0))
				print("📥 Received POST /location → lat:", lat, "lon:", lon)
				# (You can now broadcast it, store it, update UI, etc.)
				var resp = {"status":"ok"}
				var resp_bytes = to_utf8_buffer(JSON.stringify(resp))
				http_server.respond(rid, 200, resp_bytes, {"Content-Type":"application/json"})
			else:
				var err_bytes = to_utf8_buffer('{"error":"invalid json"}')
				http_server.respond(rid, 400, err_bytes, {"Content-Type":"application/json"})
		else:
			var nf = to_utf8_buffer('{"error":"not found"}')
			http_server.respond(rid, 404, nf, {"Content-Type":"application/json"})
