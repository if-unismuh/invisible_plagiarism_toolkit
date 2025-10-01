from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

ROOT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ORIGINAL = ROOT_DIR / "workspace" / "input" / "original"
WORKSPACE_TURNITIN = ROOT_DIR / "workspace" / "input" / "turnitin"
ACCEPTED_DOC_SUFFIXES = {".docx"}


class JobState:
    def __init__(self, job_id: str, mode: str) -> None:
        self.job_id = job_id
        self.mode = mode
        self.status = "queued"
        self.detail = "Menunggu pemrosesan"
        self.result: Dict[str, Any] | None = None
        self.error: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "mode": self.mode,
            "status": self.status,
            "detail": self.detail,
            "result": self.result,
            "error": self.error,
        }


_jobs: Dict[str, JobState] = {}
_jobs_lock = threading.Lock()

app = FastAPI(title="Invisible Plagiarism Toolkit Portal", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def ensure_workspace() -> None:
    for directory in (WORKSPACE_ORIGINAL, WORKSPACE_TURNITIN):
        directory.mkdir(parents=True, exist_ok=True)


@app.post("/api/process")
async def process_documents(
    background_tasks: BackgroundTasks,
    original_doc: UploadFile = File(...),
    turnitin_pdf: UploadFile = File(...),
    mode: str = Form("balanced"),
) -> JSONResponse:
    mode = mode.lower().strip()
    if mode not in {"stealth", "balanced", "aggressive"}:
        raise HTTPException(status_code=400, detail="Mode tidak dikenali. Gunakan stealth, balanced, atau aggressive.")

    if not original_doc.filename:
        raise HTTPException(status_code=400, detail="File dokumen asli tidak valid.")
    if not turnitin_pdf.filename:
        raise HTTPException(status_code=400, detail="File PDF Turnitin tidak valid.")

    original_suffix = Path(original_doc.filename).suffix.lower()
    if original_suffix not in ACCEPTED_DOC_SUFFIXES:
        raise HTTPException(status_code=400, detail="Dokumen harus bertipe DOCX.")

    pdf_suffix = Path(turnitin_pdf.filename).suffix.lower()
    if pdf_suffix != ".pdf":
        raise HTTPException(status_code=400, detail="Laporan Turnitin harus berformat PDF.")

    job_id = uuid.uuid4().hex
    doc_target = WORKSPACE_ORIGINAL / f"{job_id}{original_suffix}"
    pdf_target = WORKSPACE_TURNITIN / f"{job_id}{pdf_suffix}"

    # Persist files to disk
    try:
        await save_upload(original_doc, doc_target)
        await save_upload(turnitin_pdf, pdf_target)
    except Exception as exc:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan file: {exc}") from exc

    job = JobState(job_id, mode)
    with _jobs_lock:
        _jobs[job_id] = job

    background_tasks.add_task(run_job, job, doc_target, pdf_target)

    return JSONResponse({"job_id": job_id, "status": job.status, "detail": job.detail})


@app.get("/api/status/{job_id}")
async def get_status(job_id: str) -> JSONResponse:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
    return JSONResponse(job.to_dict())


async def save_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Bersihkan file lama di folder target agar CLI memilih unggahan terbaru
    await purge_existing(destination.parent, destination.suffix)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, upload.file.seek, 0)
    with destination.open("wb") as buffer:
        await loop.run_in_executor(None, shutil.copyfileobj, upload.file, buffer)
    await upload.close()


async def purge_existing(directory: Path, suffix: str) -> None:
    loop = asyncio.get_running_loop()

    def _purge() -> None:
        for item in directory.glob(f"*{suffix}"):
            try:
                item.unlink()
            except FileNotFoundError:
                continue

    await loop.run_in_executor(None, _purge)


