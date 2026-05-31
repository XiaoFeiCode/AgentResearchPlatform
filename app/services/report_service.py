"""
Report Engine service layer — framework-agnostic business logic.

Manages task lifecycle and report generation.
"""

import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# Ensure engines/ and app/ are on Python path
_root = Path(__file__).resolve().parent.parent.parent
for _p in (str(_root / "engines"), str(_root / "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Constants ───────────────────────────────────────────────────────────────

MAX_TASK_HISTORY = 5

# ── Global state ────────────────────────────────────────────────────────────

current_task: Optional["ReportTask"] = None
task_lock = threading.Lock()
tasks_registry: dict[str, "ReportTask"] = {}


def _prune_tasks():
    if len(tasks_registry) > MAX_TASK_HISTORY:
        oldest = sorted(tasks_registry.values(), key=lambda t: t.created_at)
        for t in oldest[:-MAX_TASK_HISTORY]:
            tasks_registry.pop(t.task_id, None)


def _get_task(task_id: str) -> Optional["ReportTask"]:
    with task_lock:
        if current_task and current_task.task_id == task_id:
            return current_task
        return tasks_registry.get(task_id)


def _safe_filename(value: str, fallback: str = "report") -> str:
    sanitized = "".join(c for c in str(value) if c.isalnum() or c in (" ", "-", "_")).strip()
    return sanitized.replace(" ", "_") or fallback


# ── ReportTask ──────────────────────────────────────────────────────────────

class ReportTask:
    """Tracks report generation: status, progress, and output file paths."""

    def __init__(self, query: str, task_id: str, custom_template: str = ""):
        self.task_id = task_id
        self.query = query
        self.custom_template = custom_template
        self.status = "pending"
        self.progress = 0
        self.error_message = ""
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.html_content = ""
        self.report_file_path = ""
        self.report_file_relative_path = ""
        self.report_file_name = ""
        self.state_file_path = ""
        self.ir_file_path = ""
        self.markdown_file_path = ""
        self.markdown_file_name = ""

    def update_status(self, status: str, progress: int | None = None, error_message: str = ""):
        self.status = status
        if progress is not None:
            self.progress = progress
        if error_message:
            self.error_message = error_message
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id, "query": self.query,
            "status": self.status, "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "has_result": bool(self.html_content),
            "report_file_ready": bool(self.report_file_path),
            "report_file_name": self.report_file_name,
            "report_file_path": self.report_file_relative_path or self.report_file_path,
            "state_file_ready": bool(self.state_file_path),
            "state_file_path": self.state_file_path,
            "ir_file_ready": bool(self.ir_file_path),
            "ir_file_path": self.ir_file_path,
            "markdown_file_ready": bool(self.markdown_file_path),
            "markdown_file_name": self.markdown_file_name,
            "markdown_file_path": self.markdown_file_path,
        }


# ── Input file checks ───────────────────────────────────────────────────────

ENGINE_INPUT_DIRS = {
    "insight": "data/report/insight",
    "media": "data/report/media",
    "query": "data/report/query",
}
FORUM_LOG_PATH = "logs/forum.log"


def check_engines_ready() -> dict[str, Any]:
    """Check if engine output files and forum log are ready."""
    found, missing, latest = [], [], {}

    for engine, dirpath in ENGINE_INPUT_DIRS.items():
        if not os.path.isdir(dirpath):
            missing.append(f"{engine}: 目录不存在")
            continue
        md_files = sorted(
            [f for f in os.listdir(dirpath) if f.endswith('.md')],
            key=lambda x: os.path.getmtime(os.path.join(dirpath, x)),
        )
        if md_files:
            found.append(f"{engine}: {len(md_files)} 个文件")
            latest[engine] = os.path.join(dirpath, md_files[-1])
        else:
            missing.append(f"{engine}: 目录中没有 .md 文件")

    forum_ok = os.path.exists(FORUM_LOG_PATH)
    if forum_ok:
        found.append(f"forum: {os.path.basename(FORUM_LOG_PATH)}")
        latest['forum'] = FORUM_LOG_PATH
    else:
        missing.append("forum: 日志文件不存在")

    return {
        'ready': bool(found and forum_ok),
        'files_found': found,
        'missing_files': missing,
        'latest_files': latest,
    }


def _load_input_files(file_paths: dict[str, str]) -> dict[str, Any]:
    """Load engine reports and forum log content."""
    content = {'reports': [], 'forum_logs': ''}
    for engine in ('query', 'media', 'insight'):
        path = file_paths.get(engine)
        try:
            content['reports'].append(open(path, encoding='utf-8').read() if path else "")
        except Exception:
            content['reports'].append("")
    try:
        if 'forum' in file_paths:
            content['forum_logs'] = open(file_paths['forum'], encoding='utf-8').read()
    except Exception:
        pass
    return content


# ── Report generation (background thread) ───────────────────────────────────

def run_report_generation(task: ReportTask, query: str, custom_template: str = ""):
    try:
        task.update_status("running", 5)

        check_result = check_engines_ready()
        if not check_result.get("ready"):
            task.update_status("error", 0,
                               f"输入文件未准备就绪: {check_result.get('missing_files', [])}")
            return

        from engines.ReportEngine.agent import generate_report

        content = _load_input_files(check_result.get("latest_files", {}))

        def stream_handler(event_type: str, payload: dict[str, Any]):
            if event_type == "progress" and "progress" in payload:
                task.update_status("running", int(payload["progress"]))

        generation_result = generate_report(
            query=query,
            reports=content.get("reports", []),
            forum_logs=content.get("forum_logs", ""),
            custom_template=custom_template,
            save_report=True,
            stream_handler=stream_handler,
            report_id=task.task_id,
        )

        if not isinstance(generation_result, dict):
            task.html_content = str(generation_result)
        else:
            saved = generation_result
            task.html_content = saved.get("html_content", "")
            task.report_file_path = saved.get("report_filepath", "")
            task.report_file_relative_path = saved.get("report_relative_path", "")
            task.report_file_name = saved.get("report_filename", "")
            task.state_file_path = saved.get("state_filepath", "")
            task.ir_file_path = saved.get("ir_filepath", "")

        task.update_status("completed", 100)

    except Exception as e:
        logger.exception(f"报告生成过程中发生错误: {e}")
        task.update_status("error", 0, str(e))


# ── Task management ─────────────────────────────────────────────────────────

def create_task(query: str, custom_template: str = "") -> ReportTask:
    global current_task

    with task_lock:
        if current_task and current_task.status == "running":
            raise RuntimeError("已有报告生成任务在运行中")
        if current_task and current_task.status in ("completed", "error"):
            current_task = None

        task_id = f"report_{int(time.time())}"
        task = ReportTask(query, task_id, custom_template)
        current_task = task
        tasks_registry[task_id] = task
        _prune_tasks()

    return task


def start_task_thread(task: ReportTask, query: str, custom_template: str = ""):
    threading.Thread(
        target=run_report_generation, args=(task, query, custom_template),
        daemon=True,
    ).start()


def get_status_dict() -> dict[str, Any]:
    engines_status = check_engines_ready()
    with task_lock:
        task_dict = current_task.to_dict() if current_task else None
    return {
        "initialized": True,
        "engines_ready": engines_status["ready"],
        "files_found": engines_status.get("files_found", []),
        "missing_files": engines_status.get("missing_files", []),
        "current_task": task_dict,
    }


# ── Log management ──────────────────────────────────────────────────────────

def clear_report_log():
    from engines.ReportEngine.utils.config import settings
    log_file = Path(settings.LOG_FILE)
    try:
        log_file.write_text("", encoding="utf-8")
    except FileNotFoundError:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("", encoding="utf-8")


# ── Export helpers ──────────────────────────────────────────────────────────

def export_markdown_for_task(task_id: str) -> dict[str, Any]:
    task = tasks_registry.get(task_id)
    if not task:
        raise LookupError("任务不存在")
    if task.status != "completed":
        raise RuntimeError(f"任务未完成，当前状态: {task.status}")
    if not task.ir_file_path or not os.path.exists(task.ir_file_path):
        raise FileNotFoundError("IR文件不存在，无法生成Markdown")

    with open(task.ir_file_path, encoding="utf-8") as f:
        document_ir = json.load(f)

    from engines.ReportEngine.renderers import MarkdownRenderer
    from engines.ReportEngine.utils.config import settings

    md_text = MarkdownRenderer().render(document_ir, ir_file_path=task.ir_file_path)

    metadata = (document_ir or {}).get("metadata") or {}
    topic = metadata.get("topic") or metadata.get("title") or task.query
    filename = f"report_{_safe_filename(topic)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    output_dir = Path(settings.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / filename
    md_path.write_text(md_text, encoding="utf-8")

    task.markdown_file_path = str(md_path.resolve())
    task.markdown_file_name = filename

    logger.info(f"导出Markdown完成: {md_path}")
    return {"file_path": task.markdown_file_path, "file_name": filename}


def export_pdf_for_task(task_id: str, optimize: bool = True) -> bytes:
    task = tasks_registry.get(task_id)
    if not task:
        raise LookupError("任务不存在")
    if task.status != "completed":
        raise RuntimeError(f"任务未完成，当前状态: {task.status}")
    if not task.ir_file_path or not os.path.exists(task.ir_file_path):
        raise FileNotFoundError("IR文件不存在")

    with open(task.ir_file_path, encoding="utf-8") as f:
        document_ir = json.load(f)

    from engines.ReportEngine.renderers import PDFRenderer
    logger.info(f"开始导出PDF，任务ID: {task_id}，布局优化: {optimize}")
    return PDFRenderer().render_to_bytes(document_ir, optimize_layout=optimize)
