import os
import sys
import json
import logging
from urllib.parse import parse_qs, urlparse
from http.server import SimpleHTTPRequestHandler, HTTPServer

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import meralco_parser
from api.calculate import perform_calculation
import api.pelp as pelp_engine

PORT = 8000

class PowerForecastServerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_DIR, **kwargs)

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/':
            self.path = '/index.html'

        if path in ['/api/health', '/api/health.py']:
            self.handle_api_health()
        elif path in ['/api/rates', '/api/rates.py']:
            self.handle_api_rates()
        elif path in ['/api/appliances', '/api/appliances.py']:
            self.handle_api_appliances()
        elif path.startswith('/api/pelp'):
            self.handle_api_pelp(parsed)
        elif path in ['/api/calculate', '/api/calculate.py']:
            params = parse_qs(parsed.query)
            kwh = float(params.get('kwh', [0])[0])
            gen_rate = float(params.get('gen_rate', [9.2504])[0])
            other = float(params.get('other', [0])[0])
            self.handle_api_calculate(kwh, gen_rate, other)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ['/api/calculate', '/api/calculate.py']:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(body)
            except Exception:
                payload = {}

            kwh = float(payload.get('kwh', 0))
            gen_rate = float(payload.get('generation_rate', payload.get('gen_rate', 9.2504)))
            other = float(payload.get('other_charges', payload.get('other', 0)))
            self.handle_api_calculate(kwh, gen_rate, other)
        elif path in ['/api/analyze', '/api/analyze.py']:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            self.handle_api_analyze(body)
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    def handle_api_health(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
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

    def handle_api_analyze(self, raw_body):
        import urllib.request
        import urllib.error

        try:
            payload = json.loads(raw_body) if raw_body else {}
        except Exception:
            payload = {}

        images = payload.get('images', [])
        image_base64 = payload.get('imageBase64')
        mime_type = payload.get('mimeType', 'image/jpeg')
        prompt = payload.get('prompt')
        preset = payload.get('preset', 'specs')
        custom_key = payload.get('customApiKey', '')
        model = payload.get('model', 'gemini-3.6-flash')

        api_key = (custom_key or os.environ.get('GEMINI_API_KEY', '')).strip()
        if not api_key:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Missing Gemini API Key",
                "message": "No API key provided. Please configure GEMINI_API_KEY or enter key in settings."
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
            self._send_cors_headers()
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

        system_prompt = "You are ApplianceSpec AI, an expert mechanical, electrical, and appliance engineering AI. Your goal is to identify appliances from photo(s) and provide technical specs (Brand, Model, Wattage, Voltage, Daily Hours, Maintenance)."
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
                self._send_cors_headers()
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
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Gemini API Error", "message": err_text}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Server Error", "message": str(e)}).encode('utf-8'))

    def handle_api_rates(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()

        rates_path = os.path.join(PROJECT_DIR, 'rates.json')
        if os.path.exists(rates_path):
            with open(rates_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        else:
            rates = meralco_parser.get_meralco_rates()
            self.wfile.write(json.dumps(rates, indent=2).encode('utf-8'))

    def handle_api_appliances(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()

        db_path = os.path.join(PROJECT_DIR, 'appliance_db.json')
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        else:
            self.wfile.write(json.dumps({"appliances": []}).encode('utf-8'))

    def handle_api_pelp(self, parsed_url):
        path = parsed_url.path.rstrip('/')
        params = parse_qs(parsed_url.query)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()

        try:
            if path in ['/api/pelp', '/api/pelp/health']:
                res = pelp_engine.get_pelp_health()
            elif path == '/api/pelp/categories':
                res = {"categories": pelp_engine.get_pelp_categories()}
            elif path in ['/api/pelp/search', '/api/pelp/appliances/search']:
                q = params.get('q', params.get('search_query', [None]))[0]
                brand = params.get('brand', [None])[0]
                model = params.get('model', [None])[0]
                category = params.get('category', [None])[0]
                try:
                    limit = int(params.get('limit', [50])[0])
                except ValueError:
                    limit = 50
                res = pelp_engine.search_pelp_appliances(
                    query_str=q,
                    brand=brand,
                    model=model,
                    category=category,
                    limit=limit
                )
            elif path.startswith('/api/pelp/category/') or path.startswith('/api/pelp/appliances/'):
                parts = path.split('/')
                slug = parts[-1]
                try:
                    limit = int(params.get('limit', [100])[0])
                except ValueError:
                    limit = 100
                res = pelp_engine.get_pelp_category_products(slug, limit=limit)
            else:
                res = pelp_engine.get_pelp_health()

            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            err_res = {"error": "Internal PELP API Error", "message": str(e)}
            self.wfile.write(json.dumps(err_res).encode('utf-8'))

    def handle_api_calculate(self, kwh, gen_rate, other_charges):
        res = perform_calculation(kwh, gen_rate, other_charges)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(res, indent=2).encode('utf-8'))

handler = PowerForecastServerHandler

def main():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    server_address = ('', port)
    httpd = HTTPServer(server_address, PowerForecastServerHandler)
    print(f"PowerForecast Functional Python Web & API Server running on http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    main()