def run_job(job: JobState, doc_path: Path, pdf_path: Path) -> None:
    update_job(job, status="processing", detail="Menjalankan pipeline CLI...")

    cmd = [
        sys.executable,
        "main.py",
        "--mode",
        job.mode,
    ]

    env = os.environ.copy()
    env["IPT_JOB_ID"] = job.job_id

    progress: Dict[str, Any] = {
        "current": "Menjalankan pipeline CLI...",
        "history": [
            {
                "message": "Menjalankan pipeline CLI...",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ],
    }
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def push_update(detail: str) -> None:
        update_job(
            job,
            status="processing",
            detail=detail,
            result={
                "stdout": "".join(stdout_lines[-200:]),
                "stderr": "".join(stderr_lines[-80:]),
                "progress": progress,
            },
        )

    try:
        with subprocess.Popen(
            cmd,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        ) as proc:
            assert proc.stdout is not None
            assert proc.stderr is not None

            while True:
                line = proc.stdout.readline()
                if line:
                    stdout_lines.append(line)
                    step = _infer_progress_step(line)
                    if step:
                        progress["current"] = step
                        progress["history"].append({
                            "message": step,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        })
                        push_update(step)
                if proc.poll() is not None:
                    for leftover in proc.stdout.readlines():
                        stdout_lines.append(leftover)
                    break

            stderr_lines.extend(proc.stderr.readlines())
            return_code = proc.wait()

        summary_path = ROOT_DIR / "workspace" / "output" / "analysis" / f"analysis_summary_{job.job_id}.json"
        priority_path = ROOT_DIR / "workspace" / "output" / "analysis" / f"priority_segments_{job.job_id}.json"
        analysis_summary = None
        files_payload: Dict[str, Any] = {}
        if summary_path.exists():
            try:
                analysis_summary = json.loads(summary_path.read_text(encoding="utf-8"))
                files_payload = {
                    "original_pdf": f"/api/jobs/{job.job_id}/files/pdf",
                    "processed_document": f"/api/jobs/{job.job_id}/files/processed",
                    "report": f"/api/jobs/{job.job_id}/files/report",
                    "analysis": f"/api/jobs/{job.job_id}/files/analysis",
                }
                if priority_path.exists():
                    files_payload["priority_segments"] = f"/api/jobs/{job.job_id}/files/priority"
            except json.JSONDecodeError:
                analysis_summary = None
        if "processed_document" not in files_payload:
            try:
                fallback_processed = _guess_processed_path(job.job_id, job.mode)
            except FileNotFoundError:
                fallback_processed = None
            if fallback_processed is not None:
                files_payload["processed_document"] = f"/api/jobs/{job.job_id}/files/processed"

        if return_code == 0:
            progress["current"] = "Pipeline selesai tanpa error."
            progress["history"].append({
                "message": "Pipeline selesai tanpa error.",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            update_job(
                job,
                status="completed",
                detail="Pipeline selesai tanpa error.",
                result={
                    "stdout": "".join(stdout_lines[-400:]),
                    "stderr": "".join(stderr_lines[-200:]),
                    "doc_path": str(doc_path),
                    "pdf_path": str(pdf_path),
                    "analysis_summary": analysis_summary,
                    "files": files_payload,
                    "progress": progress,
                },
            )
        else:
            update_job(
                job,
                status="failed",
                detail="Pipeline mengembalikan kode error.",
                result={
                    "stdout": "".join(stdout_lines[-400:]),
                    "stderr": "".join(stderr_lines[-200:]),
                    "progress": progress,
                },
                error="".join(stderr_lines[-400:]) or "Terjadi kesalahan."
            )
    except Exception as exc:  # pragma: no cover - safety net
        update_job(job, status="failed", detail="Eksekusi pipeline gagal.", error=str(exc))


def _infer_progress_step(line: str) -> str | None:
    text = line.lower()
    mapping = [
        ("converting pdf", "Menjalankan OCR (ocrmypdf)..."),
        ("ocr fallback", "Menjalankan OCR fallback bahasa Inggris..."),
        ("extracting highlights", "Menganalisis highlight berwarna..."),
        ("extracted", "Highlight berhasil diekstraksi."),
        ("filtered to", "Menyusun segmen prioritas dari highlight."),
        ("applying targeted invisible manipulations", "Mengaplikasikan manipulasi pada segmen terpilih."),
        ("document processed successfully", "Mengaplikasikan manipulasi tak terlihat."),
        ("report generated", "Menyusun laporan hasil dan laporan JSON."),
        ("analysis summary saved", "Menyimpan ringkasan highlight terpilih."),
    ]
    for key, label in mapping:
        if key in text:
            return label
    return None


def update_job(job: JobState, *, status: str, detail: str, result: Dict[str, Any] | None = None, error: str | None = None) -> None:
    job.status = status
    job.detail = detail
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
    with _jobs_lock:
        _jobs[job.job_id] = job




@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT_DIR / "web" / "index.html")


@app.get("/result")
async def result_view() -> FileResponse:
    return FileResponse(ROOT_DIR / "web" / "result.html")


@app.get("/flags")
async def flags_view() -> FileResponse:
    return FileResponse(ROOT_DIR / "web" / "flags.html")


def _load_summary(job_id: str) -> Dict[str, Any]:
    summary_path = ROOT_DIR / "workspace" / "output" / "analysis" / f"analysis_summary_{job_id}.json"
    if not summary_path.exists():
        raise FileNotFoundError
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FileNotFoundError from exc


def _resolve_summary_path(job_id: str, key: str) -> Path:
    data = _load_summary(job_id)
    relative = data.get(key)
    if not relative:
        raise FileNotFoundError
    path = (ROOT_DIR / relative).resolve()
    if not path.exists() or ROOT_DIR not in path.parents and path != ROOT_DIR:
        raise FileNotFoundError
    return path


def _guess_processed_path(job_id: str, mode: str | None) -> Path:
    processed_dir = ROOT_DIR / "workspace" / "output" / "processed"
    candidates: list[Path] = []
    if mode:
        candidates.append(processed_dir / f"{job_id}_{mode}_processed.docx")
    candidates.extend(sorted(processed_dir.glob(f"{job_id}_*_processed.docx")))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError


def _guess_changes_path(job_id: str) -> Path:
    """Find change log JSON file for a job"""
    processed_dir = ROOT_DIR / "workspace" / "output" / "processed"
    
    # Common patterns for change log files
    patterns = [
        f"{job_id}_*_processed.changes.json",
        f"*_{job_id}_*.changes.json", 
        f"{job_id}*.changes.json",
        f"changes_{job_id}.json",
        f"{job_id}_changes.json",
    ]
    
    for pattern in patterns:
        candidates = list(processed_dir.glob(pattern))
        if candidates:
            # Return the most recent one
            return max(candidates, key=lambda p: p.stat().st_mtime)
    
    # Also check logs directory
    logs_dir = ROOT_DIR / "logs"
    if logs_dir.exists():
        for pattern in patterns:
            candidates = list(logs_dir.glob(pattern))
            if candidates:
                return max(candidates, key=lambda p: p.stat().st_mtime)
    
    raise FileNotFoundError


def _guess_analysis_path(job_id: str) -> Path:
    """Find analysis report file for a job"""
    processed_dir = ROOT_DIR / "workspace" / "output" / "processed"
    
    # Common patterns for analysis files
    patterns = [
        f"{job_id}_*_analysis.json",
        f"{job_id}_analysis.json",
        f"analysis_{job_id}.json",
        f"{job_id}_*_report.json",
        f"{job_id}_report.json",
        f"report_{job_id}.json",
    ]
    
    for pattern in patterns:
        candidates = list(processed_dir.glob(pattern))
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_mtime)
    
    # Also check logs directory
    logs_dir = ROOT_DIR / "logs"
    if logs_dir.exists():
        for pattern in patterns:
            candidates = list(logs_dir.glob(pattern))
            if candidates:
                return max(candidates, key=lambda p: p.stat().st_mtime)
    
    raise FileNotFoundError


@app.get("/api/jobs/{job_id}/files/{file_type}")
async def download_job_file(job_id: str, file_type: str) -> FileResponse:
    key_map = {
        "pdf": "original_pdf",
        "processed": "processed_document",
        "report": "report",
        "analysis": None,
        "priority": "priority_segments_file",
        "changes": None,  # Change log JSON
        "changelog": None,  # Alternative name
    }
    if file_type not in key_map:
        raise HTTPException(status_code=404, detail="Jenis file tidak dikenal.")
    
    if file_type == "analysis":
        try:
            path = _guess_analysis_path(job_id)
        except FileNotFoundError:
            # Fallback to default analysis path
            path = ROOT_DIR / "workspace" / "output" / "analysis" / f"analysis_summary_{job_id}.json"
    elif file_type in ["changes", "changelog"]:
        # Look for change log JSON file
        path = _guess_changes_path(job_id)
    else:
        try:
            path = _resolve_summary_path(job_id, key_map[file_type])
        except FileNotFoundError:
            if file_type == "processed":
                with _jobs_lock:
                    job = _jobs.get(job_id)
                mode = job.mode if job else None
                try:
                    path = _guess_processed_path(job_id, mode)
                except FileNotFoundError as exc:
                    raise HTTPException(status_code=404, detail="File tidak ditemukan.") from exc
            else:
                raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    if not path.exists():
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    return FileResponse(path)


@app.get("/api/jobs/{job_id}/summary")
async def job_summary(job_id: str) -> JSONResponse:
    try:
        data = _load_summary(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ringkasan tidak ditemukan.")
    return JSONResponse(data)
