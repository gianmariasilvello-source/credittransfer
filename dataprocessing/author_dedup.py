"""
Author Deduplication for the curated MES dataset.

The MES authors file holds one record per author *mention source*, so a single person
often appears under several ids ('Brewin, Robert J. W.', 'Brewin, R. J. W.', 'Brewin, RJW',
'R Brewin'). Author metrics (h-index, credit rankings) then split one person's credit
across several ids.

Pipeline (code decides everything it can; TypeSafe judges only the ambiguous pairs):

1. Blocking (code): pairs of records with the same normalized surname and compatible
   given names ('R.' ~ 'Robert', 'Brad D.' ~ 'Bradley D.', 'RJW' ~ 'R. J. W.').
2. Hard rules (code): same ORCID -> merge; two different ORCIDs -> keep apart.
3. Judgment (TypeSafe or Simple Jev): for the remaining pairs, one request per pair with
   the two authors' name forms, co-authors, and works. A Score picks one of three outcomes
   (different people / curator review / same person) and two Nouls explain which
   evidence agrees, for the curator. Both backends take the same questions; answers are
   cached per backend model, so their results can be compared on the same pairs.
4. Clustering (code): union-find over merged pairs -> author_id -> canonical author_id.

The ORCID-labeled pairs double as an evaluation set: `--eval` scores them with the
ORCIDs hidden and reports how often the judgment agrees with ORCID.

Usage (from the project root):
    python -m dataprocessing.author_dedup --candidates-only      # no API calls
    python -m dataprocessing.author_dedup --eval 100             # needs TYPESAFE_API_KEY
    python -m dataprocessing.author_dedup                        # judge all, write merges
    python -m dataprocessing.author_dedup --backend simple-jev --eval 100
        # Simple Jev: FEATHERLESS_API_KEY -> production API; SIMPLE_JEV_URL -> private
        # server; neither -> public demo (compact state for its 2k-token budget, serial)
"""

import argparse
import csv
import hashlib
import itertools
import json
import os
import random
import re
import threading
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set, Tuple

from dataprocessing.MESProcessor import MESDataParser

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'source_graph_data', 'curated_MES')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'author_dedup')

TYPESAFE_MODEL = 'jev-1.13.0'  # pinned: re-evaluate before moving to a newer version
MAX_WORKERS = 6

# How much of each author record is sent to the model (works, co-author names, keywords).
# The Simple Jev public demo has a 2k-token context budget, so it gets the compact limits.
STANDARD_LIMITS = {'works': 10, 'coauthors': 25, 'keywords': 15}
COMPACT_LIMITS = {'works': 4, 'coauthors': 10, 'keywords': 6}

ORCID_RE = re.compile(r'(\d{3,4})-(\d{4})-(\d{4})-(\d{3}[\dXx])')

# --------------------------------------------------------------------------------------
# Judgment
# --------------------------------------------------------------------------------------

LEVELS = [
    "The two records describe different people: the names conflict once initials are "
    "expanded, or the co-authors and research topics point to separate careers.",
    "The two records could be the same person but the evidence is not decisive: "
    "compatible names with little overlap in co-authors or topics, or a common name "
    "shared by researchers in the same field.",
    "The two records describe one and the same person: compatible name forms "
    "together with shared co-authors or clearly continuous research topics.",
]
OUTCOME = {0: 'keep_apart', 1: 'curator', 2: 'merge'}


# Plain question specs: the Simple Jev API takes these as JSON, TypeSafe as SDK objects
QUESTIONS = {
    'same_person': dict(
        type='score',
        instructions=(
            "`author_a` and `author_b` are two author records from a bibliographic "
            "database of marine and earth-science research outputs. Each lists the "
            "name as written, the co-authors, and the works attributed to that record. "
            "How do the two records relate as people? Initials, missing middle names, "
            "diacritics, and 'Surname, Given' versus 'Given Surname' order are normal "
            "variations of one person's name."
        ),
        criteria=LEVELS,
    ),
    'names_consistent': dict(
        type='noul',
        instructions=(
            "Could the names written in `author_a.name_forms` and "
            "`author_b.name_forms` belong to the same person, allowing for initials, "
            "abbreviations, diacritics, and name order?"
        ),
    ),
    'same_research_area': dict(
        type='noul',
        instructions=(
            "Do the works of `author_a` and `author_b` fall in the same specific "
            "research area (not merely both marine or earth science)?"
        ),
    ),
}


