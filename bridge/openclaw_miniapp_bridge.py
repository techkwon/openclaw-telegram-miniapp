#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import shlex
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    CRYPTOGRAPHY_AVAILABLE = True
except Exception:
    InvalidSignature = Exception
    Ed25519PublicKey = None
    CRYPTOGRAPHY_AVAILABLE = False

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
RATE_LIMIT_WINDOW_SECONDS = max(1, int(os.environ.get('MINIAPP_RATE_LIMIT_WINDOW_SECONDS', '60')))
RATE_LIMIT_MAX_REQUESTS = max(10, int(os.environ.get('MINIAPP_RATE_LIMIT_MAX_REQUESTS', '180')))
RATE_LIMIT_ACTION_MAX_REQUESTS = max(3, int(os.environ.get('MINIAPP_RATE_LIMIT_ACTION_MAX_REQUESTS', '12')))
BROWSER_SESSION_TTL_SECONDS = max(300, int(os.environ.get('MINIAPP_BROWSER_SESSION_TTL_SECONDS', '1800')))
DEFAULT_AGENT = os.environ.get('OPENCLAW_AGENT_ID', 'main')
DEFAULT_CHANNEL = os.environ.get('OPENCLAW_MESSAGE_CHANNEL', 'telegram')
TELEGRAM_ED25519_PUBLIC_KEY_PROD = bytes.fromhex('e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d')
BRIDGE_LOG_PATH = Path(os.environ.get('MINIAPP_BRIDGE_LOG_PATH') or str(Path.home() / '.openclaw' / 'logs' / 'openclaw-miniapp-bridge.log'))
BRIDGE_ERR_LOG_PATH = Path(os.environ.get('MINIAPP_BRIDGE_ERR_LOG_PATH') or str(Path.home() / '.openclaw' / 'logs' / 'openclaw-miniapp-bridge.err.log'))
CLOUDFLARED_OUT_LOG_PATH = Path(os.environ.get('MINIAPP_CLOUDFLARED_OUT_LOG_PATH') or str(Path.home() / 'Library' / 'Logs' / 'com.cloudflare.cloudflared.out.log'))
CLOUDFLARED_ERR_LOG_PATH = Path(os.environ.get('MINIAPP_CLOUDFLARED_ERR_LOG_PATH') or str(Path.home() / 'Library' / 'Logs' / 'com.cloudflare.cloudflared.err.log'))
RATE_LIMITS = defaultdict(lambda: deque())
BROWSER_SESSIONS = {}

COMMANDS = [
    {'name': 'help', 'description': '미니앱에서 지원하는 명령 보기', 'category': 'core'},
    {'name': 'commands', 'description': '이 브리지에서 지원하는 명령 목록 보기', 'category': 'core'},
    {'name': 'status', 'description': 'OpenClaw 실행 상태 요약 보기', 'category': 'runtime'},
    {'name': 'runtime', 'description': '런타임 상태 JSON 보기', 'category': 'runtime'},
    {'name': 'model', 'description': '현재 기본 모델 정보 보기', 'category': 'runtime'},
    {'name': 'usage', 'description': '현재 세션 토큰 사용량 보기', 'category': 'runtime'},
    {'name': 'processes', 'description': '최근 세션/프로세스 보기', 'category': 'runtime'},
    {'name': 'sessions list', 'description': '최근 세션 목록 보기', 'category': 'sessions'},
    {'name': 'session status <target>', 'description': '특정 세션 상태 카드 보기', 'category': 'sessions'},
    {'name': 'session summary <target>', 'description': '특정 세션 요약 보기', 'category': 'sessions'},
    {'name': 'session history <target> [limit]', 'description': '특정 세션 최근 기록 보기', 'category': 'sessions'},
    {'name': 'session send <target> <message>', 'description': '특정 세션에 메시지 보내기', 'category': 'sessions'},
    {'name': 'session new <message>', 'description': '새 explicit 세션 생성', 'category': 'sessions'},
    {'name': 'subagents list', 'description': '현재 세션의 subagent 목록 보기', 'category': 'agents'},
    {'name': 'subagents kill <target>', 'description': 'subagent 종료', 'category': 'agents'},
    {'name': 'subagents steer <target> <message>', 'description': 'subagent에 추가 지시 보내기', 'category': 'agents'},
    {'name': 'cron list', 'description': '크론 작업 목록 보기', 'category': 'cron'},
    {'name': 'cron run <id>', 'description': '크론 작업을 즉시 실행', 'category': 'cron'},
    {'name': 'cron pause <id>', 'description': '크론 작업 일시중지', 'category': 'cron'},
    {'name': 'cron resume <id>', 'description': '크론 작업 재개', 'category': 'cron'},
    {'name': 'cron show <id>', 'description': '크론 작업 상세 보기', 'category': 'cron'},
    {'name': 'tunnel status', 'description': 'Cloudflare tunnel 상태 요약 보기', 'category': 'ops'},
    {'name': 'tunnel probe', 'description': 'public origin health probe 다시 확인', 'category': 'ops'},
    {'name': 'tunnel logs [lines]', 'description': 'cloudflared 최근 로그 보기', 'category': 'ops'},
    {'name': 'tunnel doctor', 'description': 'tunnel 문제 자동 진단', 'category': 'ops'},
    {'name': 'logs bridge [lines]', 'description': 'bridge 최근 로그 보기', 'category': 'ops'},
    {'name': 'logs tunnel [lines]', 'description': 'cloudflared 최근 로그 보기', 'category': 'ops'},
]

