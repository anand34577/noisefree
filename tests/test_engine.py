import numpy as np

from noisefree.denoiser import BLOCK_SHIFT, SAMPLE_RATE
from noisefree.engine import MODEL_DELAY, Engine, Fifo


def test_fifo_waits_for_prefill_then_plays():
    f = Fifo(1000, prefill=0.05, limit=0.5)  # 50-sample cushion
    f.push(np.ones(30, np.float32))
    assert not f.pull(10).any()  # still filling
    f.push(np.ones(30, np.float32))
    assert f.pull(10).all()


def test_fifo_trims_runaway_latency():
    f = Fifo(1000, prefill=0.05, limit=0.2)
    f.push(np.ones(500, np.float32))
    assert len(f.buf) == 50


def test_fifo_underrun_pads_with_silence():
    f = Fifo(1000, prefill=0.01, limit=1)
    f.push(np.ones(10, np.float32))
    out = f.pull(15)
    assert out[:10].all() and not out[10:].any()


class Capture:
    def __init__(self):
        self.out = []

    def push(self, x):
        self.out.append(x)


def _engine_without_devices():
    e = Engine()
    e._pending = np.zeros(0, np.float32)
    e._dry = np.zeros(MODEL_DELAY, np.float32)
    e._was_on = False
    e._rs_in = None
    e._cable = Capture()
    return e


def test_bypass_is_input_delayed_to_match_model():
    """With removal off, output is the raw mic shifted by the model latency, so toggling doesn't jump."""
    e = _engine_without_devices()
    e.enabled = False
    x = np.random.default_rng(2).normal(0, 0.1, SAMPLE_RATE // 4).astype(np.float32)
    for i in range(0, len(x), 480):  # odd chunk size, like a real 48 kHz device at 10 ms
        e._on_input(x[i:i + 480, None], 0, None, None)
    y = np.concatenate(e._cable.out)
    n = len(y)
    assert n % BLOCK_SHIFT == 0
    np.testing.assert_allclose(y[MODEL_DELAY:n], x[:n - MODEL_DELAY])
