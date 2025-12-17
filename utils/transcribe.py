from __future__ import annotations
import os
import tempfile
from typing import Tuple, Optional

import av
from faster_whisper import WhisperModel


def _convert_to_wav(input_path: str) -> str:
    """Convert audio to WAV format with mono, 16kHz sample rate using PyAV."""
    out_fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(out_fd)
    
    try:
        container = av.open(input_path)
        audio_stream = next(s for s in container.streams if s.type == 'audio')
        
        output_container = av.open(out_path, 'w')
        # Create output stream with mono layout (1 channel)
        output_stream = output_container.add_stream('pcm_s16le', rate=16000)
        
        # Create resampler to convert to mono, 16kHz
        resampler = av.AudioResampler(format='s16', layout='mono')
        
        for frame in container.decode(audio_stream):
            # Resample the frame to mono, 16kHz
            resampled_frames = resampler.resample(frame)
            if resampled_frames:
                for f in resampled_frames:
                    for packet in output_stream.encode(f):
                        output_container.mux(packet)
        
        # Flush remaining packets
        for packet in output_stream.encode():
            output_container.mux(packet)
        
        output_container.close()
    except Exception as e:
        # Clean up on error
        try:
            os.remove(out_path)
        except Exception:
            pass
        raise RuntimeError(f"Failed to convert audio: {e}") from e
    
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