def typesafe_questions():
    from typesafe_sdk import Noul, Score
    types = {'score': Score, 'noul': Noul}
    return {qid: types[q['type']](**{k: v for k, v in q.items() if k != 'type'})
            for qid, q in QUESTIONS.items()}


def judgment_version(model: str, limits: Dict) -> str:
    """Cache version: changes with the questions, the model, or the state limits."""
    # Bump the trailing tag when the state layout changes
    return hashlib.sha1(json.dumps([QUESTIONS, model, limits, 'v3'], sort_keys=True).encode()).hexdigest()[:10]


def route(score_value: float) -> str:
    """The nearest Score level names the outcome."""
    return OUTCOME[min(int(score_value + 0.5), len(LEVELS) - 1)]


# --------------------------------------------------------------------------------------
# Names and identifiers
# --------------------------------------------------------------------------------------

def strip_accents(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))


def split_name(record: Dict) -> Tuple[str, str]:
    """
    Return (given, surname) as written. Many records have empty name/surname fields and
    only a fullname, in either 'Surname, Given' or 'Given Surname' order.
    """
    given, surname = (record.get('name') or '').strip(), (record.get('surname') or '').strip()
    fullname = (record.get('fullname') or '').strip()
    if ',' in fullname:
        # The fullname keeps the original casing ('RJW'), the name field may not ('Rjw')
        surname_part, given_part = [p.strip() for p in fullname.split(',', 1)]
        return given_part or given, surname_part or surname
    if surname:
        return given, surname
    tokens = fullname.split()
    if len(tokens) < 2:
        return '', fullname
    return ' '.join(tokens[:-1]), tokens[-1]


def surname_key(surname: str) -> str:
    """Blocking key: the last word of the surname, lowercased, without accents."""
    words = re.findall(r"[a-z']+", strip_accents(surname).lower())
    return words[-1] if words else ''


def given_tokens(given: str) -> List[str]:
    """
    Split a given name into tokens, expanding packed initials: 'RJW' -> ['r', 'j', 'w'],
    'P. O. J.' -> ['p', 'o', 'j'], 'Brad D.' -> ['brad', 'd'].
    """
    tokens = []
    for raw in re.split(r'[\s.\-]+', strip_accents(given)):
        if not raw:
            continue
        if raw.isupper() and 1 < len(raw) <= 4:
            tokens.extend(raw.lower())
        else:
            tokens.append(raw.lower())
    return tokens


def given_names_compatible(a: str, b: str) -> bool:
    """
    True when two given names could be the same person's: each aligned token pair must
    agree as a prefix ('r' ~ 'robert', 'brad' ~ 'bradley'). Extra trailing tokens are
    allowed ('R.' ~ 'Robert J. W.'). This is deliberately permissive: it only has to keep
    true duplicates, the judgment decides.
    """
    ta, tb = given_tokens(a), given_tokens(b)
    if not ta or not tb:
        return False
    return all(p.startswith(q) or q.startswith(p) for p, q in zip(ta, tb))


def _name_surname_key(fullname: str) -> str:
    return surname_key(split_name({'fullname': fullname})[1])


def normalize_orcid(pid: str) -> Optional[str]:
    match = ORCID_RE.search(pid)
    if not match:
        return None
    first, second, third, last = match.groups()
    return f'{first.zfill(4)}-{second}-{third}-{last.upper()}'


# --------------------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------------------

def _read_jsonl(path: str) -> List[Dict]:
    with open(path, 'r') as f:
        return [json.loads(line) for line in f if line.strip()]


def _first(value) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ''
    return str(value or '')


