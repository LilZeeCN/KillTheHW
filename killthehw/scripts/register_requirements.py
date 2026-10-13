#!/usr/bin/env python3
"""Draft numbered requirements, then register a reviewed batch with stable links."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from _common import digest, load_job, local_path, write_json


def draft(root, job, input_id, key, title, pattern):
    item = next(x for x in job['inputs'] if x['id'] == input_id)
    extraction = item.get('extraction', {})
    if digest(Path(item['path'])) != item['sha256'] or extraction.get('source_sha256') != item['sha256']:
        raise ValueError('Source/extraction changed; re-read it before drafting')
    text_path = local_path(root, extraction['text'])
    if digest(text_path) != extraction.get('text_sha256'):
        raise ValueError('Extracted text changed; re-extract before drafting')
    regex = re.compile(pattern)
    if not {'number', 'text'} <= set(regex.groupindex):
        raise ValueError('pattern needs named number and text groups')
    rows, current, location = [], None, ''
    for n, raw in enumerate(text_path.read_text(encoding='utf-8').splitlines(), 1):
        if raw.startswith('## '):
            location = raw[3:]
            continue
        # Inner XML indices are not followed by whitespace; match the locator boundary.
        located = re.match(r'^\[(.+?)\]\s+(.*)$', raw)
        if located:
            locator, content = located.groups()
        else:
            content, locator = raw, f'extracted line {n}'
        match = regex.match(content.strip())
        if match:
            current = {'key': match['number'], 'number': match['number'], 'text': match['text'],
                       'source': {'input_id': input_id, 'locator': f'{location} {locator}'.strip()},
                       'check_kind': 'content'}
            rows.append(current)
        elif current and content.strip():
            current['text'] += '\n' + content.strip()
    return {'assignment': {'key': key, 'title': title,
                          'source': {'input_id': input_id, 'locator': 'reviewed assignment scope'}},
            'input_hashes': {input_id: item['sha256']}, 'requirements': rows,
            'review_note': 'Candidates only. Review numbering, continuations, optional groups and source locations before import.'}


def register(job, batch):
    result = deepcopy(job)
    source_hashes = {x['id']: x['sha256'] for x in job['inputs']}
    if any(source_hashes.get(k) != v for k, v in batch.get('input_hashes', {}).items()):
        raise ValueError('Batch refers to a stale source')
    used = {x['id'] for key in ('assignments', 'requirements', 'tasks', 'checks', 'deliverables')
            for x in result[key]}

    def allocate(prefix):
        n = 1
        while f'{prefix}{n:03d}' in used:
            n += 1
        value = f'{prefix}{n:03d}'
        used.add(value)
        return value

    def by_key(collection, key):
        matches = [x for x in result[collection] if x.get('registration_key') == key]
        if len(matches) > 1:
            raise ValueError(f'Duplicate registration key: {key}')
        return matches[0] if matches else None

    spec = batch['assignment']
    assignment_key = str(spec['key'])
    if not assignment_key or not spec.get('title') or not spec.get('source'):
        raise ValueError('assignment needs key, title and source')
    assignment = by_key('assignments', assignment_key)
    if assignment and any(assignment[k] != spec[k] for k in ('title', 'source')):
        raise ValueError('Existing assignment differs; update it explicitly')
    if not assignment:
        assignment = {'id': allocate('A'), 'registration_key': assignment_key,
                      'title': spec['title'], 'source': spec['source']}
        result['assignments'].append(assignment)
    mapping, seen = [], set()
    for row in batch['requirements']:
        key = f"{assignment_key}/{row['key']}"
        if key in seen or not row.get('text') or not row.get('source'):
            raise ValueError(f'Duplicate key or missing text/source: {key}')
        seen.add(key)
        source = row['source']
        if source.get('input_id') and source['input_id'] not in source_hashes:
            raise ValueError(f'Unknown input in {key}')
        if row.get('required', True) is False and not row.get('reason'):
            raise ValueError(f'Optional requirement needs a reason: {key}')
        signature = json.dumps(row, ensure_ascii=False, sort_keys=True)
        existing = by_key('requirements', key)
        if existing:
            if existing.get('registration_spec') != signature:
                raise ValueError(f'Registered requirement changed: {key}; revise existing records explicitly')
            mapping.append({'key': key, 'requirement': existing['id'],
                            'tasks': existing['task_ids'], 'checks': existing['check_ids']})
            continue
        task_key = f"{assignment_key}/{row.get('task_key', row['key'])}"
        task = by_key('tasks', task_key)
        if not task:
            task = {'id': allocate('T'), 'registration_key': task_key,
                    'title': row.get('task_title', row['text'].splitlines()[0]),
                    'requirement_ids': [], 'status': 'planned'}
            result['tasks'].append(task)
        if task['status'] != 'planned':
            raise ValueError(f'Cannot add requirements to an already started task: {task_key}')
        rid, cid = allocate('R'), allocate('C')
        task['requirement_ids'].append(rid)
        req = {'id': rid, 'registration_key': key, 'registration_spec': signature,
               'assignment_id': assignment['id'], 'text': row['text'], 'source': source,
               'number': row.get('number', row['key']), 'required': row.get('required', True),
               'task_ids': [task['id']], 'check_ids': [cid]}
        if 'reason' in row:
            req['reason'] = row['reason']
        result['requirements'].append(req)
        result['checks'].append({'id': cid, 'kind': row.get('check_kind', 'content'),
                                 'status': 'pending', 'method': '', 'result': '',
                                 'subjects': [], 'evidence': [], 'input_hashes': {}})
        mapping.append({'key': key, 'requirement': rid, 'tasks': [task['id']], 'checks': [cid]})
    if not mapping:
        raise ValueError('No requirements to register')
    return result, mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    propose = sub.add_parser('draft')
    propose.add_argument('job_dir')
    propose.add_argument('--input', required=True)
    propose.add_argument('--assignment-key', required=True)
    propose.add_argument('--title', required=True)
    propose.add_argument('--pattern', default=r'^(?P<number>\d+(?:\.\d+)*|（\d+）|[（(]\d+[)）]|（[一二三四五六七八九十]+）|[一二三四五六七八九十]+)[.、．)）]?\s*(?P<text>.+)$',
                         help='Numbering pattern with named number/text groups. The default also matches '
                              'full-width forms like （1）/（一）; supply a custom pattern for other styles '
                              'such as Chinese numerals 一、二、 or part markers (a)(b).')
    propose.add_argument('--out', type=Path, required=True)
    apply = sub.add_parser('import')
    apply.add_argument('job_dir')
    apply.add_argument('batch', type=Path)
    apply.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        root, job = load_job(args.job_dir)
        if args.command == 'draft':
            if args.out.exists():
                raise ValueError('Choose a new draft output path')
            value = draft(root, job, args.input, args.assignment_key, args.title, args.pattern)
            write_json(args.out, value)
            print(json.dumps({'draft': str(args.out), 'candidates': len(value['requirements'])}))
        else:
            for item in job['inputs']:
                if digest(Path(item['path'])) != item['sha256']:
                    raise ValueError(f"Changed source: {item['id']}")
            updated, mapping = register(job, json.loads(args.batch.read_text(encoding='utf-8')))
            if not args.dry_run and updated != job:
                write_json(root / 'job.json', updated)
                with (root / 'actions.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                                        'action': 'requirements_registered', 'observed': mapping}, ensure_ascii=False) + '\n')
            print(json.dumps({'dry_run': args.dry_run, 'mapping': mapping}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
