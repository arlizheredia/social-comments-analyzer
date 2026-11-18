#!/usr/bin/env python3
"""Construye la extensión de Chrome a partir de index.html.

- Copia el extractor (función fbExtractor de index.html) a extension/extractor.js (una única fuente).
- Genera el ZIP descargable desde la app: downloads/social-comments-analyzer-extension.zip
- Comprueba que EXT_LATEST de index.html coincide con la versión del manifiesto.
- Firma el extractor (extension/extractor.sig) para la actualización automática: la extensión instalada
  descarga el extractor publicado y solo lo acepta si la firma corresponde a la clave pública de sw.js.

Actualizar solo el extractor (sin que nadie reinstale nada): sube EXTRACTOR_LATEST en index.html,
ejecuta este script y publica. Si el cambio necesita una extensión nueva (sw.js, manifest.json o bridge.js),
sube también la versión del manifiesto, EXT_LATEST y EXTRACTOR_MIN_EXT.

La clave privada se guarda FUERA del repositorio, en ~/.config/sca-extension/extractor-signing-key.pem
(o en la ruta de la variable SCA_SIGNING_KEY). Si no existe, se crea la primera vez. Haz una copia de seguridad:
sin ella no se pueden publicar actualizaciones automáticas para las extensiones ya instaladas.

    python3 tools/build_extension.py          # genera extractor.js, su firma y el ZIP
    python3 tools/build_extension.py --check  # falla si algo está desactualizado o la firma no es válida
"""
import pathlib, re, sys, zipfile, io, os, base64, json

ROOT = pathlib.Path(__file__).resolve().parent.parent
html = (ROOT / 'index.html').read_text(encoding='utf-8')
start = html.index('function fbExtractor(){')
end = html.index('\n}\n', start) + 2          # la función termina en la primera "}" sola en su línea
fn = html[start:end]
assert fn.count('{') == fn.count('}'), 'No se pudo delimitar fbExtractor'
version = re.search(r'"version":\s*"([^"]+)"', (ROOT / 'extension' / 'manifest.json').read_text()).group(1)
ext_ver = re.search(r"const EXTRACTOR_LATEST = '([^']+)'", html).group(1)
min_ext = re.search(r"const EXTRACTOR_MIN_EXT = '([^']+)'", html).group(1)
out = ('// GENERADO desde index.html (fbExtractor) por tools/build_extension.py — no editar a mano.\n'
       f'// sca-extractor {ext_ver} · requiere extensión {min_ext}\n'
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

sig_path = ROOT / 'extension' / 'extractor.sig'
sw_path = ROOT / 'extension' / 'sw.js'
KEY = pathlib.Path(os.environ.get('SCA_SIGNING_KEY') or pathlib.Path.home() / '.config' / 'sca-extension' / 'extractor-signing-key.pem')
PUB_RE = re.compile(r'const PUBKEY = (\{[^}]*\});')
b64u = lambda n: base64.urlsafe_b64encode(n.to_bytes(32, 'big')).rstrip(b'=').decode()
vt = lambda v: tuple(int(x) for x in v.split('.'))

def sw_pubkey():
    from cryptography.hazmat.primitives.asymmetric import ec
    j = json.loads(PUB_RE.search(sw_path.read_text(encoding='utf-8')).group(1))
    if not j.get('x'): return None
    pad = lambda s: base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))
    return ec.EllipticCurvePublicNumbers(int.from_bytes(pad(j['x']), 'big'), int.from_bytes(pad(j['y']), 'big'), ec.SECP256R1()).public_key()

def sig_ok(data):
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    pub = sw_pubkey()
    if not pub or not sig_path.exists(): return False
    raw = base64.b64decode(sig_path.read_text().strip())
    try: pub.verify(utils.encode_dss_signature(int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big')), data, ec.ECDSA(hashes.SHA256())); return True
    except InvalidSignature: return False

def sign(data):
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from cryptography.hazmat.primitives import hashes, serialization
    if KEY.exists(): key = serialization.load_pem_private_key(KEY.read_bytes(), None)
    else:
        key = ec.generate_private_key(ec.SECP256R1())
        KEY.parent.mkdir(parents=True, exist_ok=True)
        KEY.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        os.chmod(KEY, 0o600)
        print(f'Clave de firma nueva creada en {KEY}: haz una copia de seguridad y no la subas al repositorio.')
    pn = key.public_key().public_numbers()
    jwk = json.dumps({'kty': 'EC', 'crv': 'P-256', 'x': b64u(pn.x), 'y': b64u(pn.y)}, separators=(',', ':'))
    sw = sw_path.read_text(encoding='utf-8')
    old = PUB_RE.search(sw).group(1)
    if old != jwk:
        if json.loads(old).get('x'): print('AVISO: la clave pública de sw.js cambia: las extensiones instaladas no aceptarán actualizaciones hasta reinstalarlas.')
        sw_path.write_text(sw.replace(f'const PUBKEY = {old};', f'const PUBKEY = {jwk};'), encoding='utf-8')
    r, s = utils.decode_dss_signature(key.sign(data, ec.ECDSA(hashes.SHA256())))
    sig_path.write_text(base64.b64encode(r.to_bytes(32, 'big') + s.to_bytes(32, 'big')).decode() + '\n')

if '--check' in sys.argv:
    problems = []
    if vt(min_ext) > vt(version): problems.append(f'EXTRACTOR_MIN_EXT ({min_ext}) es mayor que la versión de la extensión ({version})')
    if not sig_ok(out.encode('utf-8')): problems.append('extension/extractor.sig no corresponde al extractor o a la clave pública de sw.js')
    if not (target.exists() and target.read_text(encoding='utf-8') == out): problems.append('extension/extractor.js desactualizado')
    if not (zip_path.exists() and zip_path.read_bytes() == build_zip(out)): problems.append('downloads/social-comments-analyzer-extension.zip desactualizado')
    if not latest or latest.group(1) != version: problems.append(f"EXT_LATEST de index.html ({latest.group(1) if latest else '—'}) no coincide con el manifiesto ({version})")
    print('Extensión al día (v' + version + ')' if not problems else 'DESACTUALIZADO: ' + '; '.join(problems) + ' → ejecuta python3 tools/build_extension.py')
    sys.exit(1 if problems else 0)
if vt(min_ext) > vt(version): sys.exit(f'EXTRACTOR_MIN_EXT ({min_ext}) no puede ser mayor que la versión de la extensión ({version})')
target.write_text(out, encoding='utf-8')
sign(out.encode('utf-8'))
zip_path.parent.mkdir(exist_ok=True)
zip_path.write_bytes(build_zip(out))
print(f'extension/extractor.js generado y firmado ({len(out)//1024} KB, extractor v{ext_ver})')
print(f'{zip_path.relative_to(ROOT)} generado ({zip_path.stat().st_size//1024} KB, v{version})')
if not latest or latest.group(1) != version: print(f"AVISO: actualiza EXT_LATEST en index.html a '{version}'")
