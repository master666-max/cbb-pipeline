import os, re, sys, zipfile, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')
zf = zipfile.ZipFile('迷深.epub')

def fixname(info):
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode('cp437').decode('utf-8')
    except Exception:
        return info.filename

names = {fixname(i): i.filename for i in zf.infolist()}
opf_path = next(n for n in names if n.lower().endswith('.opf'))
opf = ET.fromstring(zf.read(names[opf_path]))
OPF = '{http://www.idpf.org/2007/opf}'
manifest = {it.get('id'): it.get('href') for it in opf.iter(OPF+'item')}
spine_ids = [it.get('idref') for it in opf.iter(OPF+'itemref')]

href_map = {}
for n in names:
    base = os.path.basename(n)
    href_map[base] = n

out, missing = [], 0
for i, sid in enumerate(spine_ids):
    href = manifest.get(sid)
    if not href: continue
    key = os.path.basename(href)
    zpath = href_map.get(key)
    if zpath is None:
        missing += 1; continue
    raw = zf.read(zpath)
    soup = BeautifulSoup(raw, 'html.parser')
    for t in soup(['script','style']): t.decompose()
    text = soup.get_text('\n')
    text = re.sub(r'[ \t\u3000]+', '', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()
    if len(text) < 20: continue
    chap = re.sub(r'\.(html?|xhtml)$', '', key, flags=re.I)
    out.append(f'<<<CHAPTER {i:04d} | {chap}>>>\n{text}')

full = '\n\n'.join(out)
os.makedirs('corpus', exist_ok=True)
open('corpus/mishen_full.txt', 'w', encoding='utf-8').write(full)
print(f'spine: {len(spine_ids)}, missing: {missing}, kept: {len(out)}, chars: {len(full):,}')
