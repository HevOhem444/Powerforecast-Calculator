import json
import os
import re
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

def get_gemini_api_keys():
    """
    Collects all configured Gemini API keys from environment variables.
    Supports GEMINI_API_KEY, GEMINI_API_KEY_1..10, GEMINI_API_KEY_FALLBACK,
    GEMINI_API_KEYS (comma-separated), GOOGLE_API_KEY, and GOOGLE_GEMINI_API_KEY.
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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        images = payload.get('images', [])
        image_base64 = payload.get('imageBase64')
        mime_type = payload.get('mimeType', 'image/jpeg')
        prompt = payload.get('prompt')
        preset = payload.get('preset', 'specs')
        model = payload.get('model', 'gemini-3.7-flash')

        api_keys = get_gemini_api_keys()

        if not api_keys:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Missing Gemini API Key",
                "message": "No GEMINI_API_KEY (or fallback keys) configured in Vercel Environment Variables."
            }).encode('utf-8'))
            return

        image_list = []
        if isinstance(images, list) and len(images) > 0:
            image_list = images[:3]
        elif image_base64:
            image_list = [{"imageBase64": image_base64, "mimeType": mime_type}]

        if not image_list:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Missing Appliance Images",
                "message": "No image data received. Please upload at least 1 appliance photo."
            }).encode('utf-8'))
            return

        parts = []
        for img in image_list:
            b64_data = img.get('imageBase64') or img.get('data') or ''
            clean_b64 = b64_data.split(',')[-1] if ',' in b64_data else b64_data
            parts.append({
                "inline_data": {
                    "mime_type": img.get('mimeType', 'image/jpeg'),
                    "data": clean_b64
                }
            })

        system_prompt = "You are ApplianceSpec AI, an expert mechanical, electrical, and appliance engineering AI. Identify appliances from photo(s) and provide technical specs (Brand, Model, Wattage, Voltage, Daily Hours, Maintenance)."
        parts.append({"text": f"{system_prompt}\nPrompt: {prompt or preset}"})

        req_payload = json.dumps({"contents": [{"parts": parts}]}).encode('utf-8')

        last_error_msg = "Unknown error occurred."
        last_error_code = 500

        for idx, key in enumerate(api_keys):
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                req = urllib.request.Request(
                    gemini_url,
                    data=req_payload,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    text_res = resp_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": True,
                        "modelUsed": model,
                        "imageCount": len(image_list),
                        "preset": preset,
                        "analysis": text_res,
                        "keyUsedIndex": idx + 1,
                        "totalKeysConfigured": len(api_keys),
                        "timestamp": "now"
                    }).encode('utf-8'))
                    return

            except urllib.error.HTTPError as e:
                err_text = e.read().decode('utf-8')
                last_error_code = e.code
                last_error_msg = f"HTTP {e.code}: {err_text}"
                print(f"[Gemini API] Key #{idx + 1} failed ({last_error_msg}). Trying fallback...")
            except Exception as e:
                last_error_code = 500
                last_error_msg = str(e)
                print(f"[Gemini API] Key #{idx + 1} network error ({last_error_msg}). Trying fallback...")

        # If all keys failed:
        self.send_response(last_error_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "error": "Gemini API Error",
            "message": f"All {len(api_keys)} Gemini API key(s) failed. Last error: {last_error_msg}",
            "keysAttempted": len(api_keys)
        }).encode('utf-8'))