class AuthorIndex:
    """Author records plus the works and co-authors each record is linked to."""

    def __init__(self, data_dir: str = DATA_DIR):
        self.records: Dict[str, Dict] = {}
        for record in _read_jsonl(os.path.join(data_dir, 'authors.jsonl')):
            if record.get('id'):
                self.records[str(record['id'])] = record

        self.works: Dict[str, Dict] = {}
        for name in ('publications', 'datasets', 'software'):
            path = os.path.join(data_dir, f'{name}.jsonl')
            if not os.path.exists(path):
                continue
            for item in _read_jsonl(path):
                self.works[item['id']] = {
                    'title': _first(item.get('title')).strip(),
                    'year': (item.get('dateofacceptance') or '')[:4],
                    'kind': name.rstrip('s'),
                    'keywords': [k for k in (item.get('keywords') or []) if isinstance(k, str)],
                }

        self.author_works: Dict[str, List[str]] = defaultdict(list)
        self.work_authors: Dict[str, List[str]] = defaultdict(list)
        for rel in _read_jsonl(os.path.join(data_dir, 'relations.jsonl')):
            if rel.get('semantics') == 'HasAuthor':
                work, author = rel.get('source'), str(rel.get('target'))
                self.author_works[author].append(work)
                self.work_authors[work].append(author)

        self.orcids: Dict[str, Set[str]] = {}
        self.other_pids: Dict[str, Set[str]] = {}
        for author_id, record in self.records.items():
            pids = MESDataParser._parse_pid_list(record.get('pid'))
            self.orcids[author_id] = {o for o in map(normalize_orcid, pids) if o}
            self.other_pids[author_id] = {p for p in pids if not normalize_orcid(p)}

    def coauthor_ids(self, author_id: str) -> Set[str]:
        return {c for w in self.author_works[author_id] for c in self.work_authors[w]} - {author_id}

    def coauthor_names(self, author_id: str) -> List[str]:
        return sorted({self.records[c]['fullname'].strip()
                       for c in self.coauthor_ids(author_id) if c in self.records})

    def profile(self, author_id: str, prioritize: Optional[Set[str]] = None,
                limits: Dict = STANDARD_LIMITS) -> Dict:
        """
        The state the model sees for one author record. ORCIDs are deliberately left out.
        Co-authors whose surname key is in `prioritize` are listed first, so co-authors the
        two records share survive the co-author cut.
        """
        record = self.records[author_id]
        coauthors = self.coauthor_names(author_id)
        if prioritize:
            coauthors.sort(key=lambda n: _name_surname_key(n) not in prioritize)
        works = [self.works[w] for w in self.author_works[author_id] if w in self.works]
        works.sort(key=lambda w: w['year'], reverse=True)
        keywords = Counter(k for w in works for k in w['keywords'])
        return {
            'name_forms': [record['fullname'].strip()],
            'coauthors': coauthors[:limits['coauthors']],
            'coauthor_count': len(coauthors),
            'works': [{'title': w['title'], 'year': w['year'], 'type': w['kind']}
                      for w in works[:limits['works']]],
            'work_count': len(works),
            'keywords': [k for k, _ in keywords.most_common(limits['keywords'])],
        }


# --------------------------------------------------------------------------------------
# Candidate pairs and hard rules
# --------------------------------------------------------------------------------------

def candidate_pairs(index: AuthorIndex) -> List[Dict]:
    """Blocking plus the ORCID rules. Each candidate carries the rule outcome, if any."""
    blocks: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for author_id, record in index.records.items():
        given, surname = split_name(record)
        key = surname_key(surname)
        if key and given:
            blocks[key].append((author_id, given))

    candidates = []
    for members in blocks.values():
        for (a, given_a), (b, given_b) in itertools.combinations(sorted(members), 2):
            if not given_names_compatible(given_a, given_b):
                continue
            orcid_a, orcid_b = index.orcids[a], index.orcids[b]
            if orcid_a & orcid_b:
                rule = 'merge'
            elif orcid_a and orcid_b:
                rule = 'keep_apart'
            else:
                rule = None
            shared = index.coauthor_ids(a) & index.coauthor_ids(b)
            candidates.append({
                'a': a, 'b': b,
                'name_a': index.records[a]['fullname'].strip(),
                'name_b': index.records[b]['fullname'].strip(),
                'rule': rule,
                'shared_coauthor_ids': len(shared),
                'shared_other_pids': sorted(index.other_pids[a] & index.other_pids[b]),
            })
    return candidates