ACTION_RUNNERS = {
    'restart_bridge': {
        'label': '브리지 재시작',
        'command': ['launchctl', 'kickstart', '-k', f'gui/{os.getuid()}/ai.openclaw.miniapp-bridge'],
        'success': '브리지 재시작을 요청했어요.',
    },
    'restart_gateway': {
        'label': '게이트웨이 재시작',
        'command': ['openclaw', 'gateway', 'restart'],
        'success': 'OpenClaw 게이트웨이 재시작을 요청했어요.',
    },
}


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


def get_processes(status=None):
    status = status or get_status_json()
    recent = ((status.get('sessions') or {}).get('recent') or [])
    tasks = (status.get('tasks') or {})
    processes = []
    for item in recent[:8]:
        processes.append({
            'name': item.get('agentId') or item.get('key') or 'session',
            'pid': item.get('sessionId'),
            'running': True,
            'cpu': None,
            'mem': None,
            'model': item.get('model'),
            'kind': item.get('kind'),
            'age_ms': item.get('age'),
            'tokens': item.get('totalTokens'),
        })
    return {
        'processes': processes,
        'summary': {
            'active_tasks': tasks.get('active', 0),
            'failures': tasks.get('failures', 0),
            'session_count': (status.get('sessions') or {}).get('count', 0),
        }
    }


def get_runtime_status():
    status = get_status_json()
    gateway = status.get('gateway') or {}
    service = status.get('gatewayService') or {}
    tasks = status.get('tasks') or {}
    sessions = status.get('sessions') or {}
    heartbeat = status.get('heartbeat') or {}
    recent = sessions.get('recent') or []
    return {
        'runtime_version': status.get('runtimeVersion'),
        'gateway': {
            'reachable': gateway.get('reachable'),
            'url': gateway.get('url'),
            'service': service.get('runtimeShort') or service.get('status') or 'unknown',
        },
        'tasks': tasks,
        'heartbeat': {
            'default_agent_id': heartbeat.get('defaultAgentId'),
            'agents': heartbeat.get('agents') or [],
        },
        'channels': status.get('channelSummary') or [],
        'sessions': {
            'count': sessions.get('count', 0),
            'recent': [
                {
                    'agent_id': item.get('agentId'),
                    'kind': item.get('kind'),
                    'session_id': item.get('sessionId'),
                    'model': item.get('model'),
                    'context_tokens': item.get('contextTokens'),
                    'total_tokens': item.get('totalTokens'),
                    'percent_used': item.get('percentUsed'),
                    'age_ms': item.get('age'),
                    'key': item.get('key'),
                }
                for item in recent[:8]
            ],
        },
        'processes': get_processes(status).get('processes', []),
    }


def _cloudflared_launch_status():
    try:
        uid = os.getuid()
        proc = subprocess.run(['launchctl', 'print', f'gui/{uid}/com.cloudflare.cloudflared'], capture_output=True, text=True)
        text = (proc.stdout or proc.stderr or '')
        running = proc.returncode == 0 and 'state = running' in text
    except Exception:
        running = False
    try:
        proc2 = subprocess.run(['pgrep', '-fl', 'cloudflared tunnel run --token'], capture_output=True, text=True)
        matches = [line for line in (proc2.stdout or '').splitlines() if line.strip()]
    except Exception:
        matches = []
    return {
        'launch_agent_running': running,
        'matching_processes': len(matches),
    }


def _external_public_probe():
    if not PUBLIC_ORIGIN:
        return {'configured': False, 'reachable': None, 'status': None, 'detail': 'public origin not configured'}
    try:
        parsed = urlparse(PUBLIC_ORIGIN)
        conn_cls = HTTPSConnection if parsed.scheme == 'https' else HTTPConnection
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        path = (parsed.path.rstrip('/') or '') + '/health'
        conn = conn_cls(parsed.hostname, port, timeout=8)
        conn.request('GET', path, headers={'User-Agent': 'OpenClawMiniAppBridge/1.0'})
        resp = conn.getresponse()
        body = resp.read(160).decode('utf-8', errors='replace').strip()
        reachable = resp.status < 400
        return {
            'configured': True,
            'reachable': reachable,
            'status': resp.status,
            'detail': body[:160],
        }
    except Exception as e:
        return {
            'configured': True,
            'reachable': False,
            'status': None,
            'detail': str(e),
        }


