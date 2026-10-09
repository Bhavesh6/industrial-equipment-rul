"""EquipmentHealth SCADA Web Server & Hardware Motor Controller.

Provides static file serving for the SCADA web dashboard, WebSocket/REST telemetry
ingestion directly from ESP32 on COM5, real-time Machine Learning RUL prognostics,
and bi-directional motor speed and actuation control endpoints.

Endpoints:
    GET  /api/telemetry     -> Latest live hardware sensor stream + ML RUL inference
    POST /api/motor/control -> Actuation commands: start, stop, speed, reverse, estop, reset
    GET  /api/status        -> System health, serial bridge status, ML engine state
    GET  /api/model-info    -> Trained model metrics & parameters
    POST /api/predict       -> Ad-hoc ML RUL prediction
    POST /api/chat          -> AI Prognostics Copilot assistant

Usage:
    python dashboard/serve.py        # port 8000
    python dashboard/serve.py 8080
"""

import sys
import os
import json
import time
import threading
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

# Ensure backend package and models can be imported
ROOT_PATH = str(Path(__file__).resolve().parent.parent)
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    print("Warning: pyserial is not installed. Run 'pip install pyserial' for hardware serial bridge.")

try:
    import backend.chatbot as chatbot_backend
except Exception as e:
    chatbot_backend = None
    print(f"Warning: could not import backend.chatbot: {e}")

try:
    from src.models.predict import RULPredictor
    ml_predictor = RULPredictor()
    ml_status = "ML Model Ready" if ml_predictor.is_ml_ready else "Rule-Based Fallback"
    print(f"[ML] Prognostics Engine Loaded (Status: {ml_status})")
except Exception as e:
    ml_predictor = None
    print(f"[ML] Warning: could not load ML predictor: {e}")


def find_esp32_port(preferred="COM5"):
    """Detect the COM port connected to the ESP32."""
    if not HAS_SERIAL:
        return None
    try:
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if p.device.upper() == preferred.upper():
                return p.device
        for p in ports:
            desc = (p.description or "").lower()
            if any(k in desc for k in ["cp210", "ch340", "uart", "usb serial", "silicon labs"]):
                return p.device
        return preferred if ports else None
    except Exception:
        return preferred


class HardwareSerialBridge:
    """Background worker that continuously ingests ESP32 telemetry from COM5

    and provides thread-safe bi-directional motor control commands.
    """

    def __init__(self, port="COM5", baudrate=115200):
        self.preferred_port = port
        self.active_port = None
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        self.running = True
        self.lock = threading.Lock()
        self.latest_telemetry = None
        self.latest_prediction = None
        self.last_packet_time = 0
        self.packets_received = 0
        self.last_command_sent = None

    def start(self):
        t = threading.Thread(target=self._worker_loop, daemon=True, name="HardwareSerialBridge")
        t.start()
        print(f"[SERIAL] Hardware bridge worker thread started (target: {self.preferred_port} @ {self.baudrate} baud)")

    def _worker_loop(self):
        while self.running:
            target_port = find_esp32_port(self.preferred_port)
            if not target_port:
                self.connected = False
                time.sleep(2.0)
                continue

            try:
                self.ser = serial.Serial()
                self.ser.port = target_port
                self.ser.baudrate = self.baudrate
                self.ser.timeout = 0.5
                self.ser.dtr = False
                self.ser.rts = False
                self.ser.open()
                self.ser.reset_input_buffer()
                self.active_port = target_port
                self.connected = True
                print(f"[SERIAL] Connected to ESP32 on {target_port} @ {self.baudrate} baud")

                while self.running and self.ser and self.ser.is_open:
                    raw_line = self.ser.readline()
                    if not raw_line:
                        continue

                    try:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        continue

                    if not line:
                        continue

                    if line.startswith("{") and line.endswith("}"):
                        try:
                            data = json.loads(line)
                            pred = None
                            if ml_predictor is not None:
                                try:
                                    pred = ml_predictor.predict(data)
                                except Exception as err:
                                    pred = {"error": str(err), "rul_hours": 0.0, "status": "ERROR"}

                            with self.lock:
                                self.latest_telemetry = data
                                self.latest_prediction = pred
                                self.last_packet_time = time.time()
                                self.packets_received += 1
                        except Exception:
                            pass
                    elif line.startswith("[") or "ALERT" in line or "CMD" in line:
                        print(f"  [ESP32] {line}")

            except Exception as e:
                self.connected = False
                self.active_port = None
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                    self.ser = None
                time.sleep(2.0)

    def send_command(self, cmd_str):
        """Send an actuation command string (e.g., 'SPEED=180', 'START', 'STOP', 'REVERSE', 'ESTOP') to ESP32."""
        cmd_str = cmd_str.strip()
        if not cmd_str:
            return False, "Empty command string"

        with self.lock:
            if not self.connected or not self.ser or not self.ser.is_open:
                return False, f"Hardware serial port {self.active_port or self.preferred_port} is not connected"

            try:
                msg = (cmd_str + "\n").encode("utf-8")
                self.ser.write(msg)
                self.ser.flush()
                self.last_command_sent = {"cmd": cmd_str, "time": time.time()}
                print(f"[SERIAL] >>> Sent command to ESP32: '{cmd_str}'")
                return True, f"Command '{cmd_str}' sent successfully"
            except Exception as e:
                print(f"[SERIAL] ❌ Error writing command '{cmd_str}': {e}")
                return False, str(e)

    def get_snapshot(self):
        """Retrieve the latest telemetry, ML prediction, and connection status."""
        now = time.time()
        with self.lock:
            is_stale = (now - self.last_packet_time) > 4.0 if self.last_packet_time > 0 else True
            return {
                "connected": self.connected and not is_stale,
                "port": self.active_port or self.preferred_port,
                "last_packet_age_s": round(now - self.last_packet_time, 2) if self.last_packet_time > 0 else None,
                "packets_received": self.packets_received,
                "telemetry": self.latest_telemetry,
                "prediction": self.latest_prediction,
                "last_command": self.last_command_sent,
            }


