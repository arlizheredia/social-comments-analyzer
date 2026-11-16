# Social Comments Analyzer

Aplicación web en un único archivo HTML para obtener, analizar, copiar y exportar los comentarios de publicaciones de **Facebook**, **Instagram** y **TikTok**.

## Características

- **Facebook, Instagram y TikTok**: la red social se detecta automáticamente al pegar un enlace.
- **Tres formas de obtener comentarios**
  - **Conectar con la API** (inicio de sesión de Facebook): páginas de Facebook que administras y sus cuentas profesionales de Instagram vinculadas; fechas exactas, reacciones o me gusta y respuestas.
  - **Extractor de navegador** (marcador *Social Comments Analyzer*): para cualquier publicación visible con tu sesión. El mismo marcador funciona en Facebook, Instagram y TikTok.
  - **Importar** JSON o CSV.
- **Vista de conversación** con el estilo de cada red y respuestas anidadas, o **vista de tabla** con todos los campos.
- **Análisis**: actividad en el tiempo y por hora, autores más activos, sentimiento estimado, palabras, emojis, hashtags y menciones.
- **Búsqueda y filtros** por texto, autor, tipo, sentimiento, preguntas, reacciones, adjuntos y comentarios sin respuesta de tu equipo.
- **Asistente de respuestas**: define tu equipo, detecta los comentarios que nadie del equipo ha respondido, propone una respuesta de tu catálogo o sugerida por IA gratuita (IA integrada de Chrome, Ollama, Gemini, Groq u OpenRouter), y la publica en Facebook o Instagram (con verificación posterior) o la copia y abre el comentario.
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

## Pruebas

`tests/responder.test.html` comprueba de extremo a extremo la publicación de respuestas con una Graph API simulada: endpoint y token usados, respuesta en el hilo correcto, petición de permisos, verificación posterior, errores, requisito de sesión e Instagram.

```bash
python3 -m http.server 8000
# abre http://localhost:8000/tests/responder.test.html
```

## Limitaciones

- La API solo da acceso a publicaciones de páginas y cuentas que administras; para las demás se usa el extractor.
- TikTok no ofrece una API pública de comentarios: para TikTok se usa el extractor o la importación.
- El extractor de navegador requiere un ordenador; las versiones móviles de Facebook, Instagram y TikTok no lo admiten.
- En Facebook y TikTok, las fechas del extractor son aproximadas, porque la página muestra tiempos relativos o solo el día (“2 h”, “3 sem”, “11-5”). En Instagram son exactas.
- Las condiciones de uso de Facebook, Instagram y TikTok limitan la recogida automatizada de datos: usa el extractor de forma responsable.
- El sentimiento se estima con un diccionario de palabras y emojis; es orientativo.
- La API de Meta publica las respuestas como la página o la cuenta profesional, no como una persona, y solo en el hilo del comentario principal.
