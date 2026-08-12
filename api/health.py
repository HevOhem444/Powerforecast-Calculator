import json
import os
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        res = {
            "status": "ok",
            "serverHasKey": bool(api_key),
            "maxImagesSupported": 3,
            "defaultModel": "gemini-3.6-flash",
            "supportedModels": ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-pro-preview", "gemini-flash-latest"]
        }
        self.wfile.write(json.dumps(res).encode('utf-8'))
