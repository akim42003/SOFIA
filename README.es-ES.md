

# SOFIA - Sort of Functional Interactive Agent

Una plataforma sofisticada de asistente de IA que combina automatización de escritorio, gestión de correo/calendario y capacidades de interacción multimodal. SOFIA proporciona una solución flexible y consciente de la privacidad para automatizar tareas a través de conversaciones en lenguaje natural.

## Descripción General

SOFIA opera a través de múltiples interfaces (web, superposición de escritorio y servidor MCP) con un sistema de backend de IA dual que admite tanto modelos locales (Ollama) como en la nube (OpenAI). La plataforma utiliza visión por computadora avanzada para la automatización de la interfaz de usuario y se integra perfectamente con los servicios de Google mientras mantiene estrictos límites de seguridad.

## Características Principales

- **Automatización de Escritorio**: Detección de elementos de UI impulsada por visión por computadora usando OmniParser, control preciso de ratón/teclado, análisis de capturas de pantalla y ejecución de comandos de shell en un entorno aislado (sandbox)
- **Integración de Correo y Calendario**: Funcionalidad completa de Gmail (buscar, componer, responder, reenviar) y gestión de Google Calendar a través de lenguaje natural con autenticación OAuth2
- **Almacenamiento Local de Conversaciones**: Compacta y almacena conversaciones anteriores como archivos md para su uso y referencia futura.
- **Procesamiento Multimodal**: Soporte para chat de texto e imagen, transcripción de archivos de audio vía Whisper, respuestas en flujo en tiempo real y manejo de archivos por arrastrar y soltar
- **Backend de IA Flexible**: Intercambio en caliente entre modelos locales de Ollama (enfocados en privacidad, sin conexión) y la API de OpenAI (más rápida, más precisa) mediante el patrón Brain Factory
- **Diseño Priorizado en Seguridad**: Todas las operaciones de archivos están aisladas (sandbox) en el directorio ~/SOFIA/, validación de parámetros, manejo elegante de errores y gestión segura de claves API

## Arquitectura

SOFIA emplea una arquitectura modular con tres interfaces principales:

1. **Interfaz Web** (`sofia_web.py`): Interfaz de usuario basada en Gradio para chat multimodal y transcripción de audio
2. **Interfaz de Escritorio** (`sofia_desktop.py`): Superposición transparente con PyQt6 para una integración perfecta en el escritorio
3. **Servidor MCP** (`sofia_gmail.py`): Servidor del Protocolo de Contexto de Modelo para servicios de Google

El sistema utiliza un flujo de trabajo PIENSA → PLANIFICA → EJECUTA → VERIFICA para la finalización autónoma de tareas, con ejecución concurrente de herramientas y gestión de memoria de conversación.

## Demo

Vea las capacidades de uso de computadora de SOFIA en acción:

[sofia_demo.webm](https://github.com/user-attachments/assets/25946eb9-cc1b-4ab6-b653-7ceeb6a51e9b)

*La demostración muestra la capacidad de SOFIA para comprender interfaces visuales, navegar por aplicaciones y realizar tareas de automatización de escritorio.*

## Primeros Pasos

### Requisitos

- Ubuntu 22.04+ (soporte para Windows/macOS planeado)
- Python 3.11+
- Para uso de computadora e IA local: GPU con CUDA habilitado (se recomienda 24GB+)
- Para IA en la nube: Clave API de OpenAI
- Credenciales de Google para las funciones de correo/calendario
- Se recomienda un monitor separado para la automatización de escritorio

### Instalación

```bash
git clone https://github.com/akim42003/SOFIA.git
cd SOFIA
conda create -n sofia python=3.11
conda activate sofia
pip install -r requirements.txt

# For local AI models
ollama create sofia -f Modelfile.enhanced
```

### Configuración de Servicios de Google

1. Coloque `credentials.json` en la raíz del proyecto
2. Ejecute `python sofia_gmail.py` para autenticarse
3. Siga el flujo de OAuth2 en el navegador

### Uso

```bash
# Web interface with audio support
python sofia_web.py      # Access at localhost:7860

# Desktop overlay interface
python sofia_desktop.py  # Transparent UI overlay

# Gmail/Calendar server
python sofia_gmail.py    # MCP server on port 3000
```

## Visión por Computadora y Automatización

La automatización de escritorio de SOFIA aprovecha la visión por computadora avanzada:

- **Integración de OmniParser**: Detección de elementos de UI basada en YOLO con subtítulos de Florence2/BLIP2
- **Anclaje Visual**: Mapea descripciones en lenguaje natural a coordenadas de píxeles precisas
- **Análisis de Capturas de Pantalla**: Captura e interpretación de pantalla en tiempo real
- **Recuperación de Errores**: Mecanismos de reintentos automáticos con verificación visual

## Opciones de Backend de IA

### Modelos Locales (Ollama)
- **Ventajas**: Privacidad completa, operación sin conexión, sin costos de API
- **Desventajas**: Requiere GPU con CUDA (24GB+ de VRAM), inferencia más lenta
- **Modelos Recomendados**: mistral-small3.1:24b, llama4, modelo personalizado sofia

### Modelos en la Nube (OpenAI)
- **Ventajas**: Respuesta más rápida, mayor precisión, sin requisitos de hardware
- **Desventajas**: Costos de API, requiere internet, consideraciones de privacidad de datos
- **Modelos Disponibles**: gpt-4o, gpt-o4mini, etc.

### Gestión del Backend

```bash
python switch_backend.py status   # Check current backend
python switch_backend.py openai   # Switch to OpenAI
python switch_backend.py ollama   # Switch to Ollama
```

## Configuración

### Configuración Principal
Edite `config/sofia_config.yaml`:

```yaml
ai_backend: "ollama"  # or "openai"
openai:
  model: "gpt-4o"
ollama:
  model: "sofia2"
```

### Configuración de Herramientas
Personalice el comportamiento del agente y las herramientas disponibles en `config/tools`

### Personalización del Usuario
Cree `config/user_config.yaml` para preferencias y contexto personal

## Consideraciones de Seguridad

- Todas las operaciones de archivos están restringidas al directorio `~/SOFIA/`
- Claves API gestionadas a través de variables de entorno
- OAuth2 para la autenticación de servicios de Google
- Validación de parámetros en todas las invocaciones de herramientas
- Sin ejecución arbitraria de código fuera del entorno aislado (sandbox)

## Solución de Problemas

- **Problemas de Memoria de GPU**: Reduzca el tamaño del modelo o cambie a inferencia por CPU
- **Rendimiento de OCR**: Asegúrese de que CUDA esté configurado correctamente para OmniParser
- **Autenticación de Gmail**: Verifique credentials.json y la validez del token OAuth2
- **Control de Escritorio**: Verifique los permisos de PyAutoGUI y la configuración de pantalla

Desarrollado por Alex Kim.
