import numpy as np
import pytest
import soundfile as sf

from noisefree.filedenoise import Cancelled, clean_file, default_output

CPU = "CPUExecutionProvider"


def noisy_file(path, rate=44100, seconds=2, channels=2):
    rng = np.random.default_rng(2)
    x = rng.normal(0, 0.05, (rate * seconds, channels)).astype(np.float32)
    sf.write(path, x, rate, subtype="PCM_16")
    return x


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def test_keeps_rate_length_and_channels_and_removes_noise(tmp_path):
    src, dst = str(tmp_path / "in.wav"), str(tmp_path / "out.wav")
    x = noisy_file(src)
    clean_file(src, dst, CPU)
    y, rate = sf.read(dst, dtype="float32", always_2d=True)
    info = sf.info(dst)
    assert rate == 44100 and y.shape == x.shape and info.subtype == "PCM_16"
    settled = slice(rate // 2, None)  # the LSTM state settles in the first half second
    assert rms_db(x[settled]) - rms_db(y[settled]) > 15


def test_zero_strength_returns_the_original(tmp_path):
    src, dst = str(tmp_path / "in.wav"), str(tmp_path / "out.flac")
    x = noisy_file(src, rate=16000, channels=1)
    clean_file(src, dst, CPU, strength=0.0)
    y, _ = sf.read(dst, dtype="float32", always_2d=True)
    assert np.max(np.abs(y - x)) < 1e-3  # 16-bit rounding only, no delay


def test_cancel_writes_nothing(tmp_path):
    src, dst = str(tmp_path / "in.wav"), str(tmp_path / "out.wav")
    noisy_file(src, seconds=3)
    with pytest.raises(Cancelled):
        clean_file(src, dst, CPU, cancelled=lambda: True)
    assert not (tmp_path / "out.wav").exists()


def test_unsupported_file_explains_itself(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("not audio")
    with pytest.raises(ValueError, match="isn't supported"):
        clean_file(str(src), str(tmp_path / "out.wav"), CPU)


def test_default_output_name():
    assert default_output("/a/talk.mp3") == "/a/talk (clean).mp3"
    assert default_output("/a/talk.m4a") == "/a/talk (clean).wav"
