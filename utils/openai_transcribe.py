from __future__ import annotations
from typing import Tuple, Optional
from openai import OpenAI


def transcribe_audio_openai(
    audio_path: str,
    api_key: str,
    language: Optional[str] = "en",
) -> Tuple[str, str]:
    """
    Transcribe audio using OpenAI's Whisper API.
    
    Args:
        audio_path: Path to audio file
        api_key: OpenAI API key
        language: Language code (en, es, etc.) or None for auto-detection
        
    Returns:
        (transcript_text, detected_language)
    """
    if not api_key:
        raise ValueError("OpenAI API key is required")
    
    client = OpenAI(api_key=api_key)
    
    # Determine file format
    valid_formats = ['mp3', 'mp4', 'mpeg', 'mpga', 'wma', 'wav', 'webm', 'm4a', 'aac', 'flac', 'ogg']
    file_format = audio_path.split('.')[-1].lower()
    
    if file_format not in valid_formats:
        raise ValueError(f"Unsupported audio format: {file_format}. Supported: {', '.join(valid_formats)}")
    
    with open(audio_path, 'rb') as audio_file:
        # OpenAI Whisper API call
        if language and language != "auto":
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="json"
            )
        else:
            # Let API auto-detect language
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="json"
            )
    
    text = transcript.text
    # OpenAI doesn't return detected language, so we return a placeholder
    detected_lang = language if language and language != "auto" else "unknown"
    
    return text, detected_lang
