import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from deduplicate import group_images, delete_duplicates

ROOT = Path(__file__).resolve().parents[1]
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def source_from_url(url):
    url = str(url or '').lower()
    if 'xiaohongshu' in url:
        return '小红书'
    if 'pinterest' in url or 'pin.it' in url:
        return 'Pinterest'
    return '待补充'

labels = [
    ('建筑 AI 出图模式与工作流', ['建筑设计', 'AI 灵感']),
    ('城市办公建筑 · 暖光与玻璃立面', ['建筑设计']),
    ('东方庭院 · 景观设计与表达', ['景观庭院']),
    ('室内空间 · AI 效果对比', ['室内空间', 'AI 灵感']),
    ('林下庭院 · 自然与建筑之间', ['景观庭院']),
    ('红色构筑物 · 公共空间装置', ['建筑设计', '景观庭院']),
    ('树影下的户外休憩空间', ['景观庭院']),
    ('开放街区 · 建筑效果图表达', ['建筑设计']),
    ('极简灰调 · 开放式厨房', ['室内空间']),
]
metadata = {}
with zipfile.ZipFile(ROOT / '灵感库.xlsx') as z:
    strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        strings = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    rels = {r.attrib['Id']: r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet', NS):
        rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        target = rels[rid]
        path = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        rows = []
        for row in ET.fromstring(z.read(path)).findall('.//m:sheetData/m:row', NS):
            values = {}
            for c in row.findall('m:c', NS):
                key = re.sub(r'\d', '', c.attrib['r'])
                v = c.find('m:v', NS)
                value = v.text if v is not None else ''
                if c.attrib.get('t') == 's': value = strings[int(value)]
                if c.attrib.get('t') == 'inlineStr': value = ''.join(c.find('m:is', NS).itertext())
                values[key] = value
            rows.append(values)
        for row in rows[1:]:
            if row.get('A'):
                metadata[row['A'].strip()] = dict(title=row.get('B',''), author=row.get('C',''), likes=row.get('D',''), url=row.get('E',''), source=source_from_url(row.get('E','')))
items = []
overrides_path = ROOT / 'metadata-overrides.json'
overrides = json.loads(overrides_path.read_text(encoding='utf-8')) if overrides_path.exists() else {}
image_directory = ROOT / 'public' / 'image'
if not image_directory.exists():
    raise FileNotFoundError('缺少 public/image 图片目录。')
files = sorted(p for p in image_directory.iterdir() if p.suffix.lower() in {'.jpg','.jpeg','.png','.webp','.gif','.avif'})
known = ['20260906095206401.jpg','20260906095216508.jpg','20260906095227651.jpg','20260906095238729.jpg','20260906095248851.jpg','20260906095259938.jpg','20260906095313059.jpg','20260906095322254.jpg','20260906095323322.jpg']
previous_path = ROOT / 'src' / 'data.json'
previous_items = []
if previous_path.exists():
    previous_items = json.loads(previous_path.read_text(encoding='utf-8'))['items']
previous = {item['sha256']: item['file'] for item in previous_items if item.get('sha256')}
previous_by_hash = {item['sha256']: item for item in previous_items if item.get('sha256')}
groups = group_images(files, metadata, previous)
for group in groups:
    p = group['primary']
    title, tags = labels[known.index(p.name)] if p.name in known else (p.stem, ['未分类'])
    item = dict(file=p.name, title=title, tags=tags, author='', likes='', url='', source='待补充', inferred=True)
    if p.name in metadata:
        item.update(metadata[p.name]); item['inferred'] = False
    # Keep user-confirmed source corrections until Excel supplies a known source.
    if item['source'] == '待补充' and p.name in overrides:
        item['source'] = overrides[p.name].get('source', item['source'])
    item['sha256'] = group['sha256']
    old = previous_by_hash.get(group['sha256'], {})
    # Preserve prior tagging fields instead of replacing them with defaults.
    for key in ('tags', 'aiTags', 'taggingStatus', 'taggingModel'):
        if key in old:
            item[key] = old[key]
    item['aliases'] = [member.name for member in group['members']]
    item['duplicateRecords'] = [dict(file=member.name, **metadata[member.name]) for member in group['members'] if member.name in metadata]
    if item['source'] == '待补充':
        for member in group['members']:
            confirmed = overrides.get(member.name, {}).get('source')
            if confirmed:
                item['source'] = confirmed
                break
    items.append(item)
report = dict(algorithm='SHA-256 (exact file bytes)', scanned=len(files), unique=len(groups), duplicates=len(files)-len(groups), groups=[dict(sha256=g['sha256'], retained=g['primary'].name, duplicates=[p.name for p in g['members'][1:]]) for g in groups if len(g['members']) > 1])
payload = dict(items=items, missing=[f for f in metadata if f not in {p.name for p in files}], matched=sum(not i['inferred'] for i in items), deduplication=report)
def atomic_write(path, text):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)

atomic_write(ROOT / 'dedup-report.json', json.dumps(report, ensure_ascii=False, indent=2)+'\n')
deleted = delete_duplicates(groups, image_directory)
report['deleted'] = deleted
atomic_write(ROOT / 'dedup-report.json', json.dumps(report, ensure_ascii=False, indent=2)+'\n')
atomic_write(ROOT / 'src' / 'data.json', json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
print(f'Deduplicated: {len(files)} files -> {len(groups)} unique images; {len(deleted)} new duplicate files deleted. Original images and tags preserved.')
print(f'Updated: {len(items)} images, {payload["matched"]} matched, {len(payload["missing"])} missing.')
