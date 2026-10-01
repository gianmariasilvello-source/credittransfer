"""
Offline tests for dataprocessing/author_dedup.py and the MES relation handling.

A fake TypeSafe client and a local fake Simple Jev server stand in for the APIs, so these
run without TYPESAFE_API_KEY or FEATHERLESS_API_KEY.
Run: python -m pytest test/test_author_dedup.py   (or python test/test_author_dedup.py)
"""

import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataprocessing import author_dedup as ad
from dataprocessing import simple_jev
from dataprocessing.MESProcessor import MESDataParser


def _write_jsonl(path, rows):
    with open(path, 'w') as f:
        for row in rows:
            f.write(json.dumps(row) + '\n')


def _toy_dataset(tmp):
    authors = [
        {'id': 'a1', 'fullname': 'Brewin, Robert J. W.', 'name': 'Robert J. W.', 'surname': 'Brewin', 'pid': '[0000-0001-5134-8291]'},
        {'id': 'a2', 'fullname': 'Brewin, RJW', 'name': 'Rjw', 'surname': 'Brewin', 'pid': '[]'},
        {'id': 'a3', 'fullname': 'R Brewin', 'name': 'R', 'surname': 'Brewin', 'pid': '[0000-0001-5134-8291]'},
        {'id': 'a4', 'fullname': 'Brewin, Susan', 'name': 'Susan', 'surname': 'Brewin', 'pid': '[]'},
        {'id': 'a5', 'fullname': ' Per O. J. Hall', 'name': '', 'surname': '', 'pid': '[0000-0002-1111-2222]'},
        {'id': 'a6', 'fullname': 'Hall, P.', 'name': 'P.', 'surname': 'Hall', 'pid': '[0000-0002-3333-444x]'},
        {'id': 'a7', 'fullname': 'Sathyendranath, Shubha', 'name': 'Shubha', 'surname': 'Sathyendranath', 'pid': '[]'},
    ]
    works = [
        {'id': 'p1', 'title': ['Ocean colour remote sensing of phytoplankton'], 'keywords': ['ocean colour'], 'dateofacceptance': '2017-01-01'},
        {'id': 'p2', 'title': ['Phytoplankton size classes from satellite'], 'keywords': ['ocean colour'], 'dateofacceptance': '2015-01-01'},
        {'id': 'p3', 'title': ['Benthic fluxes in the Baltic'], 'keywords': ['sediment'], 'dateofacceptance': '2010-01-01'},
    ]
    datasets = [{'id': 'd1', 'title': ['Chlorophyll time series'], 'keywords': [], 'dateofacceptance': '2016-01-01'}]
    relations = [
        {'source': 'p1', 'target': 'a1', 'semantics': 'HasAuthor'},
        {'source': 'p1', 'target': 'a7', 'semantics': 'HasAuthor'},
        {'source': 'p2', 'target': 'a2', 'semantics': 'HasAuthor'},
        {'source': 'p2', 'target': 'a7', 'semantics': 'HasAuthor'},
        {'source': 'p3', 'target': 'a4', 'semantics': 'HasAuthor'},
        {'source': 'p3', 'target': 'a5', 'semantics': 'HasAuthor'},
        {'source': 'p1', 'target': 'p2', 'semantics': 'Cites', 'status': 'Validated'},
        {'source': 'p2', 'target': 'p3', 'semantics': 'IsPartOf', 'status': 'Added'},
        {'source': 'p3', 'target': 'p1', 'semantics': 'Cites', 'status': 'Removed'},
        {'source': 'd1', 'target': 'p1', 'semantics': 'IsSupplementedBy', 'status': 'Validated'},
        {'source': 'p1', 'target': 'd1', 'semantics': 'IsVariantFormOf', 'status': 'Added'},
    ]
    _write_jsonl(os.path.join(tmp, 'authors.jsonl'), authors)
    _write_jsonl(os.path.join(tmp, 'publications.jsonl'), works)
    _write_jsonl(os.path.join(tmp, 'datasets.jsonl'), datasets)
    _write_jsonl(os.path.join(tmp, 'relations.jsonl'), relations)


class FakeClient:
    """Answers 'same person' when the two records share a co-author, 'different' otherwise."""

    def __init__(self):
        self.calls = 0

    def system_one(self, state, questions, model=None):
        self.calls += 1
        assert set(questions) == {'same_person', 'names_consistent', 'same_research_area'}
        shared = set(state['author_a']['coauthors']) & set(state['author_b']['coauthors'])
        score = 1.9 if shared else 0.2
        answers = {
            'same_person': SimpleNamespace(score=score, confidence=0.9, probabilities={}),
            'names_consistent': SimpleNamespace(noul=0.8),
            'same_research_area': SimpleNamespace(noul=0.9 if shared else 0.1),
        }
        return SimpleNamespace(answers=answers, model='fake', usage=SimpleNamespace(input_tokens=100))


