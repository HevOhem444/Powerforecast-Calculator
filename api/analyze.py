import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

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

        api_key = (
            os.environ.get('GEMINI_API_KEY', '') or
            os.environ.get('GOOGLE_API_KEY', '') or
            os.environ.get('GOOGLE_GEMINI_API_KEY', '')
        ).strip()

        if not api_key:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Missing Gemini API Key",
                "message": "No GEMINI_API_KEY (or GOOGLE_API_KEY) configured in Vercel Environment Variables."
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
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        try:
            req = urllib.request.Request(gemini_url, data=req_payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as resp:
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
                    "timestamp": "now"
                }).encode('utf-8'))
        except urllib.error.HTTPError as e:
            err_text = e.read().decode('utf-8')
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Gemini API Error", "message": err_text}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Server Error", "message": str(e)}).encode('utf-8'))
