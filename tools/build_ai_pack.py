#!/usr/bin/env python3
"""Crea el paquete de IA (sca-ia-pack.zip) para instalar la IA de la app sin Internet.

Descarga de Hugging Face los archivos de los dos modelos que usa la app y los guarda en un ZIP
sin compresión (los modelos ONNX no se comprimen) junto con el índice «sca-ia.json».
La app lo instala con «Instalar desde archivo» copiando cada archivo a la caché del navegador
con la misma dirección que usaría la descarga normal.

Uso:
    python3 tools/build_ai_pack.py                 # crea dist/sca-ia-pack.zip
    python3 tools/build_ai_pack.py --out ruta.zip
    python3 tools/build_ai_pack.py --check ruta.zip   # comprueba un paquete existente

Publicación (fuera del historial del repositorio):
    gh release create ia-1 dist/sca-ia-pack.zip --title "Paquete de IA" --notes "Modelos de IA para instalar sin Internet"
La app enlaza a releases/latest/download/sca-ia-pack.zip.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error, zipfile, datetime

# Mismos modelos y variantes que usa la app (index.html: LLM.model, SEM.model; variante q8 = model_quantized.onnx)
MODELS = {
    'onnx-community/Qwen2.5-0.5B-Instruct': ['config.json', 'generation_config.json', 'tokenizer.json', 'tokenizer_config.json', 'onnx/model_quantized.onnx'],
    'Xenova/multilingual-e5-small': ['config.json', 'tokenizer.json', 'tokenizer_config.json', 'onnx/model_quantized.onnx'],
}
OPTIONAL = {'generation_config.json'}
BASE = 'https://huggingface.co/{model}/resolve/main/{file}'
MANIFEST = 'sca-ia.json'


def fetch(url, dest):
    tmp = dest + '.part'
    req = urllib.request.Request(url, headers={'User-Agent': 'sca-ia-pack-builder'})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, 'wb') as f:
        total = int(r.headers.get('content-length') or 0); done = 0; t0 = time.time(); last = 0
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b); done += len(b)
            if time.time() - last > 1:
                last = time.time(); speed = done / max(1e-6, last - t0) / 1e6
                pct = f'{done * 100 // total} %' if total else ''
                print(f'\r    {done / 1e6:8.1f} MB {pct:>6} · {speed:5.1f} MB/s', end='', flush=True)
    os.replace(tmp, dest); print()


def build(out, work):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    files = []
    for model, names in MODELS.items():
        for name in names:
            local = os.path.join(work, model, name)
            os.makedirs(os.path.dirname(local), exist_ok=True)
            if not os.path.exists(local):
                print(f'  Descargando {model}/{name}')
                try: fetch(BASE.format(model=model, file=name), local)
                except urllib.error.HTTPError as e:
                    if e.code == 404 and name in OPTIONAL: print('    (no existe, se omite)'); continue
                    raise
            files.append({'model': model, 'file': name, 'path': f'{model}/{name}', 'size': os.path.getsize(local), 'local': local})
    man = {'app': 'Social Comments Analyzer', 'kind': 'sca-ia-pack', 'version': 1,
           'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'files': [{k: f[k] for k in ('model', 'file', 'path', 'size')} for f in files]}
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as z:
        z.writestr(MANIFEST, json.dumps(man, indent=2, ensure_ascii=False))
        for f in files: z.write(f['local'], f['path'])
    print(f'Paquete creado: {out} ({os.path.getsize(out) / 1e6:.0f} MB, {len(files)} archivos)')


def check(path):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad: sys.exit(f'Archivo dañado en el paquete: {bad}')
        man = json.loads(z.read(MANIFEST))
        names = set(z.namelist())
        for f in man['files']:
            info = z.getinfo(f['path']) if f['path'] in names else None
            if not info: sys.exit(f'Falta {f["path"]}')
            if info.compress_type != zipfile.ZIP_STORED: sys.exit(f'{f["path"]} está comprimido: la app solo admite archivos sin compresión')
            if info.file_size != f['size']: sys.exit(f'Tamaño distinto en {f["path"]}')
        for model in MODELS:
            if not any(f['model'] == model and f['file'].endswith('.onnx') for f in man['files']): sys.exit(f'Falta el modelo {model}')
    print(f'Paquete correcto: {path} ({len(man["files"])} archivos)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default='dist/sca-ia-pack.zip')
    ap.add_argument('--work', default='dist/.ia-cache', help='carpeta donde se guardan las descargas (permite reanudar)')
    ap.add_argument('--check', metavar='ZIP', help='comprueba un paquete existente')
    a = ap.parse_args()
    check(a.check) if a.check else build(a.out, a.work)
