"""Run exact deduplication, cached AI tagging, and update React site data."""
import json
import runpy
import sys
from pathlib import Path

from ai_tagger import load_config, tag_library

ROOT = Path(__file__).resolve().parents[1]


def atomic_write(path, text):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)


try:
    if not (ROOT / '灵感库.xlsx').exists():
        raise FileNotFoundError('缺少灵感库.xlsx。请先让影刀完成数据写入。')
    prompt = (ROOT / '提示词.txt').read_text(encoding='utf-8-sig').strip()
    if not prompt:
        raise ValueError('提示词.txt 不能为空。')
    config = load_config(ROOT)

    print('[1/3] 正在按文件内容去重并同步 Excel 元数据...', flush=True)
    result = runpy.run_path(str(ROOT / 'automation' / 'refresh_data.py'), run_name='__main__')
    payload = result['payload']

    print('[2/3] 正在使用 qwen3-vl-plus 为新增或变更图片打标...', flush=True)
    report = tag_library(ROOT, payload, config, prompt)
    atomic_write(ROOT / 'src' / 'data.json', json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    print(f'新打标：{report["success"]}；使用缓存：{report["cached"]}；失败：{len(report["failed"])}', flush=True)
    if report['failed']:
        raise ValueError('部分图片打标失败。成功结果已保存，请查看 tagging-report.json 后再次运行。')

    print('[3/3] 素材数据已同步，接下来将生成网站图片和构建文件。', flush=True)
except Exception as error:
    print(f'更新失败：{error}', file=sys.stderr, flush=True)
    sys.exit(1)
