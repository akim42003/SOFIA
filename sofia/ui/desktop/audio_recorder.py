import tempfile
import pyaudio
import wave
from PyQt6.QtCore import QThread, pyqtSignal


class AudioRecorder(QThread):
    """Thread for recording audio input"""
    finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recording = False
        self.frames = []

    def run(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)

        self.recording = True
        self.frames = []

        while self.recording:
            data = stream.read(CHUNK)
            self.frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save audio to temp file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        wf = wave.open(temp_audio.name, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()

        self.finished.emit(temp_audio.name)

    def stop_recording(self):
        self.recording = False