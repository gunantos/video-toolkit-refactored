"""
Logging utilities for Video Toolkit
"""

import logging
import sys
from pathlib import Path

from core.config import get_config


def setup_logging():
    cfg = get_config()
    log_level = getattr(logging, cfg.get('logging', {}).get('level', 'INFO').upper(), logging.INFO)
    log_format = cfg.get('logging', {}).get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = cfg.get('logging', {}).get('file', 'data/logs/video-toolkit.log')

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8')
        ],
    )
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