# --------------------------------------------------------------------------------------
# Judging, with a JSON cache so reruns and threshold changes cost nothing
# --------------------------------------------------------------------------------------

class JudgmentCache:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.data = {}
        if os.path.exists(path):
            with open(path) as f:
                self.data = json.load(f)

    @staticmethod
    def key(a: str, b: str, version: str) -> str:
        return f'{a}|{b}|{version}'

    def get(self, a: str, b: str, version: str) -> Optional[Dict]:
        return self.data.get(self.key(a, b, version))

    def put(self, a: str, b: str, version: str, value: Dict):
        with self.lock:
            self.data[self.key(a, b, version)] = value

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)


class PairJudge:
    """
    Judges candidate pairs with one of two backends that take the same questions:
    'typesafe' (TypeSafe System One, TYPESAFE_API_KEY) or 'simple-jev' (Featherless
    Simple Jev classifier; see dataprocessing/simple_jev.py for endpoints and keys).
    """

    def __init__(self, index: AuthorIndex, cache: Optional[JudgmentCache], client=None,
                 backend: str = 'typesafe', model: Optional[str] = None,
                 limits: Optional[Dict] = None):
        self.index = index
        self.cache = cache
        self.backend = backend
        if backend == 'simple-jev':
            from dataprocessing.simple_jev import SimpleJevClient
            self.client = client or SimpleJevClient(**({'model': model} if model else {}))
            self.model = model or self.client.model
            demo = getattr(self.client, 'is_demo', False)
            self.limits = limits or (COMPACT_LIMITS if demo else STANDARD_LIMITS)
            self.workers = 1 if demo else MAX_WORKERS  # the demo allows 2 requests/second
            self.questions = QUESTIONS
        elif backend == 'typesafe':
            self.client = client  # created on first use, so offline code paths need no key
            self.model = model or TYPESAFE_MODEL
            self.limits = limits or STANDARD_LIMITS
            self.workers = MAX_WORKERS
            self.questions = None
        else:
            raise ValueError(f'unknown backend {backend!r}')
        self.version = judgment_version(self.model, self.limits)

    def state(self, a: str, b: str) -> Dict:
        keys_a = {_name_surname_key(n) for n in self.index.coauthor_names(a)}
        keys_b = {_name_surname_key(n) for n in self.index.coauthor_names(b)}
        shared = keys_a & keys_b
        return {'author_a': self.index.profile(a, shared, self.limits),
                'author_b': self.index.profile(b, shared, self.limits)}

    def judge(self, a: str, b: str) -> Dict:
        cached = self.cache.get(a, b, self.version)
        if cached is not None:
            return cached
        if self.client is None:
            from typesafe_sdk import TypeSafeClient
            self.client = TypeSafeClient(model=self.model, timeout=120.0)
        if self.questions is None:
            self.questions = typesafe_questions()
        response = self.client.system_one(state=self.state(a, b), questions=self.questions,
                                          model=self.model)
        same = response.answers['same_person']
        result = {
            'score': same.score,
            'confidence': same.confidence,
            'probabilities': same.probabilities,
            'names_consistent': response.answers['names_consistent'].noul,
            'same_research_area': response.answers['same_research_area'].noul,
            'model': response.model,
            'input_tokens': response.usage.input_tokens or 0,
        }
        self.cache.put(a, b, self.version, result)
        return result

    def judge_all(self, pairs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Dict]:
        results = {}
        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                for (a, b), result in zip(pairs, pool.map(lambda p: self.judge(*p), pairs)):
                    results[(a, b)] = result
                    if len(results) % 100 == 0:
                        print(f'  judged {len(results):,}/{len(pairs):,} pairs', end='\r')
                        self.cache.save()
        finally:
            self.cache.save()
        print(f'  judged {len(results):,}/{len(pairs):,} pairs')
        return results


