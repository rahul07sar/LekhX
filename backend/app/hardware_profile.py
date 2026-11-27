"""Hardware capability inspection for tuning local llama.cpp defaults."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform

from .config import RUNTIME_DIR

HARDWARE_PROFILE_PATH = RUNTIME_DIR / "hardware-profile.json"
HARDWARE_PROFILE_VERSION = 1


@dataclass(frozen=True)
class HardwareRecommendations:
    """Recommended llama.cpp settings derived from host CPU and RAM."""

    threads: int
    context_size: int
    max_tokens: int
    timeout_seconds: int
    gpu_layers: int
    model_name: str
    fallback_model_name: str
    minimum_memory_gb: int


@dataclass(frozen=True)
class HardwareProfile:
    """Persisted host hardware summary used by the desktop runtime."""

    version: int
    detected_at_utc: str
    system: str
    machine: str
    cpu_count: int
    memory_bytes: int | None
    tier: str
    recommendations: HardwareRecommendations

    @property
    def memory_gb(self) -> float | None:
        """Return installed physical memory in GiB when available."""

        if self.memory_bytes is None:
            return None
        return round(self.memory_bytes / (1024**3), 1)

    def to_json_dict(self) -> dict[str, object]:
        """Serialize hardware profile metadata for JSON responses."""

        payload = asdict(self)
        payload["memory_gb"] = self.memory_gb
        return payload


def _detect_memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if isinstance(pages, int) and isinstance(page_size, int) and pages > 0 and page_size > 0:
            return pages * page_size
    except (AttributeError, ValueError, OSError):
        pass
    return None


def detect_hardware_profile() -> HardwareProfile:
    """Compute recommended local inference parameters from host resources."""

    cpu_count = max(1, os.cpu_count() or 2)
    memory_bytes = _detect_memory_bytes()
    memory_gb = (memory_bytes / (1024**3)) if memory_bytes else 4.0

    if memory_gb >= 16:
        tier = "advanced"
        recommendations = HardwareRecommendations(
            threads=min(cpu_count, 8),
            context_size=8192,
            max_tokens=2048,
            timeout_seconds=120,
            gpu_layers=-1,
            model_name="lekhx-1.0.0",
            fallback_model_name="qwen2.5-0.5b",
            minimum_memory_gb=4,
        )
    elif memory_gb >= 8:
        tier = "balanced"
        recommendations = HardwareRecommendations(
            threads=min(cpu_count, 6),
            context_size=4096,
            max_tokens=1536,
            timeout_seconds=120,
            gpu_layers=0,
            model_name="lekhx-1.0.0",
            fallback_model_name="qwen2.5-0.5b",
            minimum_memory_gb=4,
        )
    else:
        tier = "small"
        recommendations = HardwareRecommendations(
            threads=min(cpu_count, 4),
            context_size=2048,
            max_tokens=1024,
            timeout_seconds=120,
            gpu_layers=0,
            model_name="qwen2.5-0.5b",
            fallback_model_name="qwen2.5-0.5b",
            minimum_memory_gb=2,
        )

    return HardwareProfile(
        version=HARDWARE_PROFILE_VERSION,
        detected_at_utc=datetime.now(timezone.utc).isoformat(),
        system=platform.system().lower(),
        machine=platform.machine().lower(),
        cpu_count=cpu_count,
        memory_bytes=memory_bytes,
        tier=tier,
        recommendations=recommendations,
    )


def ensure_hardware_profile() -> HardwareProfile:
    """Detect and cache hardware recommendations under `RUNTIME_DIR`."""

    profile = detect_hardware_profile()
    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        Path(HARDWARE_PROFILE_PATH).write_text(
            json.dumps(profile.to_json_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return profile
