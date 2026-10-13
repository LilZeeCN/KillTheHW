#!/usr/bin/env python3
"""Durable POSIX PTY execution with raw output, explicit input and process-exit status."""
import argparse
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import uuid

from _common import digest, load_job, local_path, write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def worker(directory):
    request = json.loads((directory / 'request.json').read_text())
    state = {'kind': 'pty_session', 'state': 'starting', 'started_at': now(),
             'argv': request['argv'], 'cwd': request['cwd'], 'columns': request['columns'],
             'rows': request['rows'], 'worker_pid': os.getpid(), 'session_id': request['session_id']}
    child, master = pty.fork()
    if child == 0:
        try:
            os.chdir(request['cwd'])
            os.environ['TERM'] = 'xterm-256color'
            os.execvp(request['argv'][0], request['argv'])
        except Exception as error:
            os.write(2, f'Execution failed: {error}\n'.encode())
            os._exit(127)
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', request['rows'], request['columns'], 0, 0))
    state.update(state='running', process_pid=child)
    write_json(directory / 'status.json', state)
    exit_status, stop_at, eof = None, None, False
    try:
        from _common import caffeinate_guard
        with caffeinate_guard(), (directory / 'raw.log').open('ab', buffering=0) as log:
            while exit_status is None or not eof:
                if (directory / 'stop.request').exists() and stop_at is None and exit_status is None:
                    try:
                        os.killpg(child, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    stop_at = time.monotonic()
                if stop_at is not None and time.monotonic() - stop_at > 2 and exit_status is None:
                    try:
                        os.killpg(child, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                for queued in sorted((directory / 'inbox').glob('*.input')):
                    if exit_status is not None:
                        break
                    data = queued.read_bytes()
                    remaining = memoryview(data)
                    while remaining:
                        remaining = remaining[os.write(master, remaining):]
                    queued.rename(directory / 'sent' / queued.name)
                if not eof and select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        chunk = b''
                    if chunk:
                        log.write(chunk)
                    else:
                        eof = True
                if exit_status is None:
                    pid, value = os.waitpid(child, os.WNOHANG)
                    if pid:
                        exit_status = value
                if eof and exit_status is None:
                    time.sleep(0.05)
        state.update(state='stopped' if stop_at is not None else 'exited',
                     exit_code=os.waitstatus_to_exitcode(exit_status), ended_at=now(),
                     raw_sha256=digest(directory / 'raw.log'))
    except Exception as error:
        state.update(state='interrupted', error=str(error), ended_at=now())
    finally:
        os.close(master)
        write_json(directory / 'status.json', state)


def session_path(job_dir, session_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', session_id):
        raise ValueError('session ID must contain 1-64 letters, digits, hyphens or underscores')
    root, _ = load_job(job_dir)
    return local_path(root, f'evidence/pty/{session_id}')


def idle_seconds(directory):
    """Seconds since raw.log last grew; heuristic only, never proof of completion."""
    try:
        return max(time.time() - (directory / 'raw.log').stat().st_mtime, 0.0)
    except OSError:
        return None


def status(directory, wait=0, idle=None):
    deadline = time.monotonic() + wait
    while True:
        path = directory / 'status.json'
        launcher = directory / 'launcher.json'
        value = json.loads(path.read_text()) if path.exists() else {
            'state': 'starting', **(json.loads(launcher.read_text()) if launcher.exists() else {})}
        ended = value['state'] not in {'starting', 'running'}
        if not ended and idle is not None:
            quiet = idle_seconds(directory)
            if quiet is not None and quiet >= idle:
                # Interactive clients (REPL shells) never exit; a quiet log is only a hint.
                value['idle_seconds'] = quiet
                value['idle_hint'] = ('no new output for the requested interval; heuristic only, '
                                      'verify the actual prompt/state in raw.log before sending input')
                return value
        if ended or time.monotonic() >= deadline:
            if value.get('worker_pid') and not ended:
                try:
                    os.kill(value['worker_pid'], 0)
                except ProcessLookupError:
                    value.update(state='interrupted', error='Worker is no longer running; do not infer command success')
                    ended = True
            if idle is not None and not ended:
                value['idle_seconds'] = idle_seconds(directory)
            return value
        time.sleep(0.1)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '_worker':
        worker(Path(sys.argv[2]))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    start = commands.add_parser('start')
    start.add_argument('job_dir')
    start.add_argument('session_id')
    start.add_argument('--cwd', type=Path, required=True)
    start.add_argument('--columns', type=int, default=120)
    start.add_argument('--rows', type=int, default=40)
    # Command argv is separated by --, so host strings are never interpreted by a shell here.
    for name in ('status', 'send', 'stop'):
        p = commands.add_parser(name)
        p.add_argument('job_dir')
        p.add_argument('session_id')
        if name == 'status':
            p.add_argument('--wait', type=float, default=0)
            p.add_argument('--idle', type=float, default=None,
                           help='Return early once raw.log has been quiet for this many seconds '
                                '(for interactive clients that do not exit). Heuristic hint only; '
                                'always confirm the prompt in raw.log before further input.')
        elif name == 'send':
            p.add_argument('--file', type=Path, required=True)
    raw = sys.argv[1:]
    argv = raw[raw.index('--') + 1:] if '--' in raw else []
    args = parser.parse_args(raw[:raw.index('--')] if '--' in raw else raw)
    try:
        directory = session_path(args.job_dir, args.session_id)
        if args.command == 'start':
            if not argv or not args.cwd.is_dir():
                raise ValueError('Provide an existing cwd and a command after --')
            if directory.exists():
                raise ValueError('Session already exists; inspect/resume it or choose a new session ID')
            if not 20 <= args.columns <= 500 or not 5 <= args.rows <= 200:
                raise ValueError('PTY dimensions outside supported range')
            directory.mkdir(parents=True)
            (directory / 'inbox').mkdir()
            (directory / 'sent').mkdir()
            (directory / 'raw.log').touch()
            write_json(directory / 'request.json', {'session_id': args.session_id, 'argv': argv,
                       'cwd': str(args.cwd.resolve()), 'columns': args.columns, 'rows': args.rows})
            with (directory / 'worker.log').open('wb') as log:
                process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '_worker', str(directory)],
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            write_json(directory / 'launcher.json', {'worker_pid': process.pid, 'launched_at': now()})
            print(json.dumps({'session': str(directory), 'worker_pid': process.pid, 'state': 'starting'}))
            return 0
        if not directory.exists():
            raise ValueError('Unknown session')
        if args.command == 'status':
            if not 0 <= args.wait <= 60:
                raise ValueError('wait must be between 0 and 60 seconds')
            if args.idle is not None and not 1 <= args.idle <= 300:
                raise ValueError('idle must be between 1 and 300 seconds')
            value = status(directory, args.wait, args.idle)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0 if value['state'] == 'exited' and value.get('exit_code') == 0 else 1
        if status(directory)['state'] not in {'starting', 'running'}:
            raise ValueError('Session has already ended; inputs/stops were not sent')
        if args.command == 'send':
            data = args.file.read_bytes()
            if len(data) > 4096:
                raise ValueError('Interactive input is limited to 4096 bytes; execute scripts/files through command argv')
            queued = directory / 'inbox' / f'{time.time_ns()}-{uuid.uuid4().hex}.input'
            temporary = queued.with_suffix('.tmp')
            temporary.write_bytes(data)
            temporary.rename(queued)
            print(json.dumps({'state': 'queued', 'bytes': len(data), 'input_sha256': hashlib.sha256(data).hexdigest()}))
        else:
            (directory / 'stop.request').write_text(now())
            print(json.dumps({'state': 'stop_requested', 'note': 'Inspect status for actual process termination'}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
