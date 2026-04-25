import importlib.util
import io
import json
import shutil
import tarfile
import unittest
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

import requests


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "skills"
    / "gem5-prescreen"
    / "scripts"
    / "gem5_prescreener.py"
)
SPEC = importlib.util.spec_from_file_location("gem5_prescreener", SCRIPT_PATH)
gem5_prescreener = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gem5_prescreener)


def make_tar_gz(files: Dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in files.items():
            payload = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: Optional[dict] = None,
        text: str = "",
        content: bytes = b"",
        lines: Optional[List[str]] = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.content = content
        self._lines = lines or []

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self) -> dict:
        return self._json_data

    def iter_lines(self, decode_unicode: bool = False):
        for line in self._lines:
            yield line if decode_unicode else line.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestGem5Prescreener(unittest.TestCase):
    def setUp(self):
        self.run_name = f"test_gem5_{uuid.uuid4().hex[:8]}"
        self.input_dir = gem5_prescreener.WORKSPACE_ROOT / "gem5PrescreenInputs" / self.run_name
        self.artifact_path = gem5_prescreener.WORKSPACE_ROOT / "gem5PrescreenArtifacts" / self.run_name
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.script_path = self.input_dir / "demo_iter_1.py"
        self.script_path.write_text("# compiled script copy\n", encoding="utf-8")
        self.elf_name = "demo_iter_1.Default.ELF"
        (self.input_dir / self.elf_name).write_bytes(b"\x7fELFcompiled")
        stale_dir = self.input_dir / "work_force"
        stale_dir.mkdir(parents=True, exist_ok=True)
        (stale_dir / "AgenticTargetTest.Default.ELF").write_bytes(b"\x7fELFstale")
        self.old_poll_interval = gem5_prescreener.POLL_INTERVAL
        gem5_prescreener.POLL_INTERVAL = 0

    def tearDown(self):
        gem5_prescreener.POLL_INTERVAL = self.old_poll_interval
        shutil.rmtree(self.input_dir, ignore_errors=True)
        shutil.rmtree(self.artifact_path, ignore_errors=True)

    def test_run_persists_artifacts_and_manifest(self):
        task_id = "run-success-001"
        uploaded = {}
        tar_bytes = make_tar_gz(
            {
                f"m5out_{task_id}/stats.txt": "simInsts 123\nsystem.cpu.ipc 1.25\n",
                f"m5out_{task_id}/simout": "booting\nPASS_MARKER\n",
                f"m5out_{task_id}/simerr": "warn line\n",
            }
        )

        def fake_post(url, *args, **kwargs):
            if url.endswith("/upload"):
                uploaded["filename"] = kwargs["files"]["file"][0]
                return FakeResponse(json_data={"task_id": task_id, "filename": self.elf_name})
            if url.endswith(f"/run/{task_id}"):
                return FakeResponse(json_data={"task_id": task_id, "status": "pending"})
            raise AssertionError(f"Unexpected POST URL: {url}")

        def fake_get(url, *args, **kwargs):
            if url.endswith(f"/status/{task_id}"):
                return FakeResponse(json_data={"task_id": task_id, "status": "completed", "exit_code": 0})
            if url.endswith(f"/output/{task_id}"):
                return FakeResponse(
                    lines=[
                        "data: === Starting gem5 simulation ===",
                        "data: Exiting @ tick 99 because m5_exit instruction encountered",
                        "data: __DONE__",
                    ]
                )
            if url.endswith(f"/download/{task_id}"):
                return FakeResponse(content=tar_bytes)
            raise AssertionError(f"Unexpected GET URL: {url}")

        with patch.object(gem5_prescreener.requests, "post", side_effect=fake_post), patch.object(
            gem5_prescreener.requests, "get", side_effect=fake_get
        ):
            result = gem5_prescreener.run_gem5_prescreen(
                str(self.script_path),
                str(self.artifact_path),
                maxinsts=123,
            )

        artifact_dir = self.artifact_path
        self.assertTrue((artifact_dir / "output.log").exists())
        self.assertTrue((artifact_dir / "manifest.json").exists())
        self.assertTrue((artifact_dir / "m5out.tar.gz").exists())
        self.assertTrue((artifact_dir / "m5out" / "stats.txt").exists())

        manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["script_path"], str(self.script_path.resolve()))
        self.assertEqual(manifest["artifact_path"], str(self.artifact_path.resolve()))
        self.assertEqual(manifest["final_status"], "completed")
        self.assertTrue(manifest["download"]["success"])
        self.assertTrue(manifest["extract"]["success"])
        self.assertEqual(uploaded["filename"], self.elf_name)

        summary = json.loads(result)
        self.assertEqual(summary["status"], "completed")
        self.assertTrue(summary["m5out_downloaded"])
        self.assertTrue(summary["m5out_extracted"])
        self.assertIn("does not run RTL/VCS simulation", summary["note"])

    def test_run_keeps_output_and_manifest_when_download_fails(self):
        task_id = "run-failed-001"

        def fake_post(url, *args, **kwargs):
            if url.endswith("/upload"):
                return FakeResponse(json_data={"task_id": task_id, "filename": self.elf_name})
            if url.endswith(f"/run/{task_id}"):
                return FakeResponse(json_data={"task_id": task_id, "status": "pending"})
            raise AssertionError(f"Unexpected POST URL: {url}")

        def fake_get(url, *args, **kwargs):
            if url.endswith(f"/status/{task_id}"):
                return FakeResponse(json_data={"task_id": task_id, "status": "failed", "exit_code": 7})
            if url.endswith(f"/output/{task_id}"):
                return FakeResponse(lines=["data: runtime failure", "data: __DONE__"])
            if url.endswith(f"/download/{task_id}"):
                raise requests.RequestException("404 Client Error")
            raise AssertionError(f"Unexpected GET URL: {url}")

        with patch.object(gem5_prescreener.requests, "post", side_effect=fake_post), patch.object(
            gem5_prescreener.requests, "get", side_effect=fake_get
        ):
            result = gem5_prescreener.run_gem5_prescreen(str(self.script_path), str(self.artifact_path))

        artifact_dir = self.artifact_path
        manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue((artifact_dir / "output.log").exists())
        self.assertFalse((artifact_dir / "m5out.tar.gz").exists())
        self.assertEqual(manifest["final_status"], "failed")
        self.assertFalse(manifest["download"]["success"])
        self.assertFalse(manifest["extract"]["success"])
        summary = json.loads(result)
        self.assertFalse(summary["m5out_downloaded"])
        self.assertIn("404 Client Error", summary["download_error"])

    def test_reports_missing_script_path(self):
        missing_path = self.input_dir / "missing_iter_1.py"
        result = gem5_prescreener.run_gem5_prescreen(str(missing_path), str(self.artifact_path))
        self.assertIn("path does not exist", result)
        self.assertFalse(self.artifact_path.exists())


if __name__ == "__main__":
    unittest.main()