def _tail_text_file(path, lines=40):
    path = Path(path)
    if not path.exists():
        return f'로그 파일이 없어요: {path}'
    try:
        content = path.read_text(errors='replace').splitlines()
        tail = content[-max(1, min(lines, 200)):]
        return '\n'.join(tail) if tail else '(로그 없음)'
    except Exception as e:
        return f'로그를 읽지 못했어요: {e}'


def _parse_tail_lines(text, default=40):
    text = (text or '').strip()
    if not text:
        return default
    try:
        value = int(text)
        return max(5, min(value, 200))
    except Exception:
        return default


def get_system_diagnostics():
    runtime = get_runtime_status()
    return {
        'bridge': {
            'host': HOST,
            'port': PORT,
            'public_origin': PUBLIC_ORIGIN,
            'public_origin_configured': bool(PUBLIC_ORIGIN),
            'backend_base': BACKEND_BASE,
        },
        'auth': {
            'telegram_owner_ids_configured': bool(TELEGRAM_OWNER_IDS),
            'telegram_bot_token_configured': bool(TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKENS),
            'shared_token_configured': bool(SHARED_TOKEN),
            'ed25519_available': CRYPTOGRAPHY_AVAILABLE,
            'initdata_max_age_seconds': INITDATA_MAX_AGE_SECONDS,
        },
        'gateway': runtime.get('gateway') or {},
        'tasks': runtime.get('tasks') or {},
        'sessions': {
            'count': (runtime.get('sessions') or {}).get('count', 0),
        },
        'cloudflared': _cloudflared_launch_status(),
        'external_probe': _external_public_probe(),
        'logs': {
            'bridge_out': str(BRIDGE_LOG_PATH),
            'bridge_err': str(BRIDGE_ERR_LOG_PATH),
            'cloudflared_out': str(CLOUDFLARED_OUT_LOG_PATH),
            'cloudflared_err': str(CLOUDFLARED_ERR_LOG_PATH),
        },
    }


def _tool_text_json(result, fallback_key=None):
    details = (result.get('result') or {}).get('details')
    if isinstance(details, dict) and details:
        return details
    content = (result.get('result') or {}).get('content') or []
    for item in content:
        if item.get('type') == 'text' and item.get('text'):
            try:
                return json.loads(item['text'])
            except Exception:
                pass
    return {fallback_key: content} if fallback_key else {}


def list_sessions(limit=20, active_minutes=None, message_limit=0):
    args = {'limit': limit}
    if active_minutes is not None:
        args['activeMinutes'] = active_minutes
    if message_limit:
        args['messageLimit'] = message_limit
    result = invoke_gateway_tool('sessions_list', args=args, message_channel=DEFAULT_CHANNEL)
    return _tool_text_json(result, fallback_key='sessions')


def resolve_session_target(target):
    target = (target or '').strip()
    if not target:
        raise RuntimeError('session target is required')
    if ':' in target:
        sessions = list_sessions(limit=100).get('sessions') or []
        for item in sessions:
            if item.get('key') == target:
                return item.get('sessionId') or target, item.get('key') or target
        return target, target
    return target, target


def get_session_status_text(target):
    session_id, session_key = resolve_session_target(target)
    result = invoke_gateway_tool('session_status', args={'sessionKey': session_key}, message_channel=DEFAULT_CHANNEL)
    details = (result.get('result') or {}).get('details') or {}
    return details.get('statusText') or json.dumps(details, ensure_ascii=False, indent=2)


def get_session_summary(target):
    session_id, session_key = resolve_session_target(target)
    sessions = list_sessions(limit=100).get('sessions') or []
    found = None
    for item in sessions:
        if item.get('key') == session_key or item.get('sessionId') == session_id:
            found = item
            break
    if not found:
        return {
            'sessionKey': session_key,
            'sessionId': session_id,
            'summary': '세션을 찾지 못했어요.',
        }
    parts = [
        f"세션: {found.get('key') or session_key}",
        f"상태: {found.get('status') or found.get('kind') or 'unknown'}",
        f"모델: {found.get('model') or '—'}",
    ]
    if found.get('totalTokens') is not None:
        parts.append(f"토큰: {found.get('totalTokens')} total")
    if found.get('contextTokens') is not None:
        parts.append(f"컨텍스트: {found.get('contextTokens')}")
    if found.get('updatedAt'):
        parts.append(f"업데이트: {now_iso_from_ms(found.get('updatedAt'))}")
    child_sessions = found.get('childSessions') or []
    if child_sessions:
        parts.append(f"하위 세션: {len(child_sessions)}개")
    return {
        'sessionKey': found.get('key') or session_key,
        'sessionId': found.get('sessionId') or session_id,
        'model': found.get('model'),
        'status': found.get('status') or found.get('kind'),
        'totalTokens': found.get('totalTokens'),
        'contextTokens': found.get('contextTokens'),
        'updatedAt': found.get('updatedAt'),
        'childSessions': child_sessions,
        'summary': '\n'.join(parts),
    }


