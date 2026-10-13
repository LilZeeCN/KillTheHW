#!/usr/bin/env python3
"""Control VS Code / Cursor editor & integrated terminal 100% silently in background via Extension Host V8 Inspector."""
import argparse
import base64
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request


def _find_extension_host_pids():
    res = subprocess.run(
        ["ps", "-eo", "pid,command"],
        capture_output=True, text=True, check=False
    )
    pids = []
    for line in res.stdout.splitlines():
        if "Code Helper (Plugin)" in line and "--inspect-port=0" in line:
            parts = line.strip().split(None, 1)
            if parts and parts[0].isdigit():
                pids.append(int(parts[0]))
    return pids


def _get_inspector_ws_for_pid(pid):
    def probe_ports():
        res = subprocess.run(
            ["lsof", "-Pan", "-p", str(pid), "-iTCP", "-sTCP:LISTEN"],
            capture_output=True, text=True, check=False
        )
        for line in res.stdout.splitlines():
            if "127.0.0.1:" in line:
                for token in line.split():
                    if token.startswith("127.0.0.1:"):
                        port = token.split(":")[1]
                        try:
                            data = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=0.8).read()
                            items = json.loads(data)
                            if items and "webSocketDebuggerUrl" in items[0]:
                                return items[0]["webSocketDebuggerUrl"]
                        except Exception:
                            pass
        return None

    ws = probe_ports()
    if ws:
        return ws
    try:
        os.kill(pid, signal.SIGUSR1)
    except OSError:
        return None
    for _ in range(10):
        time.sleep(0.2)
        ws = probe_ports()
        if ws:
            return ws
    return None


def _eval_ws(ws_url, expression):
    _, rest = ws_url.split("ws://", 1)
    host_port, path = rest.split("/", 1)
    host, port = host_port.split(":")
    s = socket.create_connection((host, int(port)), timeout=5)
    try:
        key = base64.b64encode(b"killthehw-vscode").decode()
        req = (
            f"GET /{path} HTTP/1.1\r\n"
            f"Host: {host_port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.sendall(req.encode())
        s.recv(4096)

        payload = json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "includeCommandLineAPI": True,
                "returnByValue": True,
                "awaitPromise": True,
            }
        }).encode()
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header.extend(n.to_bytes(2, "big"))
        else:
            header.append(0x80 | 127)
            header.extend(n.to_bytes(8, "big"))
        header.extend(b"\x00\x00\x00\x00")
        s.sendall(header + payload)

        while True:
            b = s.recv(2)
            if not b:
                break
            length = b[1] & 0x7f
            if length == 126:
                length = int.from_bytes(s.recv(2), "big")
            elif length == 127:
                length = int.from_bytes(s.recv(8), "big")
            buf = b""
            while len(buf) < length:
                buf += s.recv(length - len(buf))
            msg = json.loads(buf.decode())
            if msg.get("id") == 1:
                return msg.get("result", {}).get("result", {}).get("value")
    finally:
        s.close()


def find_target_ws(workspace=None):
    target_ws = str(Path(workspace).resolve()) if workspace else None
    for pid in _find_extension_host_pids():
        ws = _get_inspector_ws_for_pid(pid)
        if not ws:
            continue
        info = _eval_ws(ws, """
        (() => {
            const M = process.getBuiltinModule ? process.getBuiltinModule("module") : require("module");
            const extMod = Object.values(M._cache).find(m => m.filename && m.filename.includes(".vscode/extensions/"));
            if (!extMod) return null;
            const vscode = extMod.require("vscode");
            const folders = (vscode.workspace.workspaceFolders || []).map(f => f.uri.fsPath);
            return { folders };
        })()
        """)
        if not info:
            continue
        if not target_ws or any(Path(f).resolve() == Path(target_ws) for f in info.get("folders", [])):
            return ws
    raise RuntimeError("Could not find a running VS Code Extension Host matching the workspace.")


def main():
    parser = argparse.ArgumentParser(description="Headless background control for VS Code without focus stealing.")
    parser.add_argument("--workspace", help="Workspace folder path to match")
    parser.add_argument("--open-file", help="Open file in editor silently")
    parser.add_argument("--close-others", action="store_true", help="Close other editor tabs before opening file")
    parser.add_argument("--new-terminal", action="store_true", help="Reset and create a single clean integrated terminal")
    parser.add_argument("--send-text", help="Send command text to the integrated terminal and execute it")
    args = parser.parse_args()

    ws = find_target_ws(args.workspace)
    actions = {
        "openFile": str(Path(args.open_file).resolve()) if args.open_file else None,
        "closeOthers": bool(args.close_others),
        "newTerminal": bool(args.new_terminal),
        "sendText": args.send_text,
        "cwd": str(Path(args.workspace).resolve()) if args.workspace else None,
    }
    js = f"""
    (async () => {{
        const cfg = {json.dumps(actions)};
        const M = process.getBuiltinModule ? process.getBuiltinModule("module") : require("module");
        const extMod = Object.values(M._cache).find(m => m.filename && m.filename.includes(".vscode/extensions/"));
        const vscode = extMod.require("vscode");
        const out = {{}};

        if (cfg.closeOthers) {{
            await vscode.commands.executeCommand("workbench.action.closeAllEditors");
        }}
        if (cfg.openFile) {{
            const doc = await vscode.workspace.openTextDocument(cfg.openFile);
            const editor = await vscode.window.showTextDocument(doc, {{ preview: false, preserveFocus: false }});
            await vscode.commands.executeCommand("workbench.action.files.revert");
            editor.selection = new vscode.Selection(0, 0, 0, 0);
            editor.revealRange(new vscode.Range(0, 0, 0, 0));
            if (vscode.window.terminals.length > 0 && !cfg.newTerminal) {{
                vscode.window.terminals[0].show(false);
            }}
            out.openedFile = doc.fileName;
        }}
        if (cfg.newTerminal) {{
            for (const t of vscode.window.terminals) {{
                t.dispose();
            }}
            await new Promise(r => setTimeout(r, 400));
            const term = vscode.window.createTerminal({{ name: "zsh", cwd: cfg.cwd || undefined }});
            term.show(false);
            out.newTerminalPid = await term.processId;
        }}
        if (cfg.sendText !== null && cfg.sendText !== undefined) {{
            let term = vscode.window.activeTerminal || vscode.window.terminals[0];
            if (!term) {{
                term = vscode.window.createTerminal({{ name: "zsh", cwd: cfg.cwd || undefined }});
            }}
            term.show(false);
            term.sendText(cfg.sendText + "\\r", false);
            out.sentText = cfg.sendText;
            out.terminalPid = await term.processId;
        }}
        return out;
    }})()
    """
    res = _eval_ws(ws, js)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
