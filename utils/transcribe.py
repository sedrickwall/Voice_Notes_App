from __future__ import annotations
import os
import tempfile
from typing import Tuple, Optional

from pydub import AudioSegment
from faster_whisper import WhisperModel


def _convert_to_wav(input_path: str) -> str:
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    out_fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(out_fd)
    audio.export(out_path, format="wav")
    return out_path


def transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    language: Optional[str] = "en",
) -> Tuple[str, str]:
    """
    Returns: (transcript_text, detected_language)
    Uses faster-whisper locally (free).
    """
    wav_path = _convert_to_wav(audio_path)

    # CPU-only safe defaults. If you have GPU, switch device="cuda"
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        wav_path,
        language=language,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    transcript_lines = []
    for seg in segments:
        transcript_lines.append(seg.text.strip())

    transcript = " ".join([t for t in transcript_lines if t]).strip()
    detected_lang = getattr(info, "language", "unknown")

    try:
        os.remove(wav_path)
    except Exception:
        pass

    return transcript, detected_lang