def test_name_helpers():
    assert ad.given_names_compatible('Robert J. W.', 'RJW')
    assert ad.given_names_compatible('R', 'Robert J. W.')
    assert ad.given_names_compatible('Brad D.', 'Bradley D.')
    assert not ad.given_names_compatible('Brad D.', 'Bernard')
    assert not ad.given_names_compatible('Robert', 'Susan')
    assert ad.split_name({'fullname': ' Per O. J. Hall', 'name': '', 'surname': ''}) == ('Per O. J.', 'Hall')
    assert ad.split_name({'fullname': 'Brewin, RJW', 'name': 'Rjw', 'surname': 'Brewin'}) == ('RJW', 'Brewin')
    assert ad.surname_key('Van Oevelen') == 'oevelen'
    assert ad.normalize_orcid('000-0001-5291-3141') == '0000-0001-5291-3141'
    assert ad.normalize_orcid('0000-0002-4838-327x') == '0000-0002-4838-327X'
    assert ad.route(0.2) == 'keep_apart' and ad.route(1.3) == 'curator' and ad.route(1.94) == 'merge'


def test_candidates_and_rules():
    with tempfile.TemporaryDirectory() as tmp:
        _toy_dataset(tmp)
        index = ad.AuthorIndex(tmp)
        pairs = {(c['a'], c['b']): c for c in ad.candidate_pairs(index)}
        assert pairs[('a1', 'a3')]['rule'] == 'merge'  # same ORCID
        assert pairs[('a5', 'a6')]['rule'] == 'keep_apart'  # different ORCIDs
        assert pairs[('a1', 'a2')]['rule'] is None  # needs judgment
        assert ('a1', 'a4') not in pairs  # Robert vs Susan never compared
        assert 'orcid' not in json.dumps(ad.PairJudge(index, None).state('a1', 'a2')).lower()


def test_run_dedup_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        _toy_dataset(tmp)
        index = ad.AuthorIndex(tmp)
        client = FakeClient()
        cache = ad.JudgmentCache(os.path.join(tmp, 'out', 'cache.json'))
        summary = ad.run_dedup(index, ad.PairJudge(index, cache, client), os.path.join(tmp, 'out'))
        merges = json.load(open(os.path.join(tmp, 'out', 'author_merges.json')))
        # a1~a3 by ORCID, a1~a2 by judgment (shared co-author a7): one person
        assert merges == {'a2': 'a1', 'a3': 'a1'}
        assert summary['people_after_merge'] == 5
        calls = client.calls
        # rerun is served from the cache
        ad.run_dedup(index, ad.PairJudge(index, ad.JudgmentCache(cache.path), client), os.path.join(tmp, 'out'))
        assert client.calls == calls


def test_transitive_conflict_goes_to_curator():
    canonical, conflicts = ad.cluster(['a', 'b', 'c'], [('a', 'b'), ('b', 'c')], [('a', 'c')])
    assert canonical == {'a': 'a', 'b': 'a', 'c': 'a'}
    assert conflicts == [('a', 'c')]


def test_mes_relations_case_insensitive_and_status_filter():
    with tempfile.TemporaryDirectory() as tmp:
        _toy_dataset(tmp)
        files = [os.path.join(tmp, f) for f in ('publications.jsonl', 'datasets.jsonl')]
        rel = os.path.join(tmp, 'relations.jsonl')
        parser = MESDataParser(*files, relations_file=rel)
        parser.parse_all()
        ids = parser.external_to_internal_node
        assert parser.edges == {
            (ids['p1'], ids['p2']),  # p1 Cites p2
            (ids['p3'], ids['p2']),  # p2 IsPartOf p3
            (ids['p1'], ids['d1']),  # d1 IsSupplementedBy p1
        }
        assert parser.relation_stats['skipped_status'] == 1
        assert parser.unknown_semantics == {'IsVariantFormOf': 1}

        keep_all = MESDataParser(*files, relations_file=rel, excluded_statuses=set())
        keep_all.parse_all()
        assert (ids['p3'], ids['p1']) in keep_all.edges