# --------------------------------------------------------------------------------------
# Clustering and outputs
# --------------------------------------------------------------------------------------

def cluster(author_ids: List[str], merged_pairs: List[Tuple[str, str]],
            separated_pairs: List[Tuple[str, str]]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """
    Union-find over merged pairs. Returns author_id -> canonical id (smallest id in the
    cluster) and the separated pairs that transitive merging put in one cluster anyway,
    which need a curator.
    """
    parent = {a: a for a in author_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in merged_pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    members = defaultdict(list)
    for a in author_ids:
        members[find(a)].append(a)
    canonical = {}
    for group in members.values():
        root = min(group, key=lambda x: (len(x), x))
        for a in group:
            canonical[a] = root
    conflicts = [(a, b) for a, b in separated_pairs if canonical[a] == canonical[b]]
    return canonical, conflicts


def run_dedup(index: AuthorIndex, judge: PairJudge, output_dir: str) -> Dict:
    candidates = candidate_pairs(index)
    to_judge = [(c['a'], c['b']) for c in candidates if c['rule'] is None]
    print(f'{len(candidates):,} candidate pairs: '
          f"{sum(c['rule'] == 'merge' for c in candidates):,} merged by ORCID, "
          f"{sum(c['rule'] == 'keep_apart' for c in candidates):,} kept apart by ORCID, "
          f'{len(to_judge):,} to judge')
    judgments = judge.judge_all(to_judge)

    merged, separated, queue = [], [], []
    rows = []
    for c in candidates:
        pair = (c['a'], c['b'])
        if c['rule']:
            outcome, j = c['rule'], None
        else:
            j = judgments[pair]
            outcome = route(j['score'])
        (merged if outcome == 'merge' else separated if outcome == 'keep_apart' else queue).append(pair)
        rows.append({**c, 'outcome': outcome, 'judgment': j})

    canonical, conflicts = cluster(sorted(index.records), merged, separated)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'pair_decisions.jsonl'), 'w') as f:
        for row in rows:
            f.write(json.dumps(row) + '\n')
    with open(os.path.join(output_dir, 'author_merges.json'), 'w') as f:
        json.dump({a: c for a, c in canonical.items() if a != c}, f, indent=1, sort_keys=True)
    with open(os.path.join(output_dir, 'curator_queue.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['author_a', 'name_a', 'author_b', 'name_b', 'reason', 'score',
                         'confidence', 'names_consistent', 'same_research_area',
                         'shared_coauthor_ids'])
        reasons = {**{p: 'uncertain' for p in queue}, **{p: 'transitive conflict' for p in conflicts}}
        for row in rows:
            pair = (row['a'], row['b'])
            if pair in reasons:
                j = row['judgment'] or {}
                writer.writerow([row['a'], row['name_a'], row['b'], row['name_b'], reasons[pair],
                                 _fmt(j.get('score')), _fmt(j.get('confidence')),
                                 _fmt(j.get('names_consistent')), _fmt(j.get('same_research_area')),
                                 row['shared_coauthor_ids']])

    n_clusters = len(set(canonical.values()))
    summary = {
        'backend': judge.backend,
        'model': judge.model,
        'judgment_version': judge.version,
        'author_records': len(index.records),
        'people_after_merge': n_clusters,
        'records_merged_away': len(index.records) - n_clusters,
        'pairs': Counter(r['outcome'] for r in rows),
        'curator_queue': len(queue) + len(conflicts),
        'transitive_conflicts': len(conflicts),
        'input_tokens': sum(j.get('input_tokens', 0) for j in judgments.values()),
    }
    with open(os.path.join(output_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    return summary


def _fmt(value) -> str:
    return '' if value is None else f'{value:.3f}'


def evaluate(index: AuthorIndex, judge: PairJudge, sample: int, seed: int = 0) -> Dict:
    """
    Judge ORCID-labeled pairs with the ORCIDs hidden: same ORCID = same person, two
    different ORCIDs = different people. Reports routing against those labels.
    """
    candidates = candidate_pairs(index)
    rng = random.Random(seed)
    labeled = []
    for rule, label in (('merge', True), ('keep_apart', False)):
        group = [c for c in candidates if c['rule'] == rule]
        labeled += [(c, label) for c in rng.sample(group, min(sample, len(group)))]
    judgments = judge.judge_all([(c['a'], c['b']) for c, _ in labeled])

    table = Counter()
    errors = []
    for c, label in labeled:
        j = judgments[(c['a'], c['b'])]
        outcome = route(j['score'])
        table[('same' if label else 'different', outcome)] += 1
        if (label and outcome == 'keep_apart') or (not label and outcome == 'merge'):
            errors.append({'label_same': label, 'outcome': outcome, 'name_a': c['name_a'],
                           'name_b': c['name_b'], 'score': round(j['score'], 3),
                           'shared_coauthor_ids': c['shared_coauthor_ids']})

    def rate(label, outcome):
        total = sum(v for (l, _), v in table.items() if l == label)
        return table[(label, outcome)] / total if total else float('nan')

    return {
        'pairs': {f'{l}->{o}': v for (l, o), v in sorted(table.items())},
        'wrong_merge_rate': rate('different', 'merge'),
        'missed_merge_rate': rate('same', 'keep_apart'),
        'auto_merge_recall': rate('same', 'merge'),
        'curator_rate': (table[('same', 'curator')] + table[('different', 'curator')]) / max(len(labeled), 1),
        'errors': errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data-dir', default=DATA_DIR)
    parser.add_argument('--output-dir', default=OUTPUT_DIR)
    parser.add_argument('--candidates-only', action='store_true',
                        help='write candidate pairs and rule outcomes; no API calls')
    parser.add_argument('--eval', type=int, metavar='N',
                        help='judge N ORCID-matched and N ORCID-conflicting pairs, ORCIDs hidden')
    parser.add_argument('--backend', choices=['typesafe', 'simple-jev'], default='typesafe',
                        help='typesafe: TYPESAFE_API_KEY. simple-jev: FEATHERLESS_API_KEY for '
                             'the production API, SIMPLE_JEV_URL for a private server, '
                             'neither for the public demo')
    parser.add_argument('--model', help='override the backend default model')
    args = parser.parse_args()

    index = AuthorIndex(args.data_dir)
    if args.candidates_only:
        candidates = candidate_pairs(index)
        os.makedirs(args.output_dir, exist_ok=True)
        path = os.path.join(args.output_dir, 'candidates.jsonl')
        with open(path, 'w') as f:
            for c in candidates:
                f.write(json.dumps(c) + '\n')
        print(f'{len(candidates):,} candidate pairs -> {path}')
        print(f"  rule outcomes: {dict(Counter(c['rule'] for c in candidates))}")
        return

    if args.backend == 'typesafe' and not os.environ.get('TYPESAFE_API_KEY'):
        raise SystemExit('Set TYPESAFE_API_KEY (https://console.typesafe.ai/), use '
                         '--backend simple-jev, or use --candidates-only.')
    cache = JudgmentCache(os.path.join(args.output_dir, 'judgment_cache.json'))
    judge = PairJudge(index, cache, backend=args.backend, model=args.model)
    if args.backend == 'simple-jev':
        print(f'Simple Jev endpoint: {judge.client.base_url}  model: {judge.model}  '
              f'limits: {judge.limits}  workers: {judge.workers}')

    if args.eval:
        report = evaluate(index, judge, args.eval)
        path = os.path.join(args.output_dir, f'eval_report_{args.backend}.json')
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        print(json.dumps({k: v for k, v in report.items() if k != 'errors'}, indent=2))
        print(f'{len(report["errors"])} hard errors; full report -> {path}')
        return

    summary = run_dedup(index, judge, args.output_dir)
    print(json.dumps(summary, indent=2))
    print(f'Outputs in {args.output_dir}/')


if __name__ == '__main__':
    main()
