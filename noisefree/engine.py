"""Audio routing: mic -> 16 kHz -> denoiser -> virtual cable (+ optional monitor).

Each device runs its own stream at its native rate; soxr converts to and from
the model's 16 kHz, and a small FIFO per output absorbs clock drift between
devices. The router keeps running while noise removal is switched off (raw
audio passes through), so meeting apps never lose the microphone.
"""
import threading

import numpy as np
import sounddevice as sd
import soxr

from . import devices
from .denoiser import BLOCK_LEN, BLOCK_SHIFT, SAMPLE_RATE, Denoiser

# DTLN output lags its input by one window minus one hop.
MODEL_DELAY = BLOCK_LEN - BLOCK_SHIFT


class Fifo:
    """Thread-safe sample queue that keeps latency between `prefill` and `limit` seconds."""

    def __init__(self, rate, prefill=0.03, limit=0.15):
        self.buf = np.zeros(0, np.float32)
        self.lock = threading.Lock()
        self.prefill = int(rate * prefill)
        self.limit = int(rate * limit)
        self.primed = False

    def push(self, x):
        with self.lock:
            self.buf = np.concatenate((self.buf, x))
            if len(self.buf) > self.limit:
                self.buf = self.buf[-self.prefill:]

    def pull(self, n):
        with self.lock:
            if not self.primed:
                if len(self.buf) < self.prefill:
                    return np.zeros(n, np.float32)
                self.primed = True
            out, self.buf = self.buf[:n], self.buf[n:]
            if len(out) < n:
                self.primed = False  # underrun: rebuild the cushion
                out = np.pad(out, (0, n - len(out)))
            return out


class Output:
    def __init__(self, dev, on_lost):
        self.fifo = Fifo(dev.rate)
        self.rs = None if dev.rate == SAMPLE_RATE else soxr.ResampleStream(SAMPLE_RATE, dev.rate, 1, dtype="float32")
        ch = min(2, dev.channels)
        self.stream = devices.open_stream(sd.OutputStream, dev, channels=ch, callback=self._cb,
                                          finished_callback=on_lost)
        self.stream.start()

    def push(self, x16):
        self.fifo.push(self.rs.resample_chunk(x16) if self.rs else x16)

    def _cb(self, outdata, frames, t, status):
        outdata[:] = self.fifo.pull(frames)[:, None]

    def close(self):
        self.stream.abort()
        self.stream.close()


def _rms(x):
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0


class Engine:
    def __init__(self):
        self.denoiser = None
        self.enabled = True
        self.strength = 1.0
        self.level_in = 0.0
        self.level_out = 0.0
        self.error = None       # "mic" | "cable" | "monitor" when a device disappears
        self.running = False
        self._mic = None
        self._cable = None
        self._monitor = None
        self._rs_in = None
        self._stopping = False

    # ---- model

    def load_model(self, provider):
        """Load on the requested provider, falling back to CPU. Returns (provider, fell_back)."""
        try:
            d = Denoiser(provider)
            fell_back = provider not in ("auto", "CPUExecutionProvider") and d.provider == "CPUExecutionProvider"
        except Exception:
            d, fell_back = Denoiser("CPUExecutionProvider"), provider != "CPUExecutionProvider"
        self.denoiser = d  # swapped atomically; the audio thread picks it up on the next block
        return d.provider, fell_back

    # ---- streams

    def start(self, mic, cable, monitor=None):
        self.stop()
        self.error = None
        self._stopping = False
        self._pending = np.zeros(0, np.float32)
        self._dry = np.zeros(MODEL_DELAY, np.float32)
        self._was_on = False
        self._rs_in = (None if mic.rate == SAMPLE_RATE
                       else soxr.ResampleStream(mic.rate, SAMPLE_RATE, 1, dtype="float32"))
        try:
            if cable:
                self._cable = Output(cable, lambda: self._lost("cable"))
            if monitor:
                self._monitor = Output(monitor, lambda: self._lost("monitor"))
            self._mic = devices.open_stream(sd.InputStream, mic, channels=1, callback=self._on_input,
                                            finished_callback=lambda: self._lost("mic"))
            self._mic.start()
        except Exception:
            self.stop()
            raise
        self.running = True

    def set_monitor(self, dev):
        old, self._monitor = self._monitor, None
        if old:
            self._stopping = True
            old.close()
            self._stopping = False
        if dev and self.running:
            self._monitor = Output(dev, lambda: self._lost("monitor"))

    def stop(self):
        self._stopping = True
        for s in (self._mic,):
            if s:
                s.abort()
                s.close()
        for o in (self._cable, self._monitor):
            if o:
                o.close()
        self._mic = self._cable = self._monitor = self._rs_in = None
        self.running = False
        self.level_in = self.level_out = 0.0

    def _lost(self, which):
        if not self._stopping:
            self.error = which

    # ---- audio thread

    def _on_input(self, indata, frames, t, status):
        x = indata[:, 0]
        x16 = self._rs_in.resample_chunk(x) if self._rs_in else x.copy()
        pending = np.concatenate((self._pending, x16))
        n = len(pending) // BLOCK_SHIFT * BLOCK_SHIFT
        self._pending = pending[n:]
        if not n:
            return
        chunk = pending[:n]
        # Delay the raw signal so the dry/wet blend lines up with the model's output.
        hist = np.concatenate((self._dry, chunk))
        dry, self._dry = hist[:n], hist[n:]

        d, s = self.denoiser, self.strength
        on = bool(d and self.enabled and s > 0)
        if on and not self._was_on:
            d.reset()  # model state is stale after a pause
        self._was_on = on
        if on:
            wet = np.concatenate([d.process(chunk[i:i + BLOCK_SHIFT]) for i in range(0, n, BLOCK_SHIFT)])
            out = s * wet + (1 - s) * dry
        else:
            out = dry

        self.level_in = _rms(chunk)
        self.level_out = _rms(out)
        for o in (self._cable, self._monitor):
            if o:
                o.push(out)
