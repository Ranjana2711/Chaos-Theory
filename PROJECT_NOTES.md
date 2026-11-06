# Flicker (Team Chaos Theory) - P3 Resource-Efficient Text-to-Image
OS: Windows, GPU: RTX 5060 Laptop 8GB, torch 2.11 cu128, diffusers 0.42, transformers 5, gradio 6, pandas<3, scipy<1.16
Run scripts as modules from project root: python -m src.<name>. Imports use "from src.x import y".
Data: data/annotations/captions_val2017.json, data/val2017/

Configs (src/generate.py):
- baseline: stable-diffusion-v1-5/stable-diffusion-v1-5, fp32, 25 steps, guidance 7.5
- fp16: same model, fp16, 25 steps
- fast: same model, fp16 + LCM-LoRA latent-consistency/lcm-lora-sdv1-5, LCMScheduler, 4 steps, guidance 1.0
- tiny: nota-ai/bk-sdm-tiny, fp16, DPMSolverMultistepScheduler, 20 steps (no LCM)
On CPU always use float32. generate() returns image, latency_s (denoising only), load_time_s, peak_mem_mb.

Tiers (src/adaptive.py): Max = fp16 512px 25 steps guidance 7.5; High = fast 512px 4 steps + best-of-N CLIP rerank; Medium = fast 512px 2 steps; Low = tiny 384px 15 steps + upscale to 512 (LCM best at 4 steps per ablation)
Only one pipeline in GPU memory at a time. Windows-safe: no multiprocessing, num_workers=0.

Done: dataset.py, generate.py, postprocess.py, adaptive.py, evaluate.py, app.py
- fp16_lora: fp16 config + our LoRA (rank 8) trained on 1000 COCO train2017 images, weights in outputs/lora_coco. Train/val split: LoRA trained on train2017, evaluated on val2017.
