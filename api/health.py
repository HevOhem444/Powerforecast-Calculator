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

        # Check standard Gemini / Google API key environment variable names
        gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
        google_key = os.environ.get('GOOGLE_API_KEY', '').strip()
        google_gemini_key = os.environ.get('GOOGLE_GEMINI_API_KEY', '').strip()

        api_key = gemini_key or google_key or google_gemini_key
        server_has_key = bool(api_key)

        key_name = 'GEMINI_API_KEY' if gemini_key else ('GOOGLE_API_KEY' if google_key else ('GOOGLE_GEMINI_API_KEY' if google_gemini_key else None))

        res = {
            "status": "ok",
            "serverHasKey": server_has_key,
            "keyNameDetected": key_name,
            "maxImagesSupported": 3,
            "defaultModel": "gemini-3.7-flash",
            "supportedModels": ["gemini-3.7-flash", "gemini-2.5-flash", "gemini-flash-latest"]
        }
        self.wfile.write(json.dumps(res).encode('utf-8'))