class _FakeSimpleJev(BaseHTTPRequestHandler):
    """Local stand-in for POST /v1/classifier. Scripted statuses are consumed first."""
    script = []
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        type(self).requests.append({'body': body, 'auth': self.headers.get('Authorization')})
        status = type(self).script.pop(0) if type(self).script else 200
        if status == 301:
            self.send_response(301)
            self.send_header('Location', 'https://example.com/elsewhere')
            self.end_headers()
            return
        if status != 200:
            self.send_response(status)
            self.send_header('Retry-After', '0')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': {'message': f'status {status}'}}).encode())
            return
        state = body['state']
        shared = set(state['author_a']['coauthors']) & set(state['author_b']['coauthors'])
        answers = {}
        for qid, q in body['questions'].items():
            if q['type'] == 'score':
                answers[qid] = {'score': 1.9 if shared else 0.1, 'confidence': 0.9,
                                'probabilities': {}, 'legend': {}}
            else:
                answers[qid] = {'noul': 0.8}
        payload = {'model': body['model'], 'answers': answers,
                   'usage': {'prompt_tokens': 321, 'completion_tokens': 0}}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *args):
        pass


def _serve():
    _FakeSimpleJev.script, _FakeSimpleJev.requests = [], []
    server = HTTPServer(('127.0.0.1', 0), _FakeSimpleJev)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}'


def _state():
    return {'author_a': {'coauthors': ['X']}, 'author_b': {'coauthors': ['X']}}


def test_simple_jev_client_parses_and_retries():
    server, url = _serve()
    try:
        client = simple_jev.SimpleJevClient(base_url=url, api_key='k', min_interval=0)
        _FakeSimpleJev.script = [429, 503]
        response = client.system_one(_state(), ad.QUESTIONS)
        assert response.answers['same_person'].score == 1.9
        assert response.answers['names_consistent'].noul == 0.8
        assert response.usage.input_tokens == 321
        assert len(_FakeSimpleJev.requests) == 3  # two retried failures, then success
        assert _FakeSimpleJev.requests[0]['auth'] == 'Bearer k'
        sent = _FakeSimpleJev.requests[0]['body']['questions']
        assert sent['same_person']['type'] == 'score' and sent['same_person']['criteria'] == ad.LEVELS

        _FakeSimpleJev.script = [401]
        try:
            client.system_one(_state(), ad.QUESTIONS)
            raise AssertionError('401 should raise')
        except simple_jev.SimpleJevError as e:
            assert '401' in str(e)
        assert len(_FakeSimpleJev.requests) == 4  # no retry on 401

        _FakeSimpleJev.script = [301]
        try:
            client.system_one(_state(), ad.QUESTIONS)
            raise AssertionError('redirect should raise')
        except simple_jev.SimpleJevError as e:
            assert 'not following' in str(e)

        keyless = simple_jev.SimpleJevClient(base_url=url, api_key='', min_interval=0)
        keyless.system_one(_state(), ad.QUESTIONS)
        assert _FakeSimpleJev.requests[-1]['auth'] is None
    finally:
        server.shutdown()


def test_simple_jev_endpoint_selection():
    env = {k: os.environ.pop(k) for k in ('FEATHERLESS_API_KEY', 'SIMPLE_JEV_URL') if k in os.environ}
    try:
        demo = simple_jev.SimpleJevClient()
        assert demo.is_demo and demo.min_interval == 0.5
        assert simple_jev.SimpleJevClient(api_key='k').base_url == simple_jev.PRODUCTION_URL
        os.environ['SIMPLE_JEV_URL'] = 'http://gpu-box:8000/'
        assert simple_jev.SimpleJevClient(api_key='k').base_url == 'http://gpu-box:8000'
    finally:
        os.environ.pop('SIMPLE_JEV_URL', None)
        os.environ.update(env)


def test_run_dedup_with_simple_jev_backend():
    server, url = _serve()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _toy_dataset(tmp)
            index = ad.AuthorIndex(tmp)
            client = simple_jev.SimpleJevClient(base_url=url, api_key='', min_interval=0)
            cache = ad.JudgmentCache(os.path.join(tmp, 'out', 'cache.json'))
            judge = ad.PairJudge(index, cache, client, backend='simple-jev')
            assert judge.limits == ad.STANDARD_LIMITS and judge.model == simple_jev.DEFAULT_MODEL
            summary = ad.run_dedup(index, judge, os.path.join(tmp, 'out'))
            merges = json.load(open(os.path.join(tmp, 'out', 'author_merges.json')))
            assert merges == {'a2': 'a1', 'a3': 'a1'}
            assert summary['backend'] == 'simple-jev' and summary['input_tokens'] == 2 * 321
            # A TypeSafe judge does not reuse Simple Jev answers from the shared cache
            assert ad.PairJudge(index, cache).version != judge.version

            demo_client = simple_jev.SimpleJevClient(base_url=url, min_interval=0)
            demo_client.is_demo = True
            demo = ad.PairJudge(index, cache, demo_client, backend='simple-jev')
            assert demo.limits == ad.COMPACT_LIMITS and demo.workers == 1
    finally:
        server.shutdown()


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print(f'ok  {name}')
