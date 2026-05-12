# 🔐 Proyecto de Hacking Ético - Ciberseguridad

> **⚠️ AVISO:** Proyecto exclusivamente **educativo**. El uso indebido sin consentimiento es **ilegal**.

## 📋 Descripción

Aplicación de hacking ético con arquitectura **cliente-servidor** que integra 4 módulos:

| # | Módulo | Descripción |
|---|--------|-------------|
| 1 | **Escaneo de Puertos** | Escanea puertos lógicos abiertos de un PC remoto |
| 2 | **Generador de Contraseñas** | Genera contraseñas seguras de X longitud |
| 3 | **Sniffing de Red** | Captura tráfico de red y lo envía al servidor |
| 4 | **Keylogger** | Captura teclas + screenshots y los envía al servidor |

## 🏗️ Arquitectura (3 Máquinas)

```
┌─────────────────────────┐                    ┌─────────────────────────┐
│   CLIENTE 1 (Víctima)   │     TCP/9999       │                         │
│                         │ ──────────────────▶ │    SERVIDOR             │
│  • Juego de Memorama    │                    │                         │
│  • Keylogger oculto     │                    │  • Recibe teclas        │
│  • Screenshots          │                    │  • Recibe screenshots   │
│  • Sniffer de red       │                    │  • Recibe sniffing      │
└─────────────────────────┘                    │  • Escáner de puertos   │
                                               │  • Generador passwords  │
┌─────────────────────────┐                    │  • GUI con 4 pestañas   │
│   CLIENTE 2 (Víctima)   │     TCP/9999       │                         │
│                         │ ──────────────────▶ │                         │
│  (Mismo que Cliente 1)  │                    └─────────────────────────┘
└─────────────────────────┘
```

## 📦 Requisitos

- **Python 3.8+**
- **Linux** (todas las máquinas)
- **Red LAN** entre las 3 máquinas

### Dependencias

| Paquete | Uso | Dónde |
|---------|-----|-------|
| `evdev` | Captura de teclas | Cliente |
| `Pillow` | Screenshots | Cliente |
| `scapy` | Sniffing de red | Cliente |

> El servidor solo usa la librería estándar de Python.

---

## 🚀 GUÍA DE USO PASO A PASO

### Paso 0: Preparar el Entorno

En **las 3 máquinas**, asegúrate de tener Python 3:

```bash
python3 --version
```

### Paso 1: Configurar el SERVIDOR (Máquina 1)

1. **Copiar el proyecto** a la máquina servidor:
```bash
# Copiar la carpeta Keylog al servidor
scp -r Keylog/ usuario@IP_SERVIDOR:~/
```

2. **Ejecutar el servidor**:
```bash
cd ~/Keylog
python3 server.py
```

3. Se abre la **GUI con 4 pestañas**:
   - ⌨ **Keylogger**: Muestra teclas y screenshots recibidos en tiempo real
   - 🔍 **Port Scanner**: Escanear puertos de cualquier IP
   - 🔑 **Password Gen**: Generar contraseñas seguras
   - 📡 **Sniffer**: Ver tráfico de red capturado por los clientes

4. **Hacer clic en "▶ INICIAR"** para arrancar el servidor TCP

5. **Anotar la IP** que aparece (ej: `192.168.1.100`) — los clientes la necesitan

### Paso 2: Configurar CLIENTES (Máquinas 2 y 3)

1. **Copiar el proyecto** a cada máquina cliente:
```bash
scp -r Keylog/ usuario@IP_CLIENTE:~/
```

2. **Instalar dependencias** en cada cliente:
```bash
cd ~/Keylog
pip install -r requirements.txt
```

3. **Ejecutar el cliente** (requiere sudo para evdev y scapy):
```bash
sudo python3 client.py
```

4. Aparece el **juego de Memorama**. En el campo "Clave de acceso":
   - **Escribir la IP del servidor** (ej: `192.168.1.100`)
   - Hacer clic en **"🎮 JUGAR"**

5. El juego inicia normalmente. En segundo plano se ejecutan:
   - **Keylogger**: captura todas las teclas
   - **Screenshots**: captura pantalla cada 60 segundos
   - **Sniffer**: captura el tráfico de red

### Paso 3: Usar el Escáner de Puertos (en el Servidor)

1. Ir a la pestaña **🔍 Port Scanner**
2. Escribir la **IP objetivo** (puede ser la de un cliente)
3. Definir rango (ej: 1-1024 para puertos conocidos)
4. Clic en **"🔍 Escanear"**
5. Los puertos abiertos aparecen en verde

### Paso 4: Usar el Generador de Contraseñas (en el Servidor)

1. Ir a la pestaña **🔑 Password Gen**
2. Configurar:
   - **Longitud** (ej: 16, 24, 32)
   - **Tipos**: Mayúsculas, minúsculas, números, especiales
   - **Cantidad** de contraseñas a generar
3. Clic en **"🔑 Generar"**

### Paso 5: Monitorear (en el Servidor)

- **Pestaña Keylogger**: ver teclas en tiempo real
- **Pestaña Sniffer**: ver tráfico de red capturado
- Los archivos se guardan automáticamente:

```
Keylog/
├── server.py
├── client.py
├── requirements.txt
├── logs/                    ← Teclas capturadas (.txt)
│   └── keylog_192.168.1.50_2026-04-30_20-00-00.txt
├── screenshots/             ← Capturas de pantalla (.png)
│   └── screenshot_20260430_200100.png
└── sniff_captures/          ← Tráfico de red (.txt)
    └── sniff_20260430_200200.txt
```

---

## 📧 Configuración de Email (Opcional)

Para enviar capturas por correo, crear un archivo `.env`:

```bash
# .env
EMAIL_USER=tucorreo@gmail.com
EMAIL_PASS=tu_app_password
EMAIL_TO=destino@gmail.com
```

## 🔧 Protocolo de Comunicación

Mensajes JSON header + payload binario:

```json
{"type": "keys", "size": 45}
<45 bytes de teclas>

{"type": "screenshot", "size": 184320, "filename": "screenshot_20260430.png"}
<184320 bytes PNG>

{"type": "sniff", "size": 1024, "filename": "sniff_20260430.txt"}
<1024 bytes de tráfico capturado>
```

## ⚠️ Consideraciones Éticas

1. **Solo para fines educativos** en ambientes controlados
2. **Nunca instalar** sin consentimiento explícito del propietario
3. El uso no autorizado es un **delito** penado por la ley
4. Demuestra conceptos para aprender a **defender** sistemas

## 👥 Integrantes

| Nombre | Rol |
|--------|-----|
| — | Servidor |
| — | Cliente 1 |
| — | Cliente 2 |

## 🎓 Materia

**Ciberseguridad** — Proyecto de Hacking Ético