def get_session_history(target, limit=10, include_tools=False):
    session_id, session_key = resolve_session_target(target)
    result = invoke_gateway_tool(
        'sessions_history',
        args={'sessionKey': session_key, 'limit': limit, 'includeTools': include_tools},
        message_channel=DEFAULT_CHANNEL,
    )
    return _tool_text_json(result, fallback_key='messages')


def session_send(target, message, timeout_seconds=45):
    session_id, session_key = resolve_session_target(target)
    cmd = [
        'openclaw', 'agent', '--session-id', session_id,
        '--message', message,
        '--json', '--timeout', str(timeout_seconds),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or 'session send failed').strip())
    data = json.loads((proc.stdout or '{}').strip() or '{}')
    payloads = (((data.get('result') or {}).get('payloads') or []))
    texts = [p.get('text') for p in payloads if p.get('text')]
    return {
        'ok': data.get('status') == 'ok',
        'session_id': (((data.get('result') or {}).get('meta') or {}).get('agentMeta') or {}).get('sessionId') or session_id,
        'session_key': ((((data.get('result') or {}).get('meta') or {}).get('systemPromptReport') or {}).get('sessionKey')) or session_key,
        'run_id': data.get('runId'),
        'reply': '\n\n'.join(texts).strip(),
        'raw': data,
    }


