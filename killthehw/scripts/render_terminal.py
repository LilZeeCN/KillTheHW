#!/usr/bin/env python3
"""Render an immutable snapshot of a real PTY log, visibly labelled as non-screenshot evidence."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from _common import digest, write_json


# Common xterm palette mapped to hex RGB; bold is rendered via a brighter set.
PALETTE = {
    'black': '#5c6370', 'red': '#e06c75', 'green': '#98c379', 'brown': '#d19a66',
    'yellow': '#d19a66', 'blue': '#61afef', 'magenta': '#c678dd', 'cyan': '#56b6c2',
    'white': '#abb2bf', 'default': '#e4edf5',
    'brightblack': '#7f848e', 'brightred': '#ff6b6b', 'brightgreen': '#a9e07a',
    'brightyellow': '#ffd479', 'brightblue': '#7fc0ff', 'brightmagenta': '#e2a0ff',
    'brightcyan': '#7fe0e0', 'brightwhite': '#ffffff',
}


def cell_color(char, monochrome):
    if monochrome:
        return '#e4edf5'
    fg = char.fg if char.fg and char.fg != 'default' else 'default'
    if char.bold and fg in PALETTE and 'bright' + fg not in PALETTE and fg != 'default':
        fg = 'bright' + fg if 'bright' + fg in PALETTE else fg
    return PALETTE.get(fg, PALETTE['default'])


def render(session, output, font_path, lines_per_page=40, monochrome=False):
    import pyte
    from PIL import Image, ImageDraw, ImageFont
    if output.exists():
        raise ValueError('Output directory must be new')
    meta = json.loads((session / 'status.json').read_text())
    raw = (session / 'raw.log').read_bytes()
    if meta['state'] not in {'exited', 'stopped'}:
        raise ValueError('Capture an ended session; live sessions must be inspected without claiming a final result')
    output.mkdir(parents=True)
    snapshot = output / 'source.raw'
    snapshot.write_bytes(raw)
    if digest(snapshot) != meta.get('raw_sha256'):
        raise ValueError('PTY log changed after its exit record')
    write_json(output / 'session.json', meta)
    screen = pyte.HistoryScreen(meta['columns'], meta['rows'], history=10000)
    pyte.ByteStream(screen).feed(raw)
    rows = list(screen.history.top) + [screen.buffer[n] for n in range(screen.lines)]
    while rows and not any(c.data.strip() for c in rows[-1].values()):
        rows.pop()
    if not rows:
        rows = [{}]
    font = ImageFont.truetype(str(font_path), 18)
    header_font = ImageFont.truetype(str(font_path), 16)
    cell, height = max(11, round(font.getlength('M'))), 26
    width = max(900, meta['columns'] * cell + 40)
    manifests = []
    for start in range(0, len(rows), lines_per_page):
        chunk = rows[start:start + lines_per_page]
        picture = Image.new('RGB', (width, 115 + height * len(chunk)), '#17212b')
        draw = ImageDraw.Draw(picture)
        draw.text((20, 12), 'PTY LOG RENDER - NOT A SCREENSHOT', font=header_font, fill='#ffd479')
        draw.text((20, 38), f"Session {meta['session_id']} | exit={meta.get('exit_code')} | {meta['state']}", font=header_font, fill='white')
        draw.text((20, 62), f"log sha256: {digest(snapshot)[:32]} | rows {start + 1}-{start + len(chunk)}", font=header_font, fill='#b4c6d8')
        for y, line in enumerate(chunk):
            for x, char in sorted(line.items()):
                if char.data and char.data != ' ':
                    draw.text((20 + x * cell, 98 + y * height), char.data,
                              font=font, fill=cell_color(char, monochrome))
        path = output / f'page-{len(manifests) + 1}.png'
        picture.save(path)
        manifest = {'kind': 'pty_rendered', 'render_sha256': digest(path),
                    'source_raw': 'source.raw', 'source_sha256': digest(snapshot),
                    'session': 'session.json', 'session_sha256': digest(output / 'session.json'),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'presentation': ('monochrome terminal-cell replay; original ANSI bytes retained in source.raw'
                                     if monochrome else
                                     'ANSI-coloured terminal-cell replay; original ANSI bytes retained in source.raw'),
                    'color_mode': 'monochrome' if monochrome else 'ansi',
                    'disclosure': '真实 PTY 会话日志渲染，非屏幕截图。仅重放日志可表达的终端内容，不证明桌面环境或 GUI 操作。',
                    'history_limit': 10000, 'row_start': start + 1, 'row_end': start + len(chunk)}
        write_json(path.with_suffix('.json'), manifest)
        manifests.append(str(path))
    return {'images': manifests, 'source_sha256': digest(snapshot), 'kind': 'pty_rendered'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--font', type=Path, required=True, help='Monospaced font with the required language glyphs')
    parser.add_argument('--monochrome', action='store_true',
                        help='Drop SGR colours for a plain single-colour replay. Colour is the default '
                             'because it matches what a real terminal shows; the non-screenshot label '
                             'and provenance manifest stay identical in both modes.')
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.session, args.out_dir, args.font, monochrome=args.monochrome),
                         ensure_ascii=False, indent=2))
        return 0
    except ImportError:
        print('Rendering requires pyte and Pillow; raw PTY capture does not.', file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
