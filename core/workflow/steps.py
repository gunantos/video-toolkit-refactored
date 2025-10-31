"""
Extend workflow steps to include subtitle pipeline and splitting
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict

from core.config import get_config
from core.utils.logging import get_logger
from downloaders.universal import UniversalDownloader
from processors.subtitle.generator import extract_audio_for_whisper, generate_subtitle_whisper
from processors.subtitle.translator import translate_subtitle_robust
from processors.subtitle.embedder import embed_subtitle_in_video
from processors.video.merger import concat_videos_from_folder, split_video_by_duration

logger = get_logger(__name__)


class WorkflowStepExecutor:
    async def execute_step(self, step_name: str, context) -> Dict[str, Any]:
        start = time.time()
        if step_name == "download":
            await self._download(context)
        elif step_name == "concat":
            await self._concat(context)
        elif step_name == "split_av":
            await self._noop(context)
        elif step_name == "isolate_vocals":
            await self._noop(context)
        elif step_name == "merge_av":
            await self._noop(context)
        elif step_name == "subtitle":
            await self._subtitle(context)
        elif step_name == "translate_subtitle":
            await self._translate(context)
        elif step_name == "embed_subtitle":
            await self._embed(context)
        elif step_name == "split_final":
            await self._split_final(context)
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
        # URL → universal downloader, else treat as path
        if isinstance(context.video_source, str) and context.video_source.startswith("http"):
            downloader = UniversalDownloader(out_dir)
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, downloader.download, context.video_source)
            if file_path:
                context.video_file = Path(file_path)
                context.add_output_file(Path(file_path), "download")
                logger.info(f"Downloaded: {file_path}")
            else:
                raise RuntimeError("Download failed")
        else:
            p = Path(context.video_source)
            if p.exists():
                context.video_file = p
                logger.info(f"Using local source: {p}")
            else:
                raise FileNotFoundError(f"Source not found: {p}")

    async def _concat(self, context):
        # If working dir contains multiple mp4 or a folder provided, concat
        src = context.video_file
        if src and src.is_dir():
            out = context.working_dir / "combined_video.mp4"
            ok = concat_videos_from_folder(src, out)
            if not ok:
                raise RuntimeError("Concatenation failed")
            context.video_file = out
            context.add_output_file(out, "video")
        elif src and src.is_file():
            # No-op for single file
            return

    async def _subtitle(self, context):
        # Extract audio and run Whisper
        video = context.video_file
        if not video or not video.exists():
            raise RuntimeError("No video file for subtitle step")
        temp_audio = context.working_dir / "temp_audio_for_whisper.wav"
        ok = extract_audio_for_whisper(video, temp_audio)
        if not ok:
            raise RuntimeError("Failed to extract audio for Whisper")
        srt = generate_subtitle_whisper(
            temp_audio,
            context.working_dir,
            src_lang=get_config().processing.subtitle_language,
            model=get_config().processing.whisper_model,
        )
        try:
            if temp_audio.exists():
                temp_audio.unlink()
        except Exception:
            pass
        if not srt or not Path(srt).exists():
            raise RuntimeError("Subtitle generation failed")
        context.subtitle_files.append(Path(srt))

    async def _translate(self, context):
        # Translate last generated srt
        if not context.subtitle_files:
            return
        src_srt = context.subtitle_files[-1]
        translated = translate_subtitle_robust(src_srt, context.working_dir, target_lang=get_config().processing.target_language)
        if translated and Path(translated).exists():
            context.subtitle_files.append(Path(translated))

    async def _embed(self, context):
        video = context.video_file
        if not video or not video.exists():
            raise RuntimeError("No video for embedding")
        # Prefer translated if available
        sub = None
        for cand in reversed(context.subtitle_files):
            if Path(cand).exists():
                sub = Path(cand)
                break
        if not sub:
            return
        out = context.working_dir / f"{video.stem}_with_subtitle.mp4"
        ok = embed_subtitle_in_video(video, sub, out, {"font_size": 24})
        if ok:
            context.video_file = out
            context.add_output_file(out, "processed")

    async def _split_final(self, context):
        video = context.video_file
        if not video or not video.exists():
            return
        duration = get_config().processing.split_duration
        if duration:
            out_dir = context.working_dir / "split_parts"
            split_video_by_duration(video, out_dir, duration)
            for f in sorted(out_dir.glob("*.mp4")):
                context.add_output_file(f, "part")

    async def _noop(self, context):
        await asyncio.sleep(0.05)
