"""
Wire platform strategy and metadata generation into workflow
"""

import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from pathlib import Path

from core.config import get_config
from core.utils.logging import get_logger
from core.constants import WORKFLOW_PRESETS, ProcessingStatus
from core.workflow.steps import WorkflowStepExecutor
from core.workflow.presets import PresetManager
from core.workflow.strategy import apply_platform_strategy, generate_basic_metadata

logger = get_logger(__name__)


class WorkflowContext:
    def __init__(self, video_source: str, options: Dict[str, Any] = None):
        self.video_source = video_source
        self.options = options or {}
        self.config = get_config()
        self.current_step = None
        self.status = ProcessingStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error = None
        self.working_dir: Optional[Path] = None
        self.video_file: Optional[Path] = None
        self.subtitle_files = []
        self.output_files = []
        self.step_results = {}
        self.upload_results = {}
        self.metadata = {}
        self.tiktok_profile = self.options.get("tiktok_profile")

    def add_output_file(self, file_path: Path, file_type: str = "output"):
        from datetime import datetime as _dt
        self.output_files.append({"path": file_path, "type": file_type, "created_at": _dt.now()})


class WorkflowManager:
    def __init__(self):
        self.config = get_config()
        self.step_executor = WorkflowStepExecutor()
        self.preset_manager = PresetManager()

    def execute_workflow(self, preset_key: str, video_source: str, options: Dict[str, Any] = None,
                          progress_callback: Optional[Callable[[str], None]] = None):
        return asyncio.run(self._execute_async(preset_key, video_source, options, progress_callback))

    async def _execute_async(self, preset_key: str, video_source: str, options: Dict[str, Any] = None,
                              progress_callback: Optional[Callable[[str], None]] = None):
        ctx = WorkflowContext(video_source, options)
        wf = WORKFLOW_PRESETS[preset_key]
        # CLI overrides
        if ctx.options.get("platforms"):
            self.config.platforms.enabled_platforms = ctx.options["platforms"]
        if ctx.options.get("split_duration") is not None:
            self.config.processing.split_duration = ctx.options["split_duration"]
        # Working dir
        ctx.working_dir = self._create_workdir(video_source)
        # Platform strategy
        apply_platform_strategy(ctx)
        # Metadata
        ctx.metadata = generate_basic_metadata(video_source, ctx.working_dir)
        # Run steps
        for step in wf["steps"]:
            await self.step_executor.execute_step(step, ctx)
        return {"success": True, "output_files": [f["path"] for f in ctx.output_files], "metadata": ctx.metadata}

    def _create_workdir(self, video_source: str) -> Path:
        root = self.config.paths.output_dir
        root.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = "job_" + ts
        p = root / name
        p.mkdir(parents=True, exist_ok=True)
        return p
