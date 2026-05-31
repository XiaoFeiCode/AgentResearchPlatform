"""ReportContext — dependency container for ReportEngine graph."""

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

from .core import ChapterStorage, DocumentComposer
from .ir import IRValidator
from .llms import LLMClient
from .renderers import HTMLRenderer
from .utils.config import Settings


class FileCountBaseline:
    """File count baseline manager for checking new engine reports."""
    import os, json
    def __init__(self):
        self.baseline_file = 'logs/report_baseline.json'
        self.baseline_data = self._load()
    def _load(self) -> dict:
        if self.os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file) as f:
                    return self.json.load(f)
            except Exception:
                pass
        return {}
    def _save(self):
        self.os.makedirs(self.os.path.dirname(self.baseline_file), exist_ok=True)
        with open(self.baseline_file, 'w') as f:
            self.json.dump(self.baseline_data, f, ensure_ascii=False, indent=2)
    def initialize_baseline(self, directories: dict) -> dict:
        counts = {}
        for engine, d in directories.items():
            counts[engine] = len([f for f in (self.os.listdir(d) if self.os.path.exists(d) else []) if f.endswith('.md')])
        self.baseline_data = counts
        self._save()
        return counts


@dataclass
class ReportContext:
    llm_client: LLMClient
    config: Settings
    json_rescue_clients: List[Tuple[str, LLMClient]] = field(default_factory=list)
    chapter_storage: ChapterStorage = None
    document_composer: DocumentComposer = None
    validator: IRValidator = None
    renderer: HTMLRenderer = None
    file_baseline: FileCountBaseline = None
    stream_handler: Optional[Callable] = None
    progress_callback: Optional[Callable] = None

    def __post_init__(self):
        if self.chapter_storage is None:
            self.chapter_storage = ChapterStorage(self.config.CHAPTER_OUTPUT_DIR)
        if self.document_composer is None:
            self.document_composer = DocumentComposer()
        if self.validator is None:
            self.validator = IRValidator()
        if self.renderer is None:
            self.renderer = HTMLRenderer()
        if self.file_baseline is None:
            self.file_baseline = FileCountBaseline()
