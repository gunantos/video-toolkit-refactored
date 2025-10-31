"""
Workflow presets helper
"""

from typing import Dict

from core.constants import WORKFLOW_PRESETS


class PresetManager:
    def list_presets(self) -> Dict:
        return WORKFLOW_PRESETS

    def get(self, key: str) -> Dict:
        return WORKFLOW_PRESETS[key]
