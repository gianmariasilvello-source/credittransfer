"""
Minimal client for the Simple Jev classifier API (Featherless.ai).

Simple Jev takes the same question types as TypeSafe (choice, score, noul) at
POST <base>/v1/classifier. This client exposes a `system_one(state, questions, model)`
method returning the same answer shape the TypeSafe SDK does, so callers such as
author_dedup.PairJudge can use either backend.

Endpoints (https://simplejev.ai/skills.md):
    production: https://api.featherless.ai          (Authorization: Bearer $FEATHERLESS_API_KEY)
    public demo: https://simple-jev-demo-api.featherless.ai   (no key; 2k-token context, 2 req/s)
    private:    any base URL, set with SIMPLE_JEV_URL

Standard library only. Redirects are never followed, so a key cannot leak to another host.
"""

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime
from types import SimpleNamespace
from typing import Dict, Optional

PRODUCTION_URL = 'https://api.featherless.ai'
DEMO_URL = 'https://simple-jev-demo-api.featherless.ai'
DEFAULT_MODEL = 'featherless-ai/Qwen3.6-35B-A3B-classifier'
MAX_RETRIES = 3


class SimpleJevError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SimpleJevError(f'{req.full_url} redirected ({code}) to {newurl}; not following. '
                             f'Check the endpoint (SIMPLE_JEV_URL).')


class SimpleJevClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: str = DEFAULT_MODEL, timeout: float = 60.0,
                 min_interval: Optional[float] = None):
        """
        Args:
            base_url: API base; default SIMPLE_JEV_URL, else production when a key is set,
                else the public demo.
            api_key: default FEATHERLESS_API_KEY. Not sent when None.
            min_interval: minimum seconds between request starts (default 0.5 on the
                public demo, which allows 2 requests/second; 0 elsewhere).
        """
        self.api_key = api_key if api_key is not None else os.environ.get('FEATHERLESS_API_KEY')
        self.base_url = (base_url or os.environ.get('SIMPLE_JEV_URL')
                         or (PRODUCTION_URL if self.api_key else DEMO_URL)).rstrip('/')
        self.model = model
        self.timeout = timeout
        self.is_demo = self.base_url == DEMO_URL
        self.min_interval = (0.5 if self.is_demo else 0.0) if min_interval is None else min_interval
        self._opener = urllib.request.build_opener(_NoRedirect)
        self._pace_lock = threading.Lock()
        self._next_start = 0.0

    def _pace(self):
        with self._pace_lock:
            now = time.monotonic()
            wait = self._next_start - now
            self._next_start = max(now, self._next_start) + self.min_interval
        if wait > 0:
            time.sleep(wait)

    def _post(self, body: Dict) -> Dict:
        data = json.dumps(body).encode()
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        url = f'{self.base_url}/v1/classifier'

        for attempt in range(MAX_RETRIES + 1):
            self._pace()
            request = urllib.request.Request(url, data=data, headers=headers, method='POST')
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as e:
                detail = _error_detail(e)
                if e.code == 429 or e.code >= 500:
                    if attempt == MAX_RETRIES:
                        raise SimpleJevError(f'HTTP {e.code} after {MAX_RETRIES} retries: {detail}')
                    time.sleep(_retry_after(e) or (2 ** attempt) + random.random())
                    continue
                # 400/413/422: fix the request; 401/403: fix the key. Retrying cannot help.
                raise SimpleJevError(f'HTTP {e.code}: {detail}')
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == MAX_RETRIES:
                    raise SimpleJevError(f'network error after {MAX_RETRIES} retries: {e}')
                time.sleep((2 ** attempt) + random.random())
        raise AssertionError('unreachable')

    def system_one(self, state, questions: Dict[str, Dict], model: Optional[str] = None):
        """
        Ask `questions` (plain dicts: {'type': 'score'|'choice'|'noul', 'instructions', 'criteria'})
        about `state`. Returns an object with .answers[qid], .model and .usage.input_tokens,
        matching the TypeSafe SDK's SystemOneResponse closely enough for PairJudge.
        """
        payload = self._post({'model': model or self.model, 'state': state, 'questions': questions})
        answers = payload.get('answers')
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise SimpleJevError(f'response missing answers: {str(payload)[:300]}')
        usage = payload.get('usage') or {}
        return SimpleNamespace(
            model=payload.get('model'),
            answers={qid: SimpleNamespace(**answer) for qid, answer in answers.items()},
            usage=SimpleNamespace(input_tokens=usage.get('prompt_tokens', usage.get('input_tokens', 0)),
                                  output_tokens=usage.get('completion_tokens', usage.get('output_tokens', 0))),
        )


def _error_detail(error: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(error.read())
        return str((body.get('error') or {}).get('message') or body.get('detail') or body)[:300]
    except Exception:
        return error.reason


def _retry_after(error: urllib.error.HTTPError) -> Optional[float]:
    value = error.headers.get('Retry-After') if error.headers else None
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        try:
            return max(parsedate_to_datetime(value).timestamp() - time.time(), 0.0)
        except Exception:
            return None
