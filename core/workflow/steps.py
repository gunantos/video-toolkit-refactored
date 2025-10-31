"""
Workflow steps executor (skeleton)
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict

from core.config import get_config
from core.utils.logging import get_logger
from downloaders.universal import UniversalDownloader

logger = get_logger(__name__)


class WorkflowStepExecutor:
    async def execute_step(self, step_name: str, context) -> Dict[str, Any]:
        start = time.time()
        if step_name == "download":
            await self._download(context)
        elif step_name == "concat":
            await self._noop(context)
        elif step_name == "split_av":
            await self._noop(context)
        elif step_name == "isolate_vocals":
            await self._noop(context)
        elif step_name == "merge_av":
            await self._noop(context)
        elif step_name == "subtitle":
            await self._noop(context)
        elif step_name == "translate_subtitle":
            await self._noop(context)
        elif step_name == "embed_subtitle":
            await self._noop(context)
        elif step_name == "split_final":
            await self._noop(context)
        elif step_name == "watermark":
            await self._noop(context)
        elif step_name == "upload":
            await self._noop(context)
        else:
            raise ValueError(f"Unknown step: {step_name}")
        return {"execution_time": time.time() - start}

    async def _download(self, context):
        cfg = get_config()
        out_dir = context.working_dir or cfg.paths.output_dir
        # basic: url only -> use universal
        if context.video_source.startswith("http"):
            downloader = UniversalDownloader(out_dir)
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, downloader.download, context.video_source)
            if file_path:
                context.video_file = file_path
                context.add_output_file(Path(file_path), "download")
                logger.info(f"Downloaded: {file_path}")
            else:
                raise RuntimeError("Download failed")
        else:
            # file/folder path provided
            p = Path(context.video_source)
            if p.exists():
                context.video_file = p
                logger.info(f"Using local source: {p}")
            else:
                raise FileNotFoundError(f"Source not found: {p}")

    async def _noop(self, context):
        await asyncio.sleep(0.1)
