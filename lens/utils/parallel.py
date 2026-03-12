"""Parallel file scanning utilities."""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

# Use threads for I/O-bound work (file reading), processes for CPU-bound (parsing)
_MAX_WORKERS = min(os.cpu_count() or 4, 8)


def parallel_map(
    func: Callable[[Path], T],
    file_paths: list[Path],
    use_threads: bool = True,
    max_workers: int | None = None,
) -> list[T]:
    """Apply func to each file path in parallel. Returns results in order."""
    workers = max_workers or _MAX_WORKERS

    if len(file_paths) <= 3:
        return [func(p) for p in file_paths]

    executor_cls = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
    results: list[T | None] = [None] * len(file_paths)

    with executor_cls(max_workers=workers) as executor:
        future_to_idx = {executor.submit(func, p): i for i, p in enumerate(file_paths)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = None  # type: ignore[assignment]

    return [r for r in results if r is not None]
