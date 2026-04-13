#!/usr/bin/env python3
import hashlib
import hmac
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / 'index.html'
DOCS_DIR = REPO_ROOT / 'docs'

HOST = os.environ.get('MINIAPP_HOST', '127.0.0.1')
PORT = int(os.environ.get('MINIAPP_PORT', '8765'))
BACKEND_BASE = os.environ.get('OPENCLAW_BASE_URL', 'http://127.0.0.1:18789')
SHARED_TOKEN = os.environ.get('MINIAPP_SHARED_TOKEN') or os.environ.get('OPENCLAW_GATEWAY_TOKEN') or os.environ.get('OPENCLAW_GATEWAY_PASSWORD')
BACKEND_BEARER = os.environ.get('OPENCLAW_GATEWAY_TOKEN') or os.environ.get('OPENCLAW_GATEWAY_PASSWORD') or ''
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_BOT_TOKENS = [t for t in (os.environ.get('TELEGRAM_BOT_TOKENS', '').splitlines()) if t.strip()]
TELEGRAM_OWNER_IDS = {
    s.strip() for s in (os.environ.get('TELEGRAM_OWNER_ID', '') + ',' + os.environ.get('TELEGRAM_OWNER_IDS', '')).split(',') if s.strip()
}
INITDATA_MAX_AGE_SECONDS = int(os.environ.get('MINIAPP_INITDATA_MAX_AGE_SECONDS', '86400'))
PUBLIC_ORIGIN = (os.environ.get('MINIAPP_PUBLIC_ORIGIN') or '').strip()
AUTH_DEBUG = os.environ.get('MINIAPP_AUTH_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
DEFAULT_AGENT = os.environ.get('OPENCLAW_AGENT_ID', 'main')
DEFAULT_CHANNEL = os.environ.get('OPENCLAW_MESSAGE_CHANNEL', 'telegram')

COMMANDS = [
    {'name': 'help', 'description': '미니앱에서 지원하는 명령 보기', 'category': 'core'},
    {'name': 'commands', 'description': '이 브리지에서 지원하는 명령 목록 보기', 'category': 'core'},
    {'name': 'status', 'description': 'OpenClaw 실행 상태 요약 보기', 'category': 'runtime'},
    {'name': 'model', 'description': '현재 기본 모델 정보 보기', 'category': 'runtime'},
    {'name': 'cron list', 'description': '크론 작업 목록 보기', 'category': 'cron'},
    {'name': 'cron run <id>', 'description': '크론 작업을 즉시 실행', 'category': 'cron'},
]


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    apply_cors(handler)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Cache-Control', 'no-store')
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler, status, text):
    body = text.encode('utf-8')
    handler.send_response(status)
    apply_cors(handler)
    handler.send_header('Content-Type', 'text/plain; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def now_iso_from_ms(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def run_cli(args, expect_json=False):
    cmd = ['openclaw', *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or 'command failed').strip())
    out = (proc.stdout or '').strip()
    if expect_json:
        return json.loads(out or '{}')
    return out


def summarize_status(status):
    gateway = status.get('gateway', {})
    service = status.get('gatewayService', {})
    tasks = status.get('tasks', {})
    recent = (status.get('sessions') or {}).get('recent') or []
    model = recent[0].get('model') if recent else None
    lines = [
        f"OpenClaw {status.get('runtimeVersion', '?')}",
        f"Gateway: {'reachable' if gateway.get('reachable') else 'unreachable'} ({gateway.get('url', '?')})",
        f"Service: {service.get('runtimeShort', 'unknown')}",
        f"Tasks: active {tasks.get('active', 0)}, failures {tasks.get('failures', 0)}",
    ]
    if model:
        lines.append(f"Recent model: {model}")
    return '\n'.join(lines)


def get_status_json():
    return run_cli(['status', '--json'], expect_json=True)