# Instantiate and start the hardware serial bridge
hardware_bridge = HardwareSerialBridge(port="COM5", baudrate=115200)
hardware_bridge.start()


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

        # 1. Telemetry API endpoint
        if clean_path == "/api/telemetry":
            snapshot = hardware_bridge.get_snapshot()
            self._send_json(200, {
                "success": True,
                "data": snapshot
            })
            return

        # 2. Status & Health endpoint
        if clean_path == "/api/status":
            snapshot = hardware_bridge.get_snapshot()
            self._send_json(200, {
                "success": True,
                "server": "online",
                "serial_connected": snapshot["connected"],
                "port": snapshot["port"],
                "ml_ready": ml_predictor is not None and ml_predictor.is_ml_ready,
                "packets_received": snapshot["packets_received"],
            })
            return

        # 3. Model Info endpoint
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

        # Fallback to static asset serving
        super().do_GET()

    def do_POST(self):
        clean_path = self.path.split("?")[0].rstrip("/")

        # 1. Motor Control API endpoint
        if clean_path == "/api/motor/control":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(raw_body)
            except Exception as e:
                self._send_json(400, {"success": False, "message": f"Malformed JSON request: {e}"})
                return

            action = str(data.get("action", "")).lower().strip()
            value = data.get("value")

            # Map dashboard action to hardware protocol
            cmd_to_send = None
            if action == "start":
                cmd_to_send = "START"
            elif action == "stop":
                cmd_to_send = "STOP"
            elif action == "speed":
                try:
                    val_int = int(round(float(value)))
                    val_int = max(0, min(255, val_int))
                    cmd_to_send = f"SPEED={val_int}"
                except Exception:
                    self._send_json(400, {"success": False, "message": "Invalid speed value"})
                    return
            elif action in ["reverse", "toggle_dir"]:
                cmd_to_send = "REVERSE"
            elif action == "dir_fwd":
                cmd_to_send = "DIR=FWD"
            elif action == "dir_rev":
                cmd_to_send = "DIR=REV"
            elif action in ["estop", "emergency_stop"]:
                cmd_to_send = "ESTOP"
            elif action in ["reset", "clear_trip"]:
                cmd_to_send = "RESET"
            else:
                self._send_json(400, {"success": False, "message": f"Unknown action '{action}'"})
                return

            ok, msg = hardware_bridge.send_command(cmd_to_send)
            self._send_json(200 if ok else 503, {
                "success": ok,
                "action": action,
                "command": cmd_to_send,
                "message": msg,
                "connected": hardware_bridge.connected,
                "port": hardware_bridge.active_port or hardware_bridge.preferred_port
            })
            return

        # 2. Predict API endpoint
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

        # 3. Chatbot endpoint
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

            # If telemetry is not provided by client, enrich with live hardware snapshot
            if not telemetry and hardware_bridge.latest_telemetry:
                telemetry = hardware_bridge.latest_telemetry

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
        msg = str(args[0]) if args else ""
        if "/api/motor/control" in msg:
            print(f"[API] POST /api/motor/control -> {args[1] if len(args) > 1 else ''}")
        elif "/api/chat" in msg:
            print(f"[API] POST /api/chat -> {args[1] if len(args) > 1 else ''}")
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve_dir = Path(__file__).resolve().parent
    handler = partial(SCADAHandler, directory=str(serve_dir))
    with ThreadingHTTPServer(("0.0.0.0", port), handler) as httpd:
        print("=" * 70)
        print(f" EquipmentHealth SCADA Server & Motor Control Console")
        print(f" URL:         http://localhost:{port}")
        print(f" Static Dir:  {serve_dir}")
        print(f" Hardware:    COM5 (115200 baud, auto-reconnecting)")
        print(f" Control API: http://localhost:{port}/api/motor/control")
        print(f" Telemetry:   http://localhost:{port}/api/telemetry")
        print(f" Chatbot API: http://localhost:{port}/api/chat")
        print("=" * 70)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            hardware_bridge.running = False


if __name__ == "__main__":
    main()
