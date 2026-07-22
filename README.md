# DataExtractor - Suite OSINT Multi-Plataforma

Herramienta de automatización para extraer datos públicos de perfiles en múltiples redes sociales: **Instagram**, **TikTok**, **X (Twitter)** y **Facebook**. El sistema ofrece dos interfaces (Web y Escritorio) y dos modos de operación principales.

## Características Principales

1. **Buscador OSINT Multi-Red:** Introduce un nombre de usuario y el sistema lo busca simultáneamente en las 4 redes sociales, devolviendo todos los datos públicos de cada perfil encontrado en una tabla comparativa.
2. **Extractor por Plataforma:** Selecciona la red social, el método (API automática o Selenium manual) y el usuario objetivo para extraer datos detallados.
3. **Interfaz Web (Dashboard):** Panel de control con tema oscuro, barra lateral y tarjetas de resultados con colores por plataforma.
   - **Historial Integrado:** Registro de todas las extracciones con opción de descarga.
   - **Ajustes:** Guarda credenciales de Instagram para autocompletar formularios.
4. **Aplicación de Escritorio Nativa:** Ventana de sistema ligera (creada con `customtkinter`).
5. **Plataformas Soportadas:**
   - **Instagram:** Extracción vía Instaloader (API) o Selenium (manual).
   - **TikTok:** Extracción de perfil público (HTTP directo, sin login).
   - **X (Twitter):** Extracción de perfil público y seguidores vía Selenium.
   - **Facebook:** Extracción de perfil público y amigos vía Selenium.

---

## Instalación Automática (Recomendada)

1. Asegúrate de tener instalado **Python 3.8 o superior**.
2. Entra en la carpeta del proyecto.
3. Haz doble clic en el archivo `instalar.bat`.
4. El sistema instalará automáticamente todas las librerías necesarias y creará accesos directos en tu Escritorio:
   - `Extractor de Seguidores (Escritorio)`
   - `Extractor de Seguidores (Web)`

## Uso Rápido

- **Interfaz Web:** Haz doble clic en el acceso directo **"Extractor de Seguidores (Web)"** o ejecuta `python app.py` y abre `http://127.0.0.1:5000`.
- **Interfaz de Escritorio:** Haz doble clic en **"Extractor de Seguidores (Escritorio)"** o ejecuta `python gui_app.py`.

## Instalador para Terceros (.exe)

Si deseas compartir esta herramienta con personas que **no tienen Python instalado**:

1. Ve a la carpeta `dist/DataExtractor_Moderno/` generada tras la compilación.
2. Copia la carpeta completa y envíala, o ejecuta el archivo `DataExtractor_Moderno.exe`.
3. El usuario solo tiene que hacer doble clic en el `.exe` para iniciar la suite completa (no necesita instalar nada extra).

---

## Ejecución Manual (Para Desarrolladores)

- **Versión Web:**
  ```bash
  python app.py
  ```
  *(Luego entra a http://127.0.0.1:5000 en tu navegador)*

- **Versión de Escritorio:**
  ```bash
  python gui_app.py
  ```

### Dependencias (Si se instalan manualmente)
```bash
pip install instaloader selenium webdriver-manager flask customtkinter requests beautifulsoup4
```

---

## Ejecución con Docker (Servidor Aislado)

Para usuarios de **Docker** que quieran desplegar el Dashboard Web y la suite de herramientas automáticas sin ensuciar su entorno local de Python. 
*(Nota: Al ejecutarse en contenedor (sin pantalla), Selenium operará en modo Headless invisible. Esto es ideal para OSINT, pero complejo si necesitas hacer login manual en FB/Twitter).*

1. Clona el repositorio y abre una terminal en esta misma carpeta.
2. Construye y levanta el contenedor en segundo plano:
   ```bash
   docker-compose up -d --build
   ```
3. Accede al Dashboard desde: `http://localhost:5000`

Tus datos (CSV, JSON, historiales) se guardarán localmente gracias a los *volúmenes* configurados en el archivo `docker-compose.yml`. Para apagar el servidor web:
```bash
docker-compose down
```

---

## Estructura del Proyecto

| Archivo / Directorio | Descripción |
|---|---|
| `app.py` | Servidor web Flask (backend multi-plataforma) |
| `desktop.py` | Lanzador de la aplicación de escritorio y servidor interno |
| `gui_app.py` | Interfaz de escritorio nativa (clásica) con customtkinter |
| `extractors/` | Módulos de lógica: Instagram, TikTok, X, Facebook, OSINT, Sherlock... |
| `templates/index.html` | Interfaz web del Dashboard OSINT moderno |
| `static/` | Archivos CSS (`style.css`) y JS (`main.js`) del frontend web |
| `Output/` | Carpeta local donde se guardan los CSV, JSON y PDF generados |
| `logs/` | Registro de eventos del sistema (debug y errores) |
| `history.json` | Base de datos local que alimenta las analíticas del Dashboard |

---
*Herramienta desarrollada con fines educativos para el análisis de datos públicos en redes sociales.*


## Licencia

Este proyecto está bajo la Licencia MIT - mira el archivo [LICENSE](LICENSE) para detalles.
Copyright (c) 2026 Jorge R.
