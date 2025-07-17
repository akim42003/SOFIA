"""Audio processing and Whisper model management for SOFIA web interface."""

import os
from pathlib import Path
import shutil

try:
    import whisper
    WHISPER_AVAILABLE = True
    whisper_model = None  # Will be loaded lazily when first needed
    print("Whisper available - model will load on first audio request")
except ImportError:
    WHISPER_AVAILABLE = False
    whisper_model = None
    print("Warning: Whisper not available. Audio functionality disabled.")


def load_whisper_model():
    """Lazy load the Whisper model when first needed"""
    global whisper_model

    if whisper_model is not None:
        return whisper_model

    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        models_dir = script_dir / "models"
        local_model_path = models_dir / "small.en.pt"

        # Create models directory if it doesn't exist
        models_dir.mkdir(exist_ok=True)

        # Check if we already have the model locally
        if local_model_path.exists():
            print(f"Loading Whisper model from: {local_model_path}")
            whisper_model = whisper.load_model(str(local_model_path))
            print("Whisper model loaded from local file!")
            return whisper_model

        # Download model to default cache first
        print("Downloading Whisper small.en model (first time only)...")
        temp_model = whisper.load_model("small.en")

        # Find the cached model file
        cache_dir = Path.home() / ".cache" / "whisper"
        cached_model = cache_dir / "small.en.pt"

        if cached_model.exists():
            # Copy to our local models directory
            print(f"Copying model to: {local_model_path}")
            shutil.copy2(cached_model, local_model_path)
            print(f"Model saved locally! Size: {local_model_path.stat().st_size / (1024*1024):.1f} MB")

            # Load from our local copy
            whisper_model = whisper.load_model(str(local_model_path))
        else:
            # Fallback to the temp model
            whisper_model = temp_model
            print("Could not save model locally, using cache version")

        return whisper_model

    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return None


def process_audio(audio_file):
    """Process audio file and transcribe to text using Whisper"""
    if not WHISPER_AVAILABLE or not audio_file:
        return ""

    try:
        # Handle different file input types
        if hasattr(audio_file, 'name'):
            file_path = audio_file.name
        elif isinstance(audio_file, str):
            file_path = audio_file
        else:
            print(f"Error: Invalid audio file type: {type(audio_file)}")
            return ""

        # Verify it's actually a file
        if not os.path.isfile(file_path):
            print(f"Error: Not a valid file: {file_path}")
            return ""

        # Lazy load the model when first needed
        model = load_whisper_model()
        if model is None:
            return ""

        # Transcribe the audio file
        result = model.transcribe(file_path)
        transcribed_text = result["text"].strip()

        return transcribed_text
    except Exception as e:
        print(f"Error processing audio: {e}")
        return ""
