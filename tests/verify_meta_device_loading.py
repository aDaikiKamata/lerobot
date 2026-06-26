"""Verify that meta-device from_pretrained produces identical weights to original init.

Usage:
    python tests/verify_meta_device_loading.py <model_dir>

where <model_dir> contains config.json and model.safetensors.
"""

import json
import sys
from pathlib import Path

import torch
from safetensors.torch import load_file

from lerobot.policies.pi05.modeling_pi05 import PI05Config, PI05Policy

# Suppress verbose prints from from_pretrained
import builtins

_print = builtins.print
_noop = lambda *a, **k: None


def make_config(model_dir: str) -> PI05Config:
    d = json.loads(Path(f"{model_dir}/config.json").read_text())
    d.pop("type", None)
    return PI05Config(**d)


def load_original(model_dir: str) -> PI05Policy:
    """Original code path: cls(config) on CPU, then load_state_dict(strict=True)."""
    cfg = make_config(model_dir)
    cfg.device = "cpu"
    model = PI05Policy(cfg)
    sd = load_file(f"{model_dir}/model.safetensors")
    fixed = model._fix_pytorch_state_dict_keys(sd, model.config)
    remapped = {
        (f"model.{k}" if not k.startswith("model.") else k): v
        for k, v in fixed.items()
    }
    model.load_state_dict(remapped, strict=True)
    return model


def load_meta(model_dir: str) -> PI05Policy:
    """New code path: meta-device init via from_pretrained."""
    builtins.print = _noop
    try:
        cfg = make_config(model_dir)
        cfg.device = "cpu"
        return PI05Policy.from_pretrained(model_dir, config=cfg)
    finally:
        builtins.print = _print


def main() -> None:
    if len(sys.argv) < 2:
        _print(f"Usage: {sys.argv[0]} <model_dir>")
        sys.exit(1)

    model_dir = sys.argv[1]
    _print(f"Model dir: {model_dir}")

    _print("Building original model (takes ~100s)...")
    model_orig = load_original(model_dir)
    _print("Building meta model...")
    model_meta = load_meta(model_dir)

    # Compare parameters
    orig_params = dict(sorted(model_orig.named_parameters()))
    meta_params = dict(sorted(model_meta.named_parameters()))
    assert set(orig_params.keys()) == set(meta_params.keys()), (
        f"Parameter name sets differ: "
        f"only_orig={set(orig_params) - set(meta_params)}, "
        f"only_meta={set(meta_params) - set(orig_params)}"
    )

    param_mismatches = []
    for name in orig_params:
        if not torch.equal(orig_params[name], meta_params[name]):
            param_mismatches.append(name)

    # Compare buffers
    orig_bufs = dict(sorted(model_orig.named_buffers()))
    meta_bufs = dict(sorted(model_meta.named_buffers()))
    assert set(orig_bufs.keys()) == set(meta_bufs.keys()), (
        f"Buffer name sets differ: "
        f"only_orig={set(orig_bufs) - set(meta_bufs)}, "
        f"only_meta={set(meta_bufs) - set(orig_bufs)}"
    )

    buf_mismatches = []
    for name in orig_bufs:
        if not torch.equal(orig_bufs[name], meta_bufs[name]):
            buf_mismatches.append(name)

    # Report
    total_params = len(orig_params)
    total_bufs = len(orig_bufs)

    if param_mismatches:
        _print(f"PARAM MISMATCH ({len(param_mismatches)}/{total_params}):")
        for n in param_mismatches[:10]:
            _print(f"  {n}")

    if buf_mismatches:
        _print(f"BUFFER MISMATCH ({len(buf_mismatches)}/{total_bufs}):")
        for n in buf_mismatches[:10]:
            _print(f"  {n}")

    if param_mismatches or buf_mismatches:
        _print("FAILED")
        sys.exit(1)

    _print(f"ALL MATCH: {total_params} params, {total_bufs} buffers")


if __name__ == "__main__":
    main()
