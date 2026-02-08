# Subtitle Studio - Faster Whisper Configuration

## Overview

Faster Whisper offers configurable model sizes and decoding knobs. This reference helps you pick the right trade-off for accuracy, speed, and memory inside Blender's constrained environment.

## Model Comparison

| Model | Params | VRAM | Speed | Accuracy | Recommended Use |
|-------|--------|------|-------|----------|-----------------|
| `tiny` | 39M | ~1 GB | Very fast | Low | CPU-only, previews |
| `base` | 74M | ~1 GB | Fast | Medium | Quick drafts, CPU fallback |
| `small` | 244M | ~2 GB | Moderate | Good | Balanced speed/quality |
| `medium` | 769M | ~5 GB | Slow | High | Detailed transcripts (GPU) |
| `large-v3` | 1550M | ~8 GB | Very slow | Best | Highest-quality, GPU only |

## Recommended Configurations

- **Best balance (English)**: `model = "distil-medium.en"` or `"medium.en"` with default beam sizes.
- **Fastest (English)**: `model = "base.en"` with `beam_size=1`.
- **Highest quality (multi-language)**: `model = "large-v3"` with `beam_size=5` and `vad_filter=True`.
- **Low memory / CPU-only**: `model = "tiny"` with `compute_type="int8"` and minimal beams.

## Transcription Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `beam_size` | `int` | 5 | Higher beam counts boost accuracy at the cost of speed.
| `best_of` | `int` | 5 | Candidates sampled when temperature variants are active.
| `temperature` | `float` | 0.0 | Raise for creative outputs, keep at 0 for deterministic transcripts.
| `compression_ratio_threshold` | `float` | 2.4 | Skip overly compressed audio segments.
| `log_prob_threshold` | `float` | -1.0 | Skip low-confidence segments.
| `no_speech_threshold` | `float` | 0.6 | Avoid false positives when silence is detected.
| `vad_filter` | `bool` | `False` | Enable VAD to drop noise segments.
| `language` | `str` | `None` | Set ISO code to force language, otherwise auto-detect.

## VAD Parameters

```python
vad_parameters = {
    "threshold": 0.5,
    "min_speech_duration_ms": 250,
    "max_speech_duration_s": float("inf"),
    "min_silence_percentage_ms": 15,
    "speech_pad_ms": 0,
}
```

## Output Structure

Each segment returned by `model.transcribe()` includes:

- `segment.start` (float seconds)
- `segment.end` (float seconds)
- `segment.text` (transcribed string)
- `segment.tokens` (`list[int]` token IDs)
- `segment.probability` (float average probability)

Process segments with a simple loop to convert seconds to frames or milliseconds before creating subtitle cues.

## Language Codes

Most ISO codes are supported (`en`, `zh`, `fr`, `de`, `es`, `it`, `ja`, `ko`, `pt`, `ru`, `ar`, `hi`). Omit the `language` parameter to let the model auto-detect.

## Related
- `README.md` (usage and quick start)
- `docs/dev.md` (development workflow)
- `docs/dependencies.md` (bundled libs reference)
