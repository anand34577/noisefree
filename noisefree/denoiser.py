"""Real-time speech denoiser using the DTLN ONNX models (16 kHz, mono).

DTLN: https://github.com/breizhn/DTLN (MIT). Two stacked LSTM models:
model_1 predicts a magnitude mask in the STFT domain, model_2 refines in a
learned time-domain basis. Processes 512-sample windows with a 128-sample hop
(8 ms), so total algorithmic latency is 32 ms.
"""
import os
import urllib.request

import numpy as np
import onnxruntime as ort

from .resources import resource

SAMPLE_RATE = 16000
BLOCK_LEN = 512
BLOCK_SHIFT = 128

MODEL_DIR = resource("models")
MODEL_URL = "https://github.com/breizhn/DTLN/raw/master/pretrained_model/{}.onnx"

# Preference order when "auto" is chosen.
GPU_PROVIDERS = ["CUDAExecutionProvider", "DmlExecutionProvider", "CoreMLExecutionProvider"]

FRIENDLY = {
    "CUDAExecutionProvider": "NVIDIA GPU (CUDA)",
    "DmlExecutionProvider": "GPU (DirectML)",
    "CoreMLExecutionProvider": "Apple GPU / Neural Engine (Core ML)",
    "CPUExecutionProvider": "CPU",
}


def friendly(provider):
    return FRIENDLY.get(provider, provider.replace("ExecutionProvider", ""))


def ensure_models():
    os.makedirs(MODEL_DIR, exist_ok=True)
    paths = []
    for name in ("model_1", "model_2"):
        path = os.path.join(MODEL_DIR, name + ".onnx")
        if not os.path.exists(path):
            print(f"Downloading {name}.onnx ...")
            urllib.request.urlretrieve(MODEL_URL.format(name), path)
        paths.append(path)
    return paths


def available_providers():
    """'auto' plus every useful provider this onnxruntime build supports."""
    return ["auto"] + [p for p in ort.get_available_providers() if p in FRIENDLY]


def _resolve(provider):
    avail = ort.get_available_providers()
    if provider == "auto":
        gpu = [p for p in GPU_PROVIDERS if p in avail]
        return gpu[:1] + ["CPUExecutionProvider"]
    if provider not in avail:
        raise ValueError(f"{provider} not available (have: {avail})")
    return [provider] if provider == "CPUExecutionProvider" else [provider, "CPUExecutionProvider"]


class Denoiser:
    def __init__(self, provider="auto"):
        providers = _resolve(provider)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1  # tiny model: threading only adds latency
        if "DmlExecutionProvider" in providers:
            opts.enable_mem_pattern = False
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        p1, p2 = ensure_models()
        self.s1 = ort.InferenceSession(p1, opts, providers=providers)
        self.s2 = ort.InferenceSession(p2, opts, providers=providers)
        self.provider = self.s1.get_providers()[0]
        self.in1 = [i.name for i in self.s1.get_inputs()]
        self.in2 = [i.name for i in self.s2.get_inputs()]
        self.reset()

    def reset(self):
        self.state1 = np.zeros((1, 2, 128, 2), np.float32)
        self.state2 = np.zeros((1, 2, 128, 2), np.float32)
        self.in_buf = np.zeros(BLOCK_LEN, np.float32)
        self.out_buf = np.zeros(BLOCK_LEN, np.float32)

    def process(self, block):
        """Denoise exactly BLOCK_SHIFT mono float32 samples; returns the same count."""
        self.in_buf[:-BLOCK_SHIFT] = self.in_buf[BLOCK_SHIFT:]
        self.in_buf[-BLOCK_SHIFT:] = block

        spec = np.fft.rfft(self.in_buf)
        mag = np.abs(spec).astype(np.float32).reshape(1, 1, -1)
        mask, self.state1 = self.s1.run(None, {self.in1[0]: mag, self.in1[1]: self.state1})

        est = np.fft.irfft(mag * mask * np.exp(1j * np.angle(spec)))
        est = est.astype(np.float32).reshape(1, 1, -1)
        out, self.state2 = self.s2.run(None, {self.in2[0]: est, self.in2[1]: self.state2})

        self.out_buf[:-BLOCK_SHIFT] = self.out_buf[BLOCK_SHIFT:]
        self.out_buf[-BLOCK_SHIFT:] = 0.0
        self.out_buf += out.reshape(-1)
        return self.out_buf[:BLOCK_SHIFT].copy()
