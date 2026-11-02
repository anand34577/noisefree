"""Remove noise from a recording on disk, with the same model and strength as the live mic.

Reads and writes WAV, FLAC, OGG/Vorbis, MP3 and AIFF through libsndfile. Each channel
is cleaned separately at 16 kHz and resampled back, so the file keeps its rate and layout.
"""
import os

import numpy as np
import soundfile as sf
import soxr

from .denoiser import BLOCK_SHIFT, SAMPLE_RATE, Denoiser
from .engine import MODEL_DELAY

EXTENSIONS = ("wav", "flac", "ogg", "mp3", "aiff", "aif")


class Cancelled(Exception):
    pass


def default_output(src):
    """'talk.mp3' -> 'talk (clean).mp3' next to the original."""
    stem, ext = os.path.splitext(src)
    if ext.lower().lstrip(".") not in EXTENSIONS:
        ext = ".wav"
    return f"{stem} (clean){ext}"


def _clean_channel(den, x16, strength, report):
    den.reset()
    n = len(x16)
    padded = np.concatenate((x16, np.zeros(MODEL_DELAY + BLOCK_SHIFT, np.float32)))
    blocks = len(padded) // BLOCK_SHIFT
    out = np.empty(blocks * BLOCK_SHIFT, np.float32)
    for i in range(blocks):
        a = i * BLOCK_SHIFT
        out[a:a + BLOCK_SHIFT] = den.process(padded[a:a + BLOCK_SHIFT])
        if i % 250 == 0:
            report(i / blocks)
    clean = out[MODEL_DELAY:MODEL_DELAY + n]  # undo the model's look-ahead delay
    return strength * clean + (1 - strength) * x16


def clean_file(src, dst, provider="auto", strength=1.0, progress=lambda f: None, cancelled=lambda: False):
    """Write a denoised copy of src to dst. progress gets 0..1; raise Cancelled via cancelled()."""
    try:
        audio, rate = sf.read(src, dtype="float32", always_2d=True)
    except (sf.LibsndfileError, RuntimeError) as e:
        raise ValueError("This file type isn't supported. Use WAV, FLAC, OGG or MP3.") from e
    if not len(audio):
        raise ValueError("The file has no audio in it.")

    den = Denoiser(provider)
    channels = audio.shape[1]
    result = np.empty_like(audio)
    for ch in range(channels):
        def report(f, ch=ch):
            if cancelled():
                raise Cancelled
            progress((ch + f) / channels)
        x16 = soxr.resample(audio[:, ch], rate, SAMPLE_RATE) if rate != SAMPLE_RATE else audio[:, ch]
        y16 = _clean_channel(den, np.ascontiguousarray(x16, np.float32), strength, report)
        y = soxr.resample(y16, SAMPLE_RATE, rate) if rate != SAMPLE_RATE else y16
        result[:, ch] = np.pad(y, (0, max(0, len(audio) - len(y))))[:len(audio)]

    info = sf.info(src)
    fmt = os.path.splitext(dst)[1].lstrip(".").upper()
    fmt = {"AIF": "AIFF", "OGG": "OGG", "MP3": "MP3"}.get(fmt, fmt)
    # Keep the source's sample format when the output type matches, otherwise use the format's default.
    subtype = info.subtype if fmt == info.format and sf.check_format(fmt, info.subtype) else None
    sf.write(dst, np.clip(result, -1.0, 1.0), rate, format=fmt, subtype=subtype)
    progress(1.0)
    return dst
