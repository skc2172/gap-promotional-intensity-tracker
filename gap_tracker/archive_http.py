"""Archive transport fallback for network errors only, never HTTP access denials."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import requests
from gap_tracker.wayback import fetch as requests_fetch


def fetch(url, body_path, params=None):
    body_path = Path(body_path)
    meta_path = body_path.with_suffix(body_path.suffix + '.request.json')
    expected = requests.Request('GET', url, params=params).prepare().url
    old = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if old.get('error') and not body_path.exists() and old.get('requested_url') == expected:
        meta = old
    else:
        meta = requests_fetch(url, body_path, params)
    if not meta.get('error') or meta.get('status_code') is not None:
        return meta
    backup = meta_path.with_name(meta_path.name + '.' + hashlib.sha256(meta_path.read_bytes()).hexdigest()[:8] + '.failed')
    backup.write_bytes(meta_path.read_bytes())
    headers_path = body_path.with_suffix(body_path.suffix + '.curl-headers.txt')
    result = subprocess.run(['curl', '--compressed', '--max-time', '30', '--silent', '--show-error',
                             '--dump-header', str(headers_path), '--output', str(body_path), expected],
                            capture_output=True, text=True)
    headers, status = {}, None
    if headers_path.exists():
        for line in headers_path.read_text().splitlines():
            if line.startswith('HTTP/'):
                status = int(line.split()[1]); headers = {}
            elif ':' in line:
                k, v = line.split(':', 1)
                if 'cookie' not in k.lower(): headers[k.lower()] = v.strip()
    new = {'requested_url': expected, 'url': expected, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
           'transport': 'curl_after_connection_failure', 'previous_attempt': str(backup),
           'status_code': status, 'headers': headers}
    if result.returncode:
        new['error'] = result.stderr
        new['partial_http_status'] = new['status_code']
        new['status_code'] = None
    if body_path.exists():
        new['sha256'] = hashlib.sha256(body_path.read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(new, indent=2)+'\n')
    return new
