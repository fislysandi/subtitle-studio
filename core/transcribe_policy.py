"""Pure policy helpers for transcription retry decisions."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Sequence


@dataclass(frozen=True)
class RecallMetrics:
    """Aggregate recall signals for retry policy decisions."""

    segment_count: int
    speech_duration: float
    word_count: int
    coverage: float


def _segment_duration(segment: Any) -> float:
    start = float(getattr(segment, "start", 0.0) or 0.0)
    end = float(getattr(segment, "end", 0.0) or 0.0)
    return max(0.0, end - start)


def _segment_words(segment: Any) -> int:
    text = str(getattr(segment, "text", "") or "")
    return len(text.split())


def compute_recall_metrics(
    segments: Sequence[Any],
    audio_duration: float,
) -> RecallMetrics:
    """Compute recall metrics from transcription segments."""
    segment_count = len(segments)
    speech_duration = sum(_segment_duration(seg) for seg in segments)
    word_count = sum(_segment_words(seg) for seg in segments)
    safe_audio_duration = max(float(audio_duration or 0.0), 0.001)
    coverage = speech_duration / safe_audio_duration if audio_duration > 0 else 0.0
    return RecallMetrics(
        segment_count=segment_count,
        speech_duration=speech_duration,
        word_count=word_count,
        coverage=coverage,
    )


def is_low_recall(audio_duration: float, metrics: RecallMetrics) -> bool:
    """Determine whether a VAD pass likely missed too much speech."""
    if float(audio_duration or 0.0) < 45.0:
        return False

    return (
        metrics.segment_count < 8 or metrics.word_count < 25 or metrics.coverage < 0.03
    )


def should_retry_without_vad(audio_duration: float, metrics: RecallMetrics) -> bool:
    """Determine whether relaxed VAD results still require no-VAD retry."""
    if float(audio_duration or 0.0) < 45.0:
        return False

    return (
        metrics.segment_count < 8 or metrics.word_count < 25 or metrics.coverage < 0.02
    )


def build_relaxed_vad_parameters(original: Dict[str, Any] | None) -> Dict[str, Any]:
    """Build relaxed VAD parameters for second-pass retry."""
    source = original or {}
    return {
        "threshold": max(0.18, float(source.get("threshold", 0.35)) - 0.1),
        "min_speech_duration_ms": min(
            int(source.get("min_speech_duration_ms", 120)),
            80,
        ),
        "min_silence_duration_ms": min(
            int(source.get("min_silence_duration_ms", 700)),
            350,
        ),
        "max_speech_duration_s": float(source.get("max_speech_duration_s", 15.0)),
        "speech_pad_ms": min(900, int(source.get("speech_pad_ms", 500)) + 200),
    }


def is_candidate_better(baseline: RecallMetrics, candidate: RecallMetrics) -> bool:
    """Return True when candidate offers improved recall."""
    return (
        candidate.word_count > baseline.word_count
        or candidate.speech_duration > baseline.speech_duration
    )
