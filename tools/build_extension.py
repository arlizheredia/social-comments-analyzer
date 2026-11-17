#!/usr/bin/env python3
"""Construye la extensión de Chrome a partir de index.html.

- Copia el extractor (función fbExtractor de index.html) a extension/extractor.js (una única fuente).
- Genera el ZIP descargable desde la app: downloads/social-comments-analyzer-extension.zip
- Comprueba que EXT_LATEST de index.html coincide con la versión del manifiesto.

    python3 tools/build_extension.py          # genera extractor.js y el ZIP
    python3 tools/build_extension.py --check  # falla si algo está desactualizado
"""
import pathlib, re, sys, zipfile, io

ROOT = pathlib.Path(__file__).resolve().parent.parent
html = (ROOT / 'index.html').read_text(encoding='utf-8')
start = html.index('function fbExtractor(){')
end = html.index('\n}\n', start) + 2          # la función termina en la primera "}" sola en su línea
fn = html[start:end]
assert fn.count('{') == fn.count('}'), 'No se pudo delimitar fbExtractor'
version = re.search(r'"version":\s*"([^"]+)"', (ROOT / 'extension' / 'manifest.json').read_text()).group(1)
out = ('// GENERADO desde index.html (fbExtractor) por tools/build_extension.py — no editar a mano.\n'
       f'// Extensión {version}\n'
       '(function(){\n' + fn + 'fbExtractor();\n})();\n')
target = ROOT / 'extension' / 'extractor.js'
latest = re.search(r"const EXT_LATEST = '([^']+)'", html)
zip_path = ROOT / 'downloads' / 'social-comments-analyzer-extension.zip'
FILES = ['manifest.json', 'sw.js', 'bridge.js', 'extractor.js', 'popup.html', 'popup.js', 'icons/icon16.png', 'icons/icon32.png', 'icons/icon48.png', 'icons/icon128.png']

def build_zip(extractor_src):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            data = extractor_src.encode('utf-8') if f == 'extractor.js' else (ROOT / 'extension' / f).read_bytes()
            info = zipfile.ZipInfo('social-comments-analyzer-extension/' + f, date_time=(2026, 1, 1, 0, 0, 0))   # fecha fija: ZIP reproducible
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return buf.getvalue()

if '--check' in sys.argv:
    problems = []
    if not (target.exists() and target.read_text(encoding='utf-8') == out): problems.append('extension/extractor.js desactualizado')
    if not (zip_path.exists() and zip_path.read_bytes() == build_zip(out)): problems.append('downloads/social-comments-analyzer-extension.zip desactualizado')
    if not latest or latest.group(1) != version: problems.append(f"EXT_LATEST de index.html ({latest.group(1) if latest else '—'}) no coincide con el manifiesto ({version})")
    print('Extensión al día (v' + version + ')' if not problems else 'DESACTUALIZADO: ' + '; '.join(problems) + ' → ejecuta python3 tools/build_extension.py')
    sys.exit(1 if problems else 0)
target.write_text(out, encoding='utf-8')
zip_path.parent.mkdir(exist_ok=True)
zip_path.write_bytes(build_zip(out))
print(f'extension/extractor.js generado ({len(out)//1024} KB)')
print(f'{zip_path.relative_to(ROOT)} generado ({zip_path.stat().st_size//1024} KB, v{version})')
if not latest or latest.group(1) != version: print(f"AVISO: actualiza EXT_LATEST en index.html a '{version}'")
