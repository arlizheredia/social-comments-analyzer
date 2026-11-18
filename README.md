# Social Comments Analyzer

Aplicación web en un único archivo HTML para obtener, analizar, copiar y exportar los comentarios de publicaciones de **Facebook**, **Instagram** y **TikTok**.

## Características

- **Facebook, Instagram y TikTok**: la red social se detecta automáticamente al pegar un enlace.
- **Seguimiento diario de varias publicaciones**: lista de publicaciones, seguimientos con fecha que extraen todos los comentarios con progreso en porcentaje, se pueden detener y continuar, e **historial** guardado en el navegador (IndexedDB) con copia de seguridad.
- **Extensión de Chrome** (descargable desde la app como ZIP), imprescindible para los seguimientos: abre cada publicación en una ventana de trabajo (pequeña o minimizada, sin interrumpirte), abre su sección de comentarios y los extrae sin paneles. Para tus páginas también sirve la API de Meta. El marcador queda como auxiliar para extraer una publicación puntual desde *Obtener*.
- **Informes profesionales** a partir de varios seguimientos: resumen ejecutivo, KPI (comentarios positivos y negativos, tasa y tiempo de respuesta), evolución entre fechas, publicaciones y redes, audiencia (quién más comenta, embajadores, detractores, influyentes), marcas y temas vigilados, alertas y recomendaciones. Exportación a **Word, PDF**, HTML y Excel, y **copiar texto** con formato.
- **Búsqueda por significado con IA gratuita**: modelo multilingüe que se ejecuta en el navegador (Transformers.js) o clasificación con la IA configurada, combinable con los filtros de polaridad.
- **Tres formas de obtener comentarios**
  - **Conectar con la API** (inicio de sesión de Facebook): páginas de Facebook que administras y sus cuentas profesionales de Instagram vinculadas; fechas exactas, reacciones o me gusta y respuestas.
  - **Extractor de navegador** (marcador *Social Comments Analyzer*): para cualquier publicación visible con tu sesión. El mismo marcador funciona en Facebook, Instagram y TikTok.
  - **Importar** JSON o CSV.
- **Vista de conversación** con el estilo de cada red y respuestas anidadas, o **vista de tabla** con todos los campos.
- **Análisis**: actividad en el tiempo y por hora, autores más activos, sentimiento estimado, palabras, emojis, hashtags y menciones.
- **Búsqueda y filtros** por texto, autor, tipo, sentimiento, preguntas, reacciones, adjuntos y comentarios sin respuesta de tu equipo.
- **IA gratuita sin claves**: IA integrada de Chrome o la **IA de la app** (Qwen2.5 0.5B Instruct con Transformers.js), que se descarga una vez desde el diálogo de IA (≈ 500 MB, con progreso), queda configurada sola y funciona sin conexión. También Gemini, Groq, OpenRouter u Ollama; si el proveedor elegido falla y la IA de la app está instalada, responde esta.
- **Asistente de respuestas**: define tu equipo, detecta los comentarios que nadie del equipo ha respondido, propone una respuesta de tu catálogo o sugerida por IA gratuita, y la publica en Facebook o Instagram (con verificación posterior) o la copia y abre el comentario.
- **Copiar y exportar** a Excel (.xlsx), CSV, JSON, texto, Markdown o informe HTML, con la plataforma de cada comentario.
- Diseño Material 3, responsive, tema claro/oscuro, tutorial de inicio y centro de ayuda contextual.
- Todo se procesa en el navegador: no hay servidor.

## Uso

**En línea (HTTPS):** <https://arlizheredia.github.io/social-comments-analyzer/>

También puedes abrir `index.html` directamente en el navegador. La primera vez se muestra un tutorial con los pasos para empezar.

Para **conectar con la API**, la página debe servirse por `https://` (la versión publicada ya lo cumple; agrega `arlizheredia.github.io` a los dominios permitidos de tu app de Meta) o por `http://localhost`:

```bash
python3 -m http.server 8000
# abre http://localhost:8000
```

Necesitas el **App ID** de una app de Meta con estos permisos:

- Facebook: `pages_show_list`, `pages_read_engagement` y `pages_read_user_content`.
- Para publicar respuestas desde el asistente: `pages_manage_engagement` (se pide solo cuando hace falta). Responder exige una sesión de Facebook activa.
- Instagram (además de los anteriores): `instagram_basic` e `instagram_manage_comments`. La cuenta de Instagram debe ser profesional (Empresa o Creador) y estar vinculada a una página de Facebook que administres.

La guía completa está en la sección **Ayuda** de la aplicación.

## Extensión de Chrome

- Código en `extension/`; el extractor (`extension/extractor.js`) se genera desde `index.html` para que haya una sola fuente.
- `python3 tools/build_extension.py` regenera el extractor y el ZIP descargable `downloads/social-comments-analyzer-extension.zip`; con `--check` comprueba que todo está al día (también la versión `EXT_LATEST` de la app).
- Instalación: descargar el ZIP desde *Seguimiento*, descomprimirlo y cargarlo en `chrome://extensions` › *Modo de desarrollador* › *Cargar descomprimida* (detallado en el Centro de ayuda).

## Pruebas

- `tests/responder.test.html`: publicación de respuestas con una Graph API simulada (endpoint, token, hilo, permisos, verificación, errores, sesión, Instagram, regla del equipo).
- `tests/seguimiento.test.html`: lista de publicaciones, seguimientos con la extensión simulada (progreso, detener y continuar), modo manual, historial, informe y exportaciones a Word/HTML, búsqueda por significado y copia de seguridad.

```bash
node tools/run-tests.mjs            # ejecuta todos los tests en Chrome sin interfaz (Node 22+)
# o en el navegador: python3 -m http.server 8000 → http://localhost:8000/tests/
```

## Limitaciones

- La API solo da acceso a publicaciones de páginas y cuentas que administras; para las demás se usa el extractor.
- TikTok no ofrece una API pública de comentarios: para TikTok se usa el extractor o la importación.
- El extractor de navegador requiere un ordenador; las versiones móviles de Facebook, Instagram y TikTok no lo admiten.
- En Facebook y TikTok, las fechas del extractor son aproximadas, porque la página muestra tiempos relativos o solo el día (“2 h”, “3 sem”, “11-5”). En Instagram son exactas.
- Las condiciones de uso de Facebook, Instagram y TikTok limitan la recogida automatizada de datos: usa el extractor de forma responsable.
- El sentimiento se estima con un diccionario de palabras y emojis; es orientativo.
- La API de Meta publica las respuestas como la página o la cuenta profesional, no como una persona, y solo en el hilo del comentario principal.