def get_model_info():
    status = get_status_json()
    recent = ((status.get('sessions') or {}).get('recent') or [])
    for item in recent:
        if item.get('agentId') == DEFAULT_AGENT:
            model = item.get('model') or 'openclaw/default'
            return {
                'model': model,
                'model_short': model,
                'provider': 'gateway',
                'context_length': item.get('contextTokens'),
            }
    return {
        'model': 'openclaw/default',
        'model_short': 'openclaw/default',
        'provider': 'gateway',
        'context_length': None,
    }


def get_session_usage(session_id=None):
    status = get_status_json()
    recent = ((status.get('sessions') or {}).get('recent') or [])
    target = None
    if session_id:
        for item in recent:
            if item.get('sessionId') == session_id:
                target = item
                break
    if target is None and recent:
        target = recent[0]
    if target is None:
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    return {
        'prompt_tokens': target.get('inputTokens', 0),
        'completion_tokens': target.get('outputTokens', 0),
        'total_tokens': target.get('totalTokens', 0),
        'session_id': target.get('sessionId'),
        'percent_used': target.get('percentUsed'),
    }


def schedule_display(job):
    sched = job.get('schedule') or {}
    kind = sched.get('kind')
    if kind == 'cron':
        return sched.get('expr', '')
    if kind == 'every':
        ms = sched.get('everyMs') or 0
        if ms % 3600000 == 0:
            return f"every {ms // 3600000}h"
        if ms % 60000 == 0:
            return f"every {ms // 60000}m"
        return f"every {ms}ms"
    if kind == 'at':
        return sched.get('at', '')
    return ''


def transform_job(job):
    state = job.get('state') or {}
    payload = job.get('payload') or {}
    schedule = job.get('schedule') or {}
    return {
        'id': job.get('id'),
        'name': job.get('name') or job.get('id'),
        'enabled': job.get('enabled', True),
        'state': 'paused' if not job.get('enabled', True) else 'running',
        'next_run_at': now_iso_from_ms(state.get('nextRunAtMs')),
        'last_run_at': now_iso_from_ms(state.get('lastRunAtMs')),
        'last_status': state.get('lastStatus') or state.get('lastRunStatus') or '',
        'schedule': schedule.get('expr') or schedule.get('at') or schedule.get('everyMs'),
        'schedule_display': schedule_display(job),
        'prompt': payload.get('message') or payload.get('text') or '',
        'delivery': job.get('delivery') or {},
        'raw': job,
    }


def list_jobs():
    data = run_cli(['cron', 'list', '--json'], expect_json=True)
    jobs = [transform_job(j) for j in data.get('jobs', [])]
    return {'jobs': jobs}


def get_job(job_id):
    jobs = list_jobs()['jobs']
    for job in jobs:
        if job['id'] == job_id:
            return {'job': job}
    raise RuntimeError(f'cron job not found: {job_id}')


def schedule_args(schedule_value):
    s = (schedule_value or '').strip()
    if not s:
        raise RuntimeError('schedule is required')
    if s.startswith('+'):
        return ['--at', s]
    if re.fullmatch(r'\d+[smhd]', s):
        return ['--every', s]
    if len(s.split()) in (5, 6):
        return ['--cron', s]
    raise RuntimeError(f'unsupported schedule format: {s}')


def create_job(body):
    args = ['cron', 'add', '--name', body['name'], '--agent', DEFAULT_AGENT, '--session', 'isolated', '--json']
    args += schedule_args(body.get('schedule'))
    prompt = body.get('prompt') or body.get('message')
    if prompt:
        args += ['--message', prompt]
    if body.get('announce'):
        args += ['--announce']
        if body.get('channel'):
            args += ['--channel', body['channel']]
        if body.get('to'):
            args += ['--to', body['to']]
    else:
        args += ['--no-deliver']
    created = run_cli(args, expect_json=True)
    return created