def session_new(message, timeout_seconds=45):
    explicit_id = str(uuid.uuid4())
    cmd = [
        'openclaw', 'agent', '--session-id', explicit_id,
        '--message', message,
        '--json', '--timeout', str(timeout_seconds),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or 'session create failed').strip())
    data = json.loads((proc.stdout or '{}').strip() or '{}')
    meta = ((data.get('result') or {}).get('meta') or {})
    payloads = ((data.get('result') or {}).get('payloads') or [])
    texts = [p.get('text') for p in payloads if p.get('text')]
    return {
        'ok': data.get('status') == 'ok',
        'requested_session_id': explicit_id,
        'session_id': (meta.get('agentMeta') or {}).get('sessionId') or explicit_id,
        'session_key': (meta.get('systemPromptReport') or {}).get('sessionKey') or explicit_id,
        'run_id': data.get('runId'),
        'reply': '\n\n'.join(texts).strip(),
        'raw': data,
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


def _tunnel_status_payload():
    diag = get_system_diagnostics()
    return {
        'public_origin': (diag.get('bridge') or {}).get('public_origin'),
        'cloudflared': diag.get('cloudflared') or {},
        'external_probe': diag.get('external_probe') or {},
        'gateway': diag.get('gateway') or {},
    }


def _tunnel_doctor_text():
    diag = get_system_diagnostics()
    cloud = diag.get('cloudflared') or {}
    probe = diag.get('external_probe') or {}
    gateway = diag.get('gateway') or {}
    lines = []
    if not cloud.get('launch_agent_running'):
        lines.append('판단: cloudflared LaunchAgent가 꺼져 있어요.')
        lines.append('다음 확인: launchctl print gui/$(id -u)/com.cloudflare.cloudflared')
    elif (cloud.get('matching_processes') or 0) > 1:
        lines.append('판단: cloudflared tunnel 프로세스가 중복 실행 중이에요.')
        lines.append('다음 확인: 수동 실행본을 정리하고 LaunchAgent 1개만 남기세요.')
    elif probe.get('configured') and probe.get('reachable') is False:
        detail = str(probe.get('detail') or '')
        status = probe.get('status')
        if '1010' in detail:
            lines.append('판단: Cloudflare WAF/보안 규칙 차단 가능성이 높아요. (1010)')
            lines.append('다음 확인: Cloudflare Security Events / WAF 규칙')
        elif '1033' in detail or status == 530:
            lines.append('판단: tunnel connector 또는 Public Hostname 연결 문제가 커 보여요. (1033/530)')
            lines.append('다음 확인: Zero Trust Tunnel의 Public Hostname과 활성 connector 매핑')
        else:
            lines.append('판단: 외부 public origin 접속이 실패하고 있어요.')
            lines.append('다음 확인: /tunnel logs, /logs bridge, public /health 응답')
    elif gateway.get('reachable') is False:
        lines.append('판단: Mini App bridge는 살아 있지만 OpenClaw Gateway 연결이 불안정해요.')
        lines.append('다음 확인: /status, gateway 설정, gateway token/base url')
    else:
        lines.append('판단: 현재 tunnel/bridge/gateway 핵심 상태는 정상 쪽으로 보여요.')
        lines.append('다음 확인: Telegram 내부 initData 인증이나 실제 사용 흐름 E2E 확인')
    lines.append('')
    lines.append('요약 상태:')
    lines.append(json.dumps(_tunnel_status_payload(), ensure_ascii=False, indent=2))
    return '\n'.join(lines)


def run_named_action(action):
    spec = ACTION_RUNNERS.get((action or '').strip())
    if not spec:
        raise RuntimeError('지원하지 않는 액션입니다.')
    proc = subprocess.run(spec['command'], capture_output=True, text=True)
    output = (proc.stdout or proc.stderr or '').strip()
    if proc.returncode != 0:
        raise RuntimeError(output or f"{spec['label']} 실행에 실패했습니다.")
    return {
        'ok': True,
        'action': action,
        'label': spec['label'],
        'message': spec['success'],
        'output': output,
    }


def command_output(command, args):
    full = (command or '').strip()
    if args:
        full = f"{full} {args}".strip()
    normalized = full.lstrip('/')

    if normalized in ('help',):
        return '지원하는 브리지 명령:\n' + '\n'.join(f"- /{c['name']} — {c['description']}" for c in COMMANDS)
    if normalized in ('commands',):
        return json.dumps(commands_payload(), ensure_ascii=False, indent=2)
    if normalized in ('status',):
        return summarize_status(get_status_json())
    if normalized in ('gateway status deep', 'gateway deep', 'status deep'):
        return run_cli(['gateway', 'status', '--deep'])
    if normalized in ('runtime', 'runtime status'):
        return json.dumps(get_runtime_status(), ensure_ascii=False, indent=2)
    if normalized in ('model',):
        return json.dumps(get_model_info(), ensure_ascii=False, indent=2)
    if normalized in ('usage', 'session usage'):
        return json.dumps(get_session_usage(), ensure_ascii=False, indent=2)
    if normalized in ('processes', 'ps'):
        return json.dumps(get_processes(), ensure_ascii=False, indent=2)
    if normalized in ('sessions', 'sessions list'):
        return json.dumps(list_sessions(limit=20), ensure_ascii=False, indent=2)
    if normalized.startswith('session status '):
        target = normalized.split(maxsplit=2)[-1]
        return get_session_status_text(target)
    if normalized.startswith('session summary '):
        target = normalized.split(maxsplit=2)[-1]
        summary = get_session_summary(target)
        return summary.get('summary') or json.dumps(summary, ensure_ascii=False, indent=2)
    if normalized.startswith('session history '):
        rest = normalized[len('session history '):].strip()
        limit = 10
        parts = rest.rsplit(' ', 1)
        if len(parts) == 2 and parts[1].isdigit():
            target, limit = parts[0], int(parts[1])
        else:
            target = rest
        return json.dumps(get_session_history(target, limit=limit, include_tools=False), ensure_ascii=False, indent=2)
    if normalized.startswith('session send '):
        parts = normalized.split(maxsplit=3)
        if len(parts) < 4:
            return '사용법: /session send <target> <message>'
        _, _, target, message = parts
        result = session_send(target, message)
        reply = result.get('reply') or '(응답 없음)'
        return f"세션에 메시지 보냈어요: {result.get('session_key') or target}\n\n{reply}"
    if normalized.startswith('session new '):
        message = normalized[len('session new '):].strip()
        if not message:
            return '사용법: /session new <message>'
        result = session_new(message)
        reply = result.get('reply') or '(응답 없음)'
        return f"새 세션 생성: {result.get('session_key')}\n세션 ID: {result.get('session_id')}\n\n{reply}"
    if normalized in ('cron', 'cron list'):
        return json.dumps(list_jobs(), ensure_ascii=False, indent=2)
    if normalized.startswith('cron run '):
        job_id = normalized.split(maxsplit=2)[-1]
        cron_action(job_id, 'run')
        return f'크론 작업을 실행했어요: {job_id}'
    if normalized.startswith('cron pause '):
        job_id = normalized.split(maxsplit=2)[-1]
        cron_action(job_id, 'pause')
        return f'크론 작업을 일시중지했어요: {job_id}'
    if normalized.startswith('cron resume '):
        job_id = normalized.split(maxsplit=2)[-1]
        cron_action(job_id, 'resume')
        return f'크론 작업을 재개했어요: {job_id}'
    if normalized.startswith('cron show '):
        job_id = normalized.split(maxsplit=2)[-1]
        return json.dumps(get_job(job_id), ensure_ascii=False, indent=2)
    if normalized in ('tunnel', 'tunnel status'):
        return json.dumps(_tunnel_status_payload(), ensure_ascii=False, indent=2)
    if normalized in ('tunnel probe',):
        return json.dumps(_external_public_probe(), ensure_ascii=False, indent=2)
    if normalized.startswith('tunnel logs'):
        lines = _parse_tail_lines(normalized.replace('tunnel logs', '', 1).strip(), default=50)
        return _tail_text_file(CLOUDFLARED_ERR_LOG_PATH, lines=lines)
    if normalized in ('tunnel doctor',):
        return _tunnel_doctor_text()
    if normalized.startswith('logs bridge'):
        lines = _parse_tail_lines(normalized.replace('logs bridge', '', 1).strip(), default=50)
        return _tail_text_file(BRIDGE_ERR_LOG_PATH, lines=lines)
    if normalized.startswith('logs tunnel'):
        lines = _parse_tail_lines(normalized.replace('logs tunnel', '', 1).strip(), default=50)
        return _tail_text_file(CLOUDFLARED_ERR_LOG_PATH, lines=lines)
    if normalized in ('subagents', 'subagents list'):
        return json.dumps(get_subagents(), ensure_ascii=False, indent=2)
    if normalized.startswith('subagents kill '):
        target = normalized.split(maxsplit=2)[-1]
        result = subagent_action({'action': 'kill', 'target': target})
        return result.get('text') or json.dumps(result, ensure_ascii=False, indent=2)
    if normalized.startswith('subagents steer '):
        parts = normalized.split(maxsplit=3)
        if len(parts) < 4:
            return '사용법: /subagents steer <target> <message>'
        _, _, target, message = parts
        result = subagent_action({'action': 'steer', 'target': target, 'message': message})
        return result.get('text') or json.dumps(result, ensure_ascii=False, indent=2)
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


def _candidate_bot_ids():
    seen = []
    for token in _candidate_bot_tokens():
        bot_id = (token.split(':', 1)[0] or '').strip()
        if bot_id and bot_id not in seen:
            seen.append(bot_id)
    return seen


def _validate_telegram_init_data_ed25519(data):
    if not CRYPTOGRAPHY_AVAILABLE:
        return False
    signature = (data.get('signature') or '').strip()
    if not signature:
        return False
    lines = []
    for k, v in sorted(data.items()):
        if k in {'hash', 'signature'}:
            continue
        lines.append(f'{k}={v}')
    if not lines:
        return False
    try:
        padding = '=' * (-len(signature) % 4)
        sig_bytes = base64.urlsafe_b64decode(signature + padding)
    except Exception:
        return False
    public_key = Ed25519PublicKey.from_public_bytes(TELEGRAM_ED25519_PUBLIC_KEY_PROD)
    for bot_id in _candidate_bot_ids():
        data_check_string = f'{bot_id}:WebAppData\n' + '\n'.join(lines)
        try:
            public_key.verify(sig_bytes, data_check_string.encode('utf-8'))
            return True
        except InvalidSignature:
            continue
        except Exception:
            continue
    return False


def _validate_telegram_init_data_hmac(data):
    their_hash = data.get('hash', '')
    if not their_hash:
        return False
    body = {k: v for k, v in data.items() if k != 'hash'}
    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(body.items()))
    for bot_token in _candidate_bot_tokens():
        secret_key = hmac.new(b'WebAppData', bot_token.encode('utf-8'), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
        if hmac.compare_digest(calc_hash, their_hash):
            return True
    return False


def validate_telegram_init_data(init_data):
    if not init_data:
        return False
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
        data = dict(pairs)
        auth_date = int(data.get('auth_date', '0'))
        now = int(time.time())
        if not auth_date or auth_date > now + 60:
            return False
        if INITDATA_MAX_AGE_SECONDS > 0 and now - auth_date > INITDATA_MAX_AGE_SECONDS:
            return False
        if not (_validate_telegram_init_data_ed25519(data) or _validate_telegram_init_data_hmac(data)):
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


def _masked_origin(handler):
    origin = (handler.headers.get('Origin') or '').strip()
    if not origin:
        return ''
    parsed = urlparse(origin)
    host = parsed.netloc or parsed.path
    if not host:
        return ''
    return f'{parsed.scheme}://{host}' if parsed.scheme else host


def _masked_user_agent(handler):
    ua = (handler.headers.get('User-Agent') or '').strip()
    return ua[:64] + ('…' if len(ua) > 64 else '')


def _auth_debug_log(reason, handler, auth='', tg_init=''):
    if not AUTH_DEBUG:
        return
    print(
        f"auth reject: {reason} origin={_masked_origin(handler)!r} has_bearer={auth.startswith('Bearer ')} init_len={len(tg_init)} ua={_masked_user_agent(handler)!r}",
        file=sys.stderr,
    )


def _extract_bearer_token(handler):
    auth = handler.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth.removeprefix('Bearer ').strip()
    return ''


def _cleanup_browser_sessions(now=None):
    now = now or time.time()
    expired = [token for token, meta in BROWSER_SESSIONS.items() if (meta.get('expires_at') or 0) <= now]
    for token in expired:
        BROWSER_SESSIONS.pop(token, None)


def _issue_browser_session(subject='browser'):
    now = time.time()
    _cleanup_browser_sessions(now)
    token = 'miniapp_' + uuid.uuid4().hex + uuid.uuid4().hex
    expires_at = now + BROWSER_SESSION_TTL_SECONDS
    BROWSER_SESSIONS[token] = {
        'subject': subject,
        'issued_at': now,
        'expires_at': expires_at,
    }
    return {
        'token': token,
        'issued_at': int(now),
        'expires_at': int(expires_at),
        'ttl_seconds': BROWSER_SESSION_TTL_SECONDS,
    }


def _validate_browser_session(token):
    if not token:
        return False
    now = time.time()
    _cleanup_browser_sessions(now)
    meta = BROWSER_SESSIONS.get(token)
    if not meta:
        return False
    if (meta.get('expires_at') or 0) <= now:
        BROWSER_SESSIONS.pop(token, None)
        return False
    return True


def _rate_limit_key(handler):
    tg_init = (handler.headers.get('X-Telegram-Init-Data') or '').strip()
    if tg_init:
        try:
            data = dict(parse_qsl(tg_init, keep_blank_values=True, strict_parsing=False))
            user_raw = data.get('user', '')
            if user_raw:
                user = json.loads(user_raw)
                user_id = str(user.get('id', '')).strip()
                if user_id:
                    return 'tg:' + user_id
        except Exception:
            pass
    token = _extract_bearer_token(handler)
    if token:
        if _validate_browser_session(token):
            return 'session:' + hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]
        return 'bearer:' + hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]
    client_ip = getattr(handler, 'client_address', ['unknown'])[0]
    return 'ip:' + str(client_ip)


