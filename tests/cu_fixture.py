"""A loopback-only simulated assignment page for manual CU validation."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

HTML = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>KillTheHW 本地模拟作业</title>
<style>body{max-width:760px;margin:40px auto;font:18px/1.7 system-ui;padding:0 20px}textarea{width:100%;height:100px;font:inherit}button{padding:10px 18px;margin:12px 12px 12px 0;font:inherit}pre{white-space:pre-wrap;background:#eee;padding:18px}label{display:block}</style>
<h1>KillTheHW 本地模拟作业</h1><p>仅测试电脑操作。不连接真实课程，不计分。</p>
<p>题目：计算 2、4、6 的算术平均数，填写答案并上传 TXT，最后提交。</p>
<label for="answer">答案</label><textarea id="answer"></textarea>
<label for="file">答案文件</label><input type="file" id="file" accept=".txt">
<p><button id="upload">上传附件并保存草稿</button><button id="submit" disabled>提交本地测试作业</button></p>
<pre id="status" aria-live="polite">草稿：尚未上传</pre>
<script>
const answer=document.querySelector('#answer'), file=document.querySelector('#file'), status=document.querySelector('#status'), submit=document.querySelector('#submit');
let uploaded=null;
document.querySelector('#upload').onclick=async()=>{
 if(!file.files[0]||!answer.value.trim()){status.textContent='请填写答案并选择文件';return;}
 uploaded={answer:answer.value,filename:file.files[0].name,content:await file.files[0].text()};
 const r=await fetch('/draft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(uploaded)});
 const data=await r.json(); status.textContent='附件已上传；作业仍为草稿，尚未提交。\\n文件：'+data.filename+'\\nSHA-256：'+data.sha256;submit.disabled=false;
};
submit.onclick=async()=>{
 const r=await fetch('/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(uploaded)});
 const data=await r.json();status.textContent='已提交（仅本地模拟）\\n回执：'+data.receipt_id+'\\n文件：'+data.filename+'\\n答案：'+data.answer+'\\nSHA-256：'+data.sha256+'\\n时间：'+data.observed_at;submit.disabled=true;
};
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send_json(self, value):
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

        def do_POST(self):
            value = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            value.update(sha256=hashlib.sha256(value["content"].encode()).hexdigest(),
                         observed_at=datetime.now(timezone.utc).isoformat())
            if self.path == "/draft":
                value["state"] = "uploaded"
                destination = args.directory / "draft.json"
            elif self.path == "/submit":
                value.update(state="submitted", receipt_id="LOCAL-CU-001")
                destination = args.directory / "submission.json"
            else:
                self.send_error(404)
                return
            destination.write_text(json.dumps(value, ensure_ascii=False, indent=2))
            self.send_json(value)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    print(f"http://127.0.0.1:{server.server_port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
