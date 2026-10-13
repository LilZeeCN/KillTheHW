"""Local CLI tests using synthetic files; no learning platform is contacted."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

SCRIPTS = Path(__file__).resolve().parents[1] / "killthehw" / "scripts"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf(path, content):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
               b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    data, offsets = b"%PDF-1.4\n", [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    start = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    data += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    path.write_bytes(data)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="killthehw-test-")
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.job = self.root / "job"

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, script, *args, expected=0):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / script), *map(str, args)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else None

    def initialize(self):
        return self.cli("inspect_inputs.py", "--job-dir", self.job, self.inputs)

    def save(self, value):
        (self.job / "job.json").write_text(json.dumps(value), encoding="utf-8")

    def test_inventory_deduplication_symlinks_and_no_overwrite(self):
        source = self.inputs / "任务.txt"
        source.write_text("完成第一题。", encoding="utf-8")
        (self.inputs / "outside-link").symlink_to(self.root)
        result = self.cli("inspect_inputs.py", "--job-dir", self.job, self.inputs, source)
        self.assertEqual(result["input_count"], 1)
        self.assertEqual(len(result["skipped_directory_symlinks"]), 1)
        before = (self.job / "job.json").read_bytes()
        self.cli("inspect_inputs.py", "--job-dir", self.job, source, expected=2)
        self.assertEqual((self.job / "job.json").read_bytes(), before)

    def test_format_text_media_and_locations(self):
        with ZipFile(self.inputs / "任务.docx", "w") as z:
            z.writestr("word/document.xml", '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>选择两题</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格内的小问</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>''')
            z.writestr("word/media/image1.png", b"fixture-media")
        with ZipFile(self.inputs / "课件.pptx", "w") as z:
            z.writestr("ppt/slides/slide1.xml", '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><a:p><a:r><a:t>课堂例题</a:t></a:r></a:p></p:cSld></p:sld>''')
        with ZipFile(self.inputs / "数据.xlsx", "w") as z:
            z.writestr("xl/workbook.xml", '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="数据" sheetId="1" r:id="rId1"/></sheets></workbook>''')
            z.writestr("xl/_rels/workbook.xml.rels", '''<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>''')
            z.writestr("xl/worksheets/sheet1.xml", '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><v>3</v></c><c r="B1"><f>A1*2</f><v>6</v></c></row></sheetData></worksheet>''')
        self.initialize()
        output = self.cli("extract_materials.py", self.job)
        job = json.loads((self.job / "job.json").read_text())
        by_kind = {x["kind"]: x for x in job["inputs"]}
        docx = by_kind["docx"]["extraction"]
        text = (self.job / docx["text"]).read_text()
        self.assertIn("表格内的小问", text)
        self.assertIn("/tbl[1]/tr[1]/tc[1]/p[1]", text)
        self.assertTrue(docx["media"])
        self.assertIn("formula=A1*2; cached=6", (self.job / by_kind["xlsx"]["extraction"]["text"]).read_text())
        self.assertIn("课堂例题", (self.job / by_kind["pptx"]["extraction"]["text"]).read_text())
        self.assertTrue(all(x["visual_review_required"] for x in output))
        self.assertTrue(all(x["review"]["status"] == "pending" for x in job["inputs"]))

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext not installed")
    def test_empty_pdf_is_not_reported_as_text_extracted(self):
        pdf(self.inputs / "scan.pdf", b"")
        self.initialize()
        output = self.cli("extract_materials.py", self.job, expected=1)
        self.assertEqual(output[0]["status"], "needs_host_reader")
        self.assertTrue(output[0]["visual_review_required"])

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext not installed")
    def test_pdf_text_has_page_locator_and_visual_warning(self):
        pdf(self.inputs / "text.pdf", b"BT /F1 12 Tf 50 700 Td (Question one: calculate the arithmetic mean.) Tj ET")
        self.initialize()
        output = self.cli("extract_materials.py", self.job)
        text = (self.job / output[0]["text"]).read_text()
        self.assertIn("PDF page 1", text)
        self.assertIn("Question one", text)
        self.assertTrue(output[0]["visual_review_required"])

    def complete_record(self):
        source = self.inputs / "data.csv"
        source.write_text("value\n2\n4\n6\n")
        self.initialize()
        self.cli("extract_materials.py", self.job)
        job = json.loads((self.job / "job.json").read_text())
        item = job["inputs"][0]
        item.update(role="data", review={"status": "complete", "sha256": item["sha256"], "scope": "all rows"})
        result = self.job / "deliverables" / "answer.txt"
        result.write_text("Mean = 4\n")
        (self.job / "evidence" / "calculation.txt").write_text("(2+4+6)/3 = 4; independently sum/len = 4\n")
        job["assignments"] = [{"id": "A1", "title": "Mean", "source": "conversation"}]
        job["requirements"] = [{"id": "R1", "assignment_id": "A1", "text": "Calculate mean", "source": "conversation", "task_ids": ["T1"], "check_ids": ["C1"]}]
        job["tasks"] = [{"id": "T1", "status": "complete", "requirement_ids": ["R1"]}]
        job["deliverables"] = [{"id": "D1", "path": "deliverables/answer.txt", "sha256": sha(result), "status": "verified", "requirement_ids": ["R1"], "check_ids": ["C1"], "required_check_kinds": ["calculation"]}]
        job["checks"] = [{"id": "C1", "kind": "calculation", "status": "passed", "method": "independent sum/len", "result": "4 matches", "subjects": [{"path": "deliverables/answer.txt", "sha256": sha(result)}], "input_hashes": {item["id"]: item["sha256"]}, "evidence": ["evidence/calculation.txt"]}]
        job["delivery"] = {"target": "local", "state": "local_ready", "scope": "local answer"}
        return job

    def test_complete_record_and_missing_or_stale_work(self):
        baseline = self.complete_record()
        self.save(baseline)
        self.assertTrue(self.cli("check_deliverables.py", self.job)["record_checks_passed"])
        mutations = [lambda j: j["tasks"][0].update(status="blocked"),
                     lambda j: j["checks"][0].update(evidence=["evidence/missing.txt"]),
                     lambda j: j["checks"][0].update(input_hashes={"I001": "stale"}),
                     lambda j: j["requirements"][0].update(task_ids=[]),
                     lambda j: j["delivery"].update(target="submit", state="uploaded")]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(baseline)
                mutation(changed)
                self.save(changed)
                self.cli("check_deliverables.py", self.job, expected=1)
        self.save(baseline)
        (self.job / "deliverables" / "answer.txt").write_text("Mean = 999\n")
        self.cli("check_deliverables.py", self.job, expected=1)

    def test_submitted_claim_needs_submitted_receipt(self):
        job = self.complete_record()
        job["delivery"] = {"target": "upload", "state": "submitted", "scope": "upload only", "destination": "local-test", "receipts": [{"state": "uploaded", "destination": "local-test", "observed_at": "2026-09-12T12:00:00+08:00", "evidence": ["evidence/calculation.txt"], "deliverable_ids": ["D1"], "subjects": job["checks"][0]["subjects"]}]}
        self.save(job)
        self.cli("check_deliverables.py", self.job, expected=1)

    def test_source_change_and_unsupported_format(self):
        source = self.inputs / "任务.txt"
        source.write_text("original")
        (self.inputs / "old.doc").write_bytes(b"unparsed")
        self.initialize()
        source.write_text("changed requirement")
        results = self.cli("extract_materials.py", self.job, expected=1)
        self.assertEqual({x["status"] for x in results}, {"error", "needs_host_reader"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