def _enforce_rate_limit(handler):
    key = _rate_limit_key(handler)
    window = RATE_LIMIT_WINDOW_SECONDS
    now = time.time()
    bucket = RATE_LIMITS[key]
    while bucket and bucket[0] < now - window:
        bucket.popleft()
    limit = RATE_LIMIT_ACTION_MAX_REQUESTS if self_path_is_action(handler.path) else RATE_LIMIT_MAX_REQUESTS
    if len(bucket) >= limit:
        raise RuntimeError('RateLimited')
    bucket.append(now)


def self_path_is_action(path):
    return str(path or '').startswith('/api/actions/run')


def auth_ok(handler):
    tg_init = (handler.headers.get('X-Telegram-Init-Data') or '').strip()
    auth = handler.headers.get('Authorization', '')
    bearer = _extract_bearer_token(handler)
    if tg_init:
        ok = validate_telegram_init_data(tg_init)
        if not ok:
            _auth_debug_log('invalid telegram initData', handler, auth=auth, tg_init=tg_init)
        return ok
    if bearer and _validate_browser_session(bearer):
        return True
    if not SHARED_TOKEN:
        _auth_debug_log('no telegram initData and no shared token', handler, auth=auth, tg_init=tg_init)
        return False
    if bearer and bearer == SHARED_TOKEN:
        return True
    _auth_debug_log('bearer mismatch or missing', handler, auth=auth, tg_init=tg_init)
    return False


