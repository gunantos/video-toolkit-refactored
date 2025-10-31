"""
CLI updates: add options for platforms and TikTok profile selection
"""

import argparse
from typing import List

from rich.console import Console

from core.config import get_config
from core.workflow.manager import WorkflowManager

console = Console()


def main(args=None):
    parser = argparse.ArgumentParser(
        prog="video-toolkit",
        description="Video Toolkit - processing & multi-platform upload",
    )

    sub = parser.add_subparsers(dest="command")

    # Workflow command
    wf = sub.add_parser("workflow", help="Run a workflow preset")
    wf.add_argument("preset", help="Preset key, e.g., full_processing")
    wf.add_argument("source", help="URL/path e.g., https://... or duanju:<id|url>")
    wf.add_argument("--platforms", nargs="*", default=None, help="Override platforms list, e.g., tiktok telegram")
    wf.add_argument("--tiktok-profile", default=None, help="TikTok profile name to use")
    wf.add_argument("--split", type=int, default=None, help="Override split duration in seconds (e.g., 180)")

    # Status command (placeholder)
    sub.add_parser("status", help="Show current status")

    a = parser.parse_args(args=args)

    if a.command == "workflow":
        cfg = get_config()
        # Apply CLI overrides
        options = {}
        if a.platforms:
            options["platforms"] = a.platforms
        if a.split is not None:
            options["split_duration"] = a.split
        if a.tiktok_profile:
            options["tiktok_profile"] = a.tiktok_profile

        manager = WorkflowManager()
        result = manager.execute_workflow(
            preset_key=a.preset,
            video_source=a.source,
            options=options,
        )
        # execute_workflow is async; if not awaited here, assume manager handles run loop
        console.print("Started workflow; check logs for progress.")
        return

    parser.print_help()
