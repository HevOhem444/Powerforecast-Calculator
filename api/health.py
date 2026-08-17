import json
import os
import re
from http.server import BaseHTTPRequestHandler

def get_gemini_api_keys():
    """
    Collects all configured Gemini API keys from environment variables.
    """
    keys = []
    
    def add_key(val):
        if not val or not isinstance(val, str):
            return
        if any(c in val for c in [',', ';', '\n', '\r']):
            for sub in re.split(r'[,;\n\r]+', val):
                add_key(sub)
            return
        clean = val.strip().strip('"').strip("'")
        if clean and clean not in keys:
            keys.append(clean)

    add_key(os.environ.get('GEMINI_API_KEYS', ''))

    # 2. Numbered & standard named fallback keys
    prefixes = [
        'GEMINI_API_KEY',
        'GEMINI_API_KEY_FALLBACK',
        'GEMINI_API_KEY_BACKUP',
        'GEMINI_API_BACKUP_KEY',
        'GOOGLE_API_KEY',
        'GOOGLE_GEMINI_API_KEY'
    ]
    for p in prefixes:
        add_key(os.environ.get(p, ''))
        for i in range(1, 11):
            add_key(os.environ.get(f"{p}_{i}", ''))

    # 3. Dynamic scan of os.environ for any GEMINI / GOOGLE API KEY patterns
    for k, v in os.environ.items():
        if re.match(r'^(GEMINI|GOOGLE)_.*API_?KEY.*$', k, re.IGNORECASE):
            add_key(v)

    return keys

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

        keys = get_gemini_api_keys()
        key_count = len(keys)
        server_has_key = key_count > 0

        detected_sources = []
        if os.environ.get('GEMINI_API_KEY'):
            detected_sources.append('GEMINI_API_KEY')
        for i in range(1, 11):
            if os.environ.get(f'GEMINI_API_KEY_{i}'):
                detected_sources.append(f'GEMINI_API_KEY_{i}')
        if os.environ.get('GEMINI_API_KEY_FALLBACK'):
            detected_sources.append('GEMINI_API_KEY_FALLBACK')
        if os.environ.get('GEMINI_API_KEYS'):
            detected_sources.append('GEMINI_API_KEYS')
        if os.environ.get('GOOGLE_API_KEY'):
            detected_sources.append('GOOGLE_API_KEY')
        if os.environ.get('GOOGLE_GEMINI_API_KEY'):
            detected_sources.append('GOOGLE_GEMINI_API_KEY')

        if key_count > 1:
            primary_name = detected_sources[0] if detected_sources else 'GEMINI_API_KEY'
            key_name = f"{primary_name} (+{key_count - 1} Fallback Keys)"
        elif key_count == 1:
            key_name = detected_sources[0] if detected_sources else 'GEMINI_API_KEY'
        else:
            key_name = None

        res = {
            "status": "ok",
            "serverHasKey": server_has_key,
            "keyCount": key_count,
            "keyNameDetected": key_name,
            "detectedSources": detected_sources,
            "maxImagesSupported": 3,
            "defaultModel": "gemini-3.7-flash",
            "supportedModels": ["gemini-3.7-flash", "gemini-2.5-flash", "gemini-flash-latest"]
        }
        self.wfile.write(json.dumps(res).encode('utf-8'))

