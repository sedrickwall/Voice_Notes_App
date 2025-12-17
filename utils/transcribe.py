from __future__ import annotations
import os
import tempfile
from typing import Tuple, Optional

import av
from faster_whisper import WhisperModel


def _get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds."""
    try:
        container = av.open(audio_path)
        audio_stream = next((s for s in container.streams if s.type == 'audio'), None)
        if audio_stream and audio_stream.duration and audio_stream.time_base:
            return float(audio_stream.duration * audio_stream.time_base)
    except Exception:
        pass
    return 0


def _convert_to_wav(input_path: str) -> str:
    """Convert audio to WAV format with mono, 16kHz sample rate using PyAV."""
    out_fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(out_fd)
    
    try:
        container = av.open(input_path)
        audio_stream = next((s for s in container.streams if s.type == 'audio'), None)
        
        if audio_stream is None:
            raise ValueError("No audio stream found in file")
        
        output_container = av.open(out_path, 'w')
        output_stream = output_container.add_stream('pcm_s16le', rate=16000)
        
        # Create resampler to convert to mono, 16kHz
        resampler = av.AudioResampler(format='s16', layout='mono')
        
        frame_count = 0
        for frame in container.decode(audio_stream):
            # Resample the frame to mono, 16kHz
            resampled_frames = resampler.resample(frame)
            if resampled_frames:
                for f in resampled_frames:
                    for packet in output_stream.encode(f):
                        output_container.mux(packet)
                    frame_count += 1
        
        # Flush remaining packets
        for packet in output_stream.encode():
            output_container.mux(packet)
        
        output_container.close()
        
        if frame_count == 0:
            raise ValueError("No audio frames were processed")
            
    except Exception as e:
        # Clean up on error
        try:
            os.remove(out_path)
        except Exception:
            pass
        raise RuntimeError(f"Failed to convert audio: {e}") from e
    
    return out_path


def _chunk_audio(wav_path: str, chunk_duration_seconds: int = 1200) -> list[str]:
    """
    Split audio into chunks of specified duration.
    Default: 20 minutes (1200 seconds) per chunk.
    Returns list of chunk file paths.
    """
    chunks = []
    try:
        container = av.open(wav_path)
        audio_stream = next((s for s in container.streams if s.type == 'audio'), None)
        
        if audio_stream is None:
            return [wav_path]
        
        # Calculate total duration
        total_duration = _get_audio_duration(wav_path)
        if total_duration <= chunk_duration_seconds:
            return [wav_path]
        
        num_chunks = int((total_duration / chunk_duration_seconds) + 1)
        
        for chunk_idx in range(num_chunks):
            out_fd, chunk_path = tempfile.mkstemp(suffix=".wav")
            os.close(out_fd)
            
            start_time = chunk_idx * chunk_duration_seconds
            end_time = min((chunk_idx + 1) * chunk_duration_seconds, total_duration)
            
            output_container = av.open(chunk_path, 'w')
            output_stream = output_container.add_stream('pcm_s16le', rate=16000)
            
            resampler = av.AudioResampler(format='s16', layout='mono')
            
            for frame in container.decode(audio_stream):
                if frame.pts is None:
                    continue
                frame_time = float(frame.pts * audio_stream.time_base)
                
                if frame_time >= end_time:
                    break
                if frame_time < start_time:
                    continue
                
                resampled_frames = resampler.resample(frame)
                if resampled_frames:
                    for f in resampled_frames:
                        for packet in output_stream.encode(f):
                            output_container.mux(packet)
            
            for packet in output_stream.encode():
                output_container.mux(packet)
            
            output_container.close()
            chunks.append(chunk_path)
        
        return chunks
    except Exception as e:
        # On error, return original file
        return [wav_path]


def transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    language: Optional[str] = "en",
) -> Tuple[str, str]:
    """
    Returns: (transcript_text, detected_language)
    Uses faster-whisper locally (free). Automatically chunks large files.
    """
    wav_path = _convert_to_wav(audio_path)
    
    # Check if chunking is needed (for files > 20 minutes)
    duration = _get_audio_duration(wav_path)
    chunk_duration = 1200  # 20 minutes
    
    if duration > chunk_duration:
        # Chunk the audio
        chunks = _chunk_audio(wav_path, chunk_duration)
    else:
        chunks = [wav_path]

    # CPU-only safe defaults. If you have GPU, switch device="cuda"
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    transcript_lines = []
    detected_lang = "unknown"
    
    try:
        for chunk_path in chunks:
            segments, info = model.transcribe(
                chunk_path,
                language=language,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            for seg in segments:
                transcript_lines.append(seg.text.strip())
            
            detected_lang = getattr(info, "language", "unknown")
            
            # Clean up chunk if it's not the original file
            if chunk_path != wav_path:
                try:
                    os.remove(chunk_path)
                except Exception:
                    pass
    finally:
        # Clean up WAV conversion
        try:
            os.remove(wav_path)
        except Exception:
            pass

    transcript = " ".join([t for t in transcript_lines if t]).strip()
    detected_lang = getattr(info, "language", "unknown")

    try:
        os.remove(wav_path)
    except Exception:
        pass

    return transcript, detected_lang
