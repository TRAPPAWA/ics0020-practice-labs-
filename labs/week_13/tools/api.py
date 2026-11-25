"""Small standard-library client for the lab's OpenSearch REST API."""
import json
import os
import time
import urllib.error
import urllib.request

BASE = os.environ.get('SEARCH_URL', 'http://127.0.0.1:19200').rstrip('/')
INDEX = 'lab-events-v1'

class APIError(RuntimeError):
    pass

def request(method, path, body=None, *, ndjson=False, timeout=30):
    if not path.startswith('/'):
        raise ValueError('API path must start with /')
    data = body if isinstance(body, bytes) else (json.dumps(body).encode() if body is not None else None)
    headers = {'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/x-ndjson' if ndjson else 'application/json'
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise APIError(f'{method} {path}: HTTP {e.code}: {e.read().decode(errors="replace")[:1800]}') from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise APIError(f'{method} {path}: {e}') from e

def wait_ready(seconds=180):
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        try:
            health = request('GET', '/_cluster/health?wait_for_status=yellow&timeout=3s', timeout=8)
            if health['status'] in ('yellow', 'green') and not health.get('timed_out'):
                version = request('GET', '/')['version']['number']
                print(f'OpenSearch {version}: {health["status"]}; nodes={health["number_of_nodes"]}')
                if version != '2.19.4':
                    raise SystemExit(f'Expected 2.19.4, got {version}. Check your lab image.')
                return
        except APIError as exc:
            last = exc
        time.sleep(2)
    raise APIError(f'Cluster not ready. Inspect docker compose logs search. Last error: {last}')