def patch_job(job_id, body):
    args = ['cron', 'edit', job_id]
    if 'name' in body and body['name']:
        args += ['--name', body['name']]
    if 'schedule' in body and body['schedule']:
        args += schedule_args(body['schedule'])
    if 'prompt' in body and body['prompt']:
        args += ['--message', body['prompt']]
    if body.get('enabled') is True:
        args += ['--enable']
    if body.get('enabled') is False:
        args += ['--disable']
    if body.get('announce'):
        args += ['--announce']
    elif body.get('announce') is False:
        args += ['--no-deliver']
    run_cli(args, expect_json=False)
    return {'ok': True, 'job': get_job(job_id)['job']}


def delete_job(job_id):
    run_cli(['cron', 'rm', job_id, '--json'], expect_json=False)
    return {'ok': True}


def cron_action(job_id, action):
    if action == 'run':
        run_cli(['cron', 'run', job_id], expect_json=False)
    elif action == 'pause':
        run_cli(['cron', 'disable', job_id], expect_json=False)
    elif action == 'resume':
        run_cli(['cron', 'enable', job_id], expect_json=False)
    else:
        raise RuntimeError(f'unknown action: {action}')
    return {'ok': True}


def commands_payload():
    return {
        'commands': [
            {
                'name': item['name'],
                'description': item['description'],
                'category': item['category'],
                'icon': '⌘',
                'args': '',
            }
            for item in COMMANDS
        ]
    }


def command_output(command, args):
    full = (command or '').strip()
    if args:
        full = f"{full} {args}".strip()
    if full in ('/help', 'help'):
        return '지원하는 브리지 명령:\n' + '\n'.join(f"- /{c['name']} — {c['description']}" for c in COMMANDS)
    if full in ('/commands', 'commands'):
        return json.dumps(commands_payload(), ensure_ascii=False, indent=2)
    if full in ('/status', 'status'):
        return summarize_status(get_status_json())
    if full in ('/model', 'model'):
        return json.dumps(get_model_info(), ensure_ascii=False, indent=2)
    if full in ('/cron list', 'cron list'):
        return json.dumps(list_jobs(), ensure_ascii=False, indent=2)
    if full.startswith('/cron run ') or full.startswith('cron run '):
        job_id = full.split()[-1]
        cron_action(job_id, 'run')
        return f'크론 작업을 실행했어요: {job_id}'
    return f'OpenClaw 브리지에서 아직 지원하지 않는 명령입니다: {full}'


def _allowed_origins(handler):
    origins = {
        f'http://127.0.0.1:{PORT}',
        f'http://localhost:{PORT}',
    }
    if PUBLIC_ORIGIN:
        origins.add(PUBLIC_ORIGIN)
    host = (handler.headers.get('Host') or '').strip()
    if host:
        origins.add(f'https://{host}')
        origins.add(f'http://{host}')
    return origins


def apply_cors(handler):
    origin = (handler.headers.get('Origin') or '').strip()
    if origin and origin in _allowed_origins(handler):
        handler.send_header('Access-Control-Allow-Origin', origin)
        handler.send_header('Vary', 'Origin')
        handler.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-Telegram-Init-Data, x-openclaw-session-id, x-openclaw-message-channel')
        handler.send_header('Access-Control-Allow-Methods', 'GET,POST,PATCH,DELETE,OPTIONS')


def _candidate_bot_tokens():
    seen = []
    for token in [TELEGRAM_BOT_TOKEN, *TELEGRAM_BOT_TOKENS]:
        token = (token or '').strip()
        if token and token not in seen:
            seen.append(token)
    return seen


