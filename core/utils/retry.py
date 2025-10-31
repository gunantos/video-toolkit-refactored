"""
Retry helpers for resilient operations
"""

import asyncio
import time
from typing import Callable, Coroutine, Type, Tuple


def retry_sync(func: Callable, retries: int = 3, delay: float = 2.0, exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    for attempt in range(1, retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt == retries:
                raise
            time.sleep(delay)


async def retry_async(coro_func: Callable[..., Coroutine], *args, retries: int = 3, delay: float = 2.0, exceptions: Tuple[Type[Exception], ...] = (Exception,), **kwargs):
    for attempt in range(1, retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except exceptions:
            if attempt == retries:
                raise
            await asyncio.sleep(delay)