def backend_conn():
    parsed = urlparse(BACKEND_BASE)
    conn_cls = HTTPSConnection if parsed.scheme == 'https' else HTTPConnection
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    return conn_cls(parsed.hostname, port, timeout=120), parsed


def backend_json(method, path, body=None, headers=None):
    conn, _parsed = backend_conn()
    payload = None
    req_headers = dict(headers or {})
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
        req_headers['Content-Type'] = 'application/json'
    if BACKEND_BEARER:
        req_headers['Authorization'] = f'Bearer {BACKEND_BEARER}'
    conn.request(method, path, body=payload, headers=req_headers)
    resp = conn.getresponse()
    data = resp.read()
    ctype = resp.getheader('Content-Type', '')
    if data and 'application/json' in ctype:
        parsed = json.loads(data.decode('utf-8'))
    elif data:
        parsed = {'raw': data.decode('utf-8', errors='replace')}
    else:
        parsed = {}
    if resp.status >= 400:
        message = parsed.get('error', {}).get('message') if isinstance(parsed.get('error'), dict) else None
        message = message or parsed.get('message') or parsed.get('error') or f'backend http {resp.status}'
        raise RuntimeError(str(message))
    return parsed


def resolve_requester_session_key(session_id=None, status=None):
    if not session_id:
        return None
    status = status or get_status_json()
    recent = ((status.get('sessions') or {}).get('recent') or [])
    for item in recent:
        if item.get('sessionId') == session_id:
            return item.get('key')
    return None