def validate_telegram_init_data(init_data):
    if not init_data:
        return False
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
        data = dict(pairs)
        their_hash = data.pop('hash', '')
        if not their_hash:
            return False
        auth_date = int(data.get('auth_date', '0'))
        now = int(time.time())
        if not auth_date or auth_date > now + 60:
            return False
        if INITDATA_MAX_AGE_SECONDS > 0 and now - auth_date > INITDATA_MAX_AGE_SECONDS:
            return False
        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
        hash_ok = False
        for bot_token in _candidate_bot_tokens():
            secret_key = hmac.new(b'WebAppData', bot_token.encode('utf-8'), hashlib.sha256).digest()
            calc_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
            if hmac.compare_digest(calc_hash, their_hash):
                hash_ok = True
                break
        if not hash_ok:
            return False
        if TELEGRAM_OWNER_IDS:
            user_raw = data.get('user', '')
            if not user_raw:
                return False
            user = json.loads(user_raw)
            user_id = str(user.get('id', '')).strip()
            if not user_id or user_id not in TELEGRAM_OWNER_IDS:
                return False
        return True
    except Exception:
        return False


def auth_ok(handler):
    tg_init = (handler.headers.get('X-Telegram-Init-Data') or '').strip()
    auth = handler.headers.get('Authorization', '')
    if tg_init:
        ok = validate_telegram_init_data(tg_init)
        if not ok and AUTH_DEBUG:
            print(f"auth reject: invalid telegram initData origin={(handler.headers.get('Origin') or '')!r} has_bearer={auth.startswith('Bearer ')} init_len={len(tg_init)} ua={(handler.headers.get('User-Agent') or '')[:120]!r}", file=sys.stderr)
        return ok
    if not SHARED_TOKEN:
        if AUTH_DEBUG:
            print(f"auth reject: no telegram initData and no shared token origin={(handler.headers.get('Origin') or '')!r} has_bearer={auth.startswith('Bearer ')} ua={(handler.headers.get('User-Agent') or '')[:120]!r}", file=sys.stderr)
        return False
    if auth.startswith('Bearer ') and auth.removeprefix('Bearer ').strip() == SHARED_TOKEN:
        return True
    if AUTH_DEBUG:
        print(f"auth reject: bearer mismatch or missing origin={(handler.headers.get('Origin') or '')!r} has_bearer={auth.startswith('Bearer ')} ua={(handler.headers.get('User-Agent') or '')[:120]!r}", file=sys.stderr)
    return False


