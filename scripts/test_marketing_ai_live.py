"""Uncached exact-question acceptance through the local HTTP service.

Expected answers come from independently read DuckDB rows and Python ranking.
The shared matrix also checks deterministic Wren execution for every case.
"""
import json
import sys
from urllib.request import Request, urlopen


def post(path, payload):
    req = Request('http://127.0.0.1:4174' + path,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:4173'})
    with urlopen(req, timeout=100) as response:
        return json.load(response)


if __name__ == '__main__':
    from acceptance_matrix import main
    if '--live' not in sys.argv:
        sys.argv.append('--live')
    main()