def invoke_gateway_tool(tool, args=None, action=None, session_key=None, message_channel=DEFAULT_CHANNEL):
    body = {
        'tool': tool,
        'args': args or {},
    }
    if action:
        body['action'] = action
    if session_key:
        body['sessionKey'] = session_key
    headers = {}
    if message_channel:
        headers['x-openclaw-message-channel'] = message_channel
    return backend_json('POST', '/tools/invoke', body=body, headers=headers)


def _subagent_view(entry, active=False):
    return {
        'index': entry.get('index'),
        'run_id': entry.get('runId'),
        'key': entry.get('sessionKey'),
        'session_id': entry.get('sessionId'),
        'label': entry.get('label'),
        'task': entry.get('task'),
        'status': entry.get('status'),
        'model': entry.get('model'),
        'total_tokens': entry.get('totalTokens'),
        'runtime': entry.get('runtime'),
        'runtime_ms': entry.get('runtimeMs'),
        'started_at': entry.get('startedAt'),
        'ended_at': entry.get('endedAt'),
        'pending_descendants': entry.get('pendingDescendants', 0),
        'active': active,
    }


def get_subagents(session_id=None, recent_minutes=30, status=None):
    status = status or get_status_json()
    session_key = resolve_requester_session_key(session_id, status=status)
    result = invoke_gateway_tool(
        'subagents',
        args={'action': 'list', 'recentMinutes': recent_minutes},
        session_key=session_key,
        message_channel=DEFAULT_CHANNEL,
    )
    details = (result.get('result') or {}).get('details') or {}
    active = [_subagent_view(item, active=True) for item in details.get('active') or []]
    recent = [_subagent_view(item, active=False) for item in details.get('recent') or []]
    return {
        'requester_session_key': details.get('requesterSessionKey') or session_key,
        'caller_session_key': details.get('callerSessionKey'),
        'caller_is_subagent': details.get('callerIsSubagent', False),
        'total': details.get('total', len(active) + len(recent)),
        'active': active,
        'recent': recent,
        'subagents': active + recent,
        'text': details.get('text') or '',
    }


def subagent_action(body, session_id=None, status=None):
    status = status or get_status_json()
    session_key = resolve_requester_session_key(session_id, status=status)
    action = (body.get('action') or 'list').strip()
    args = {'action': action}
    if body.get('target'):
        args['target'] = body.get('target')
    if body.get('message'):
        args['message'] = body.get('message')
    if body.get('recentMinutes'):
        args['recentMinutes'] = body.get('recentMinutes')
    result = invoke_gateway_tool('subagents', args=args, session_key=session_key, message_channel=DEFAULT_CHANNEL)
    details = (result.get('result') or {}).get('details') or {}
    ok_statuses = {'ok', 'accepted', 'done'}
    response = {
        'ok': details.get('status') in ok_statuses,
        'action': details.get('action') or action,
        'target': details.get('target'),
        'requester_session_key': details.get('requesterSessionKey') or session_key,
        'text': details.get('text') or '',
        'details': details,
    }
    if action == 'list':
        response.update(get_subagents(session_id=session_id, recent_minutes=body.get('recentMinutes') or 30, status=status))
    return response


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_OPTIONS(self):
        self.send_response(204)
        apply_cors(self)
        self.end_headers()

    def handle_exception(self, error):
        if isinstance(error, RuntimeError) and str(error) == 'Unauthorized':
            return json_response(self, 401, {'error': {'message': 'Unauthorized'}})
        if isinstance(error, RuntimeError) and str(error) == 'RateLimited':
            return json_response(self, 429, {'error': {'message': 'Too Many Requests'}})
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
            if self.path == '/api/runtime-status':
                self.require_auth()
                return json_response(self, 200, get_runtime_status())
            if self.path == '/api/diagnostics':
                self.require_auth()
                return json_response(self, 200, get_system_diagnostics())
            if self.path == '/api/processes':
                self.require_auth()
                return json_response(self, 200, get_processes())
            if self.path == '/api/subagents':
                self.require_auth()
                session_id = self.headers.get('x-openclaw-session-id')
                return json_response(self, 200, get_subagents(session_id=session_id))
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
            if self.path == '/api/auth/session':
                if not auth_ok(self):
                    raise RuntimeError('Unauthorized')
                _enforce_rate_limit(self)
                session = _issue_browser_session(subject='browser-fallback')
                return json_response(self, 200, {'ok': True, 'token': session['token'], 'issued_at': session['issued_at'], 'expires_at': session['expires_at'], 'ttl_seconds': session['ttl_seconds']})
            if self.path == '/api/command':
                output = command_output(body.get('command'), body.get('args'))
                return json_response(self, 200, {'output': output})
            if self.path == '/api/subagents':
                session_id = self.headers.get('x-openclaw-session-id')
                return json_response(self, 200, subagent_action(body, session_id=session_id))
            if self.path == '/api/actions/run':
                return json_response(self, 200, run_named_action(body.get('action')))
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
        _enforce_rate_limit(self)

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