def backend_conn():
    parsed = urlparse(BACKEND_BASE)
    conn_cls = HTTPSConnection if parsed.scheme == 'https' else HTTPConnection
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    return conn_cls(parsed.hostname, port, timeout=120), parsed


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_OPTIONS(self):
        self.send_response(204)
        apply_cors(self)
        self.end_headers()

    def handle_exception(self, error):
        if isinstance(error, RuntimeError) and str(error) == 'Unauthorized':
            return json_response(self, 401, {'error': {'message': 'Unauthorized'}})
        return json_response(self, 500, {'error': {'message': str(error)}})

    def do_GET(self):
        try:
            if self.path in ('/', '/index.html'):
                return self.serve_file(INDEX_HTML)
            if self.path.startswith('/docs'):
                return self.serve_docs()
            if self.path == '/health':
                return self.proxy_simple('GET', '/health', auth_required=False)
            if self.path == '/api/commands':
                self.require_auth()
                return json_response(self, 200, commands_payload())
            if self.path == '/api/model-info':
                self.require_auth()
                return json_response(self, 200, get_model_info())
            if self.path.startswith('/api/session-usage'):
                self.require_auth()
                session_id = self.headers.get('x-openclaw-session-id')
                return json_response(self, 200, get_session_usage(session_id))
            if self.path == '/api/jobs':
                self.require_auth()
                return json_response(self, 200, list_jobs())
            if self.path.startswith('/api/jobs/'):
                self.require_auth()
                job_id = self.path.split('/')[3]
                return json_response(self, 200, get_job(job_id))
            return text_response(self, 404, 'not found')
        except Exception as e:
            return self.handle_exception(e)

    def do_POST(self):
        try:
            if self.path == '/v1/chat/completions':
                self.require_auth()
                return self.proxy_stream()
            self.require_auth()
            body = self.read_json()
            if self.path == '/api/command':
                output = command_output(body.get('command'), body.get('args'))
                return json_response(self, 200, {'output': output})
            if self.path == '/api/jobs':
                created = create_job(body)
                return json_response(self, 200, created)
            if self.path.startswith('/api/jobs/') and self.path.endswith('/run'):
                job_id = self.path.split('/')[3]
                return json_response(self, 200, cron_action(job_id, 'run'))
            if self.path.startswith('/api/jobs/') and self.path.endswith('/pause'):
                job_id = self.path.split('/')[3]
                return json_response(self, 200, cron_action(job_id, 'pause'))
            if self.path.startswith('/api/jobs/') and self.path.endswith('/resume'):
                job_id = self.path.split('/')[3]
                return json_response(self, 200, cron_action(job_id, 'resume'))
            return text_response(self, 404, 'not found')
        except Exception as e:
            return self.handle_exception(e)

    def do_PATCH(self):
        try:
            self.require_auth()
            if self.path.startswith('/api/jobs/'):
                body = self.read_json()
                job_id = self.path.split('/')[3]
                return json_response(self, 200, patch_job(job_id, body))
            return text_response(self, 404, 'not found')
        except Exception as e:
            return self.handle_exception(e)

    def do_DELETE(self):
        try:
            self.require_auth()
            if self.path.startswith('/api/jobs/'):
                job_id = self.path.split('/')[3]
                return json_response(self, 200, delete_job(job_id))
            return text_response(self, 404, 'not found')
        except Exception as e:
            return self.handle_exception(e)

    def require_auth(self):
        if not auth_ok(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except Exception:
                length = 0
            if length > 0:
                try:
                    self.rfile.read(length)
                except Exception:
                    pass
            raise RuntimeError('Unauthorized')

    def read_json(self):
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length) if length else b'{}'
        return json.loads(raw.decode('utf-8') or '{}')

    def serve_file(self, path: Path):
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or 'text/html'
        self.send_response(200)
        apply_cors(self)
        self.send_header('Content-Type', f'{ctype}; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_docs(self):
        rel = self.path[len('/docs'):].lstrip('/') or 'index.html'
        path = DOCS_DIR / rel
        if not path.exists() or not path.is_file():
            return text_response(self, 404, 'not found')
        return self.serve_file(path)

    def proxy_simple(self, method, path, auth_required=True):
        conn, parsed = backend_conn()
        headers = {}
        if BACKEND_BEARER:
            headers['Authorization'] = f'Bearer {BACKEND_BEARER}'
        conn.request(method, path, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        self.send_response(resp.status)
        apply_cors(self)
        self.send_header('Content-Type', resp.getheader('Content-Type', 'application/json'))
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def proxy_stream(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length) if length else b''
        conn, parsed = backend_conn()
        headers = {
            'Content-Type': 'application/json',
        }
        if BACKEND_BEARER:
            headers['Authorization'] = f'Bearer {BACKEND_BEARER}'
        for key in ('x-openclaw-session-id', 'x-openclaw-message-channel', 'x-openclaw-model', 'x-openclaw-agent-id'):
            if self.headers.get(key):
                headers[key] = self.headers.get(key)
        conn.request('POST', '/v1/chat/completions', body=body, headers=headers)
        resp = conn.getresponse()
        if resp.status == 404:
            data = {
                'error': {
                    'message': 'OpenClaw gateway HTTP chat endpoint is not enabled. Set gateway.http.endpoints.chatCompletions.enabled=true in openclaw.json.',
                }
            }
            return json_response(self, 404, data)
        self.send_response(resp.status)
        apply_cors(self)
        self.send_header('Content-Type', resp.getheader('Content-Type', 'text/event-stream'))
        if resp.getheader('x-openclaw-session-id'):
            self.send_header('x-openclaw-session-id', resp.getheader('x-openclaw-session-id'))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()


if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'OpenClaw mini app bridge on http://{HOST}:{PORT} -> {BACKEND_BASE}', file=sys.stderr)
    server.serve_forever()
