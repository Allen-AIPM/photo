"""Qwen vision tagging through the OpenAI-compatible HTTP API."""
import base64
import hashlib
import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request

MODEL = 'qwen3-vl-plus'
DIMENSIONS = ['建筑类型', '设计风格', '材料元素', '色彩特征', '场景用途']


def atomic_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def load_config(root):
    config_path = root / '.private' / 'API KEY.txt'
    if not config_path.exists():
        raise ValueError('缺少 .private/API KEY.txt，请将本地接口配置放入该文件。')
    content = config_path.read_text(encoding='utf-8-sig')
    config = {}
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        pair = re.split(r'\s*[=：]\s*', line.strip(), maxsplit=1)
        if len(pair) == 2:
            config[pair[0].upper().replace(' ', '_')] = pair[1].strip().strip('"\'')
    key = config.get('API_KEY', '')
    url = config.get('URL', config.get('BASE_URL', '')).rstrip('/')
    if not key or key.startswith('请') or not url or '请' in url:
        raise ValueError('请先在 .private/API KEY.txt 中填写 API_KEY 和 URL（阿里云 OpenAI 兼容地址）。')
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('URL 必须是 HTTPS 接口地址，不应包含密钥、查询参数或账号。')
    if not (parts.hostname.endswith('.aliyuncs.com') or parts.hostname == 'dashscope.aliyuncs.com'):
        raise ValueError('URL 应为阿里云官方 aliyuncs.com 地址。')
    if not url.endswith('/chat/completions'):
        url += '/chat/completions'
    return key, url


def validate_tags(tags):
    if not isinstance(tags, dict) or set(tags) != set(DIMENSIONS):
        raise ValueError('模型结果必须恰好包含五个指定维度。')
    for dimension in DIMENSIONS:
        values = tags[dimension]
        if not isinstance(values, list) or len(values) > 3:
            raise ValueError('每个维度必须是最多三个标签的数组。')
        if any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in values):
            raise ValueError('标签必须是非空字符串。')
        if len(set(values)) != len(values):
            raise ValueError('同一维度不能包含重复标签。')
    return {d: tags[d] for d in DIMENSIONS}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_tags(path, prompt, key, url, expected_hash):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError('图片在去重后发生变化，请等待 RPA 完成后重试。')
    if len(content) >= 7 * 1024 * 1024:
        raise ValueError('图片超过本地 Base64 上传的 7MB 限制，请先压缩。')
    mime = mimetypes.guess_type(path.name)[0]
    if not mime or not mime.startswith('image/'):
        raise ValueError('无法识别图片格式。')
    payload = {'model': MODEL, 'enable_thinking': False, 'stream': False,
               'max_tokens': 1200,
               'messages': [{'role': 'user', 'content': [
                   {'type': 'image_url', 'image_url': {'url': 'data:'+mime+';base64,'+base64.b64encode(content).decode('ascii')}},
                   {'type': 'text', 'text': prompt}]}]}
    request = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={
        'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(NoRedirect())
    for attempt in range(3):
        try:
            with opener.open(request, timeout=120) as response:
                result = json.load(response)
            choice = result['choices'][0]
            if choice.get('finish_reason') != 'stop':
                raise ValueError('模型输出未正常完成。')
            return validate_tags(json.loads(choice['message']['content']))
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise ValueError(f'阿里云接口返回 HTTP {error.code}，请检查密钥、地域、模型权限或额度。') from None
        except (urllib.error.URLError, TimeoutError):
            raise ValueError('接口连接失败或超时；已完成标签已保存，可再次运行。') from None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ValueError('模型未返回有效的五维 JSON，本张未保存为成功。') from None


def tag_library(root, payload, config, prompt):
    key, url = config
    cache_path = root / 'ai-tags.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    report = {'model': MODEL, 'enable_thinking': False, 'success': 0, 'cached': 0, 'failed': []}
    for index, item in enumerate(payload['items'], 1):
        digest = item['sha256']
        cache_key = digest + ':' + MODEL + ':' + prompt_hash
        try:
            if cache_key in cache:
                tags = validate_tags(cache[cache_key]['tags'])
                report['cached'] += 1
            else:
                print(f'  [{index}/{len(payload["items"])}] 正在打标 {item["file"]}', flush=True)
                tags = request_tags(root / 'public' / 'image' / item['file'], prompt, key, url, digest)
                cache[cache_key] = {'tags': tags, 'file': item['file'], 'model': MODEL, 'promptHash': prompt_hash}
                atomic_json(cache_path, cache)
                report['success'] += 1
            item.update(aiTags=tags, tags=list(dict.fromkeys(t for values in tags.values() for t in values)),
                        taggingStatus='success', taggingModel=MODEL)
        except ValueError as error:
            report['failed'].append({'file': item['file'], 'error': str(error)})
            item['taggingStatus'] = 'failed'
            print(f'  打标失败：{item["file"]}：{error}', flush=True)
    atomic_json(root / 'tagging-report.json', report)
    return report
