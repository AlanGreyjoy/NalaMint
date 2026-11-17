"""Capture and transcribe audio in memory with PipeWire/PulseAudio and Whisper."""

from array import array
import io
import math
import os
from pathlib import Path
import shutil
import sys
import wave

from gi.repository import Gio, GLib


RATE = 16000
MAX_SECONDS = 60
MODEL = "ggml-base.en-q5_1.bin"
DATA = Path(GLib.get_user_data_dir()) / "nalamint" / "dictation"


def engine_paths():
    bundled_engine = DATA / "whisper-cli"
    engine = os.environ.get("NALAMINT_WHISPER_CLI")
    if not engine:
        engine = bundled_engine if bundled_engine.is_file() else shutil.which("whisper-cli") or bundled_engine
    model = Path(os.environ.get("NALAMINT_WHISPER_MODEL") or DATA / MODEL).expanduser()
    return Path(engine).expanduser(), model


def level(pcm):
    samples = array("h", pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768


def record():
    return Gio.Subprocess.new(
        ["parec", "--raw", "--format=s16le", f"--rate={RATE}", "--channels=1",
         "--latency-msec=40", "--process-time-msec=20", "--client-name=NalaMint Dictation",
         "--stream-name=Dictation"],
        Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE,
    )


def transcribe(engine, model, pcm, completed):
    wav = io.BytesIO()
    with wave.open(wav, "wb") as audio:
        audio.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        audio.writeframes(pcm)
    process = Gio.Subprocess.new(
        [str(engine), "--model", str(model), "--file", "-", "--no-prints", "--no-timestamps",
         "--suppress-nst", "--threads", str(min(6, os.cpu_count() or 1)),
         "--output-txt", "--output-file", "-"],
        Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE
        | Gio.SubprocessFlags.STDERR_SILENCE,
    )

    def finished(proc, result):
        try:
            _, stdout, _ = proc.communicate_finish(result)
            if proc.get_successful():
                text = " ".join(stdout.get_data().decode("utf-8", "replace").split())
                completed(proc, "" if text in {"[BLANK_AUDIO]", "[ Silence ]"} else text)
                return
        except GLib.Error:
            pass
        completed(proc, None)

    process.communicate_async(GLib.Bytes.new(wav.getvalue()), None, finished)
    return process
