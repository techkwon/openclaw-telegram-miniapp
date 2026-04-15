#!/usr/bin/env python3
import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env_file(path):
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        env[key.strip()] = value.strip()
    return env


def get_value(name, env_file_values):
    return os.environ.get(name) or env_file_values.get(name, '')


def probe(name, url, timeout=5):
    if not url:
        print(f'- SKIP {name}: url not set')
        return True
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'openclaw-miniapp-verify/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, 'status', None) or resp.getcode()
            ok = 200 <= int(status) < 300
            print(f"{'OK' if ok else 'FAIL'} {name}: {url} -> HTTP {status}")
            return ok
    except urllib.error.HTTPError as e:
        print(f'FAIL {name}: {url} -> HTTP {e.code}')
        return False
    except Exception as e:
        print(f'FAIL {name}: {url} -> {e}')
        return False


def main():
    parser = argparse.ArgumentParser(description='Verify OpenClaw Telegram Mini App deployment')
    parser.add_argument('--env-file', default='.generated/miniapp.env', help='path to env file')
    parser.add_argument('--local-url', default='', help='override local bridge health url')
    parser.add_argument('--public-url', default='', help='override public health url')
    parser.add_argument('--gateway-url', default='', help='override gateway health url')
    args = parser.parse_args()

    env_file_values = load_env_file(args.env_file)
    miniapp_host = get_value('MINIAPP_HOST', env_file_values) or '127.0.0.1'
    miniapp_port = get_value('MINIAPP_PORT', env_file_values) or '8765'
    public_origin = get_value('MINIAPP_PUBLIC_ORIGIN', env_file_values)
    backend_base = get_value('OPENCLAW_BASE_URL', env_file_values) or 'http://127.0.0.1:18789'

    local_url = args.local_url or f'http://{miniapp_host}:{miniapp_port}/health'
    public_url = args.public_url or (public_origin.rstrip('/') + '/health' if public_origin else '')
    gateway_url = args.gateway_url or (backend_base.rstrip('/') + '/health' if backend_base else '')

    results = [
        probe('local-bridge', local_url),
        probe('openclaw-gateway', gateway_url),
        probe('public-origin', public_url) if public_url else True,
    ]

    if all(results):
        print('Deployment verification passed.')
        return 0
    print('Deployment verification failed.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
