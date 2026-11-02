import numpy as np

from noisefree.denoiser import BLOCK_SHIFT, SAMPLE_RATE, Denoiser, _resolve, available_providers


def run(d, x):
    return np.concatenate([d.process(x[i:i + BLOCK_SHIFT]) for i in range(0, len(x) - BLOCK_SHIFT + 1, BLOCK_SHIFT)])


def test_removes_steady_noise():
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 0.05, SAMPLE_RATE * 2).astype(np.float32)
    out = run(Denoiser("CPUExecutionProvider"), noise)
    # skip the first half second while the LSTM state settles
    before = np.sqrt(np.mean(noise[SAMPLE_RATE // 2:] ** 2))
    after = np.sqrt(np.mean(out[SAMPLE_RATE // 2:] ** 2))
    assert 20 * np.log10(before / after) > 15


def test_block_in_block_out():
    d = Denoiser("CPUExecutionProvider")
    y = d.process(np.zeros(BLOCK_SHIFT, np.float32))
    assert y.shape == (BLOCK_SHIFT,) and y.dtype == np.float32


def test_auto_always_keeps_cpu_fallback():
    assert _resolve("auto")[-1] == "CPUExecutionProvider"
    assert available_providers()[0] == "auto"
