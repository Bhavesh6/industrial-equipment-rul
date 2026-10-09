"""Static dev server with /api/chat backend endpoint.

Never lets the browser cache static assets, and proxies/serves the in-app
diagnostic & prognostics chatbot powered by Google Gemini, Groq, and offline SCADA guide.

Usage:
    python dashboard/serve.py        # port 8000
    python dashboard/serve.py 8080
"""

import sys
import os
import json
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Load environment variables if .env exists
try:
    from dotenv import load_dotenv
    ROOT_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Ensure backend package can be imported
ROOT_PATH = str(Path(__file__).resolve().parent.parent)
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

try:
    import backend.chatbot as chatbot_backend
except Exception as e:
    chatbot_backend = None
    print(f"Warning: could not import backend.chatbot: {e}")

try:
    from src.models.predict import RULPredictor
    ml_predictor = RULPredictor()
except Exception as e:
    ml_predictor = None
    print(f"Warning: could not load ML predictor: {e}")


class SCADAHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path == "/api/model-info":
            metrics_path = Path(__file__).resolve().parent.parent / "models" / "metrics.json"
            if metrics_path.exists():
                try:
                    with open(metrics_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._send_json(200, {"success": True, "data": data})
                    return
                except Exception as e:
                    self._send_json(500, {"success": False, "error": str(e)})
                    return
            self._send_json(404, {"success": False, "message": "Model metrics not found"})
            return

        super().do_GET()

    def do_POST(self):
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path == "/api/predict":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(raw_body)
            except Exception as e:
                self._send_json(400, {"success": False, "message": f"Malformed JSON request: {e}"})
                return

            telemetry = data.get("telemetry") or data
            if ml_predictor is not None:
                try:
                    res = ml_predictor.predict(telemetry)
                    self._send_json(200, {"success": True, "prediction": res})
                    return
                except Exception as e:
                    self._send_json(500, {"success": False, "error": str(e)})
                    return
            self._send_json(503, {"success": False, "message": "ML predictor not initialized"})
            return

        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path == "/api/chat":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(raw_body)
            except Exception as e:
                self._send_json(400, {"success": False, "message": f"Malformed JSON request: {e}"})
                return

            message = data.get("message") or data.get("query") or ""
            history = data.get("history") or []
            page = data.get("page") or "index.html"
            telemetry = data.get("telemetry")
            role = data.get("role") or "admin"

            if not message.strip():
                self._send_json(400, {"success": False, "message": "No message supplied"})
                return

            if chatbot_backend is not None:
                reply, error = chatbot_backend.ask(
                    message=message,
                    role=role,
                    history=history,
                    page=page,
                    telemetry=telemetry
                )
            else:
                reply, error = None, "Backend chatbot module not available."

            if reply:
                self._send_json(200, {"success": True, "reply": reply})
            else:
                self._send_json(503, {"success": False, "message": error or "Could not generate reply."})
            return

        # Fallback for unrecognized POST
        self.send_response(404)
        self.end_headers()

    def _send_json(self, status_code, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        # Keep console output clean
        if "/api/chat" in str(args):
            print(f"[API] POST /api/chat -> {args[1] if len(args) > 1 else ''}")
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve_dir = Path(__file__).resolve().parent
    handler = partial(SCADAHandler, directory=str(serve_dir))
    with ThreadingHTTPServer(("0.0.0.0", port), handler) as httpd:
        print(f"EquipmentHealth SCADA Server running on http://localhost:{port}")
        print(f"Directory: {serve_dir}")
        print(f"Chatbot API: http://localhost:{port}/api/chat (Gemini/Groq/Offline)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
