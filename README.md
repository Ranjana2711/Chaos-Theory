# Flicker

## 🔗 Live Demo

**Live app:** - https://locks-charts-distinguished-luxury.trycloudflare.com

> ⚠️ **Note:** The app runs on our own GPU laptop (NVIDIA, CUDA) and is shared publicly through a Cloudflare Tunnel.
> The link works only while that laptop is switched on and the app is running. It will be kept on during the evaluation window.
> If the link is down, please follow the **Run locally** steps below.

**Repository:** https://github.com/Ranjana2711/Chaos-Theory

## 👥 Team Chaos Theory (T18)

| Name | USN |
|---|---|
| R Akshayaa Sree | 1RUA24CSE0343 |
| Rachana H | 1RUA24CSE0349 |
| Ranjana Prashanth | 1RUA24CSE0359 |

## Summary

Flicker is Team Chaos Theory's P3 solution: resource-efficient text-to-image generation intended for mobile-device constraints. It combines Stable Diffusion configurations, adaptive compute tiers, candidate reranking, and optional classical image post-processing.

## Features

- Five generation configs: baseline, fp16, DreamShaper (`dream`), fast, and tiny.
- Adaptive Max, High, Medium, and Low tiers.
- DreamShaper powers the Max tier for improved prompt adherence at the same measured latency as fp16 SD v1.5.
- Automatic fallback to a lower tier after an OOM or `RuntimeError`.
- Feedback controller informed by available resources, prompt complexity, time budget, and recent latency.
- Prompt analyzer and enhancer, including visual expansion for selected concepts.
- CLIP candidate reranking.
- Classical CV post-processing with a quality report and artifact detection/correction.
- Butterfly-themed Flicker UI with an optional gallery mosaic.

## Tech stack

| Area | Technology |
|---|---|
| UI | Gradio |
| Generation | PyTorch, Diffusers, Stable Diffusion v1.5, BK-SDM-Tiny, LCM-LoRA |
| Candidate ranking and evaluation | open_clip ViT-B-32 |
| Image processing | OpenCV, NumPy, Pillow |
| Evaluation | clean-fid |
| Deployment | Docker, Cloudflare Tunnel |

## Windows setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the CUDA-enabled PyTorch build and project dependencies:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

The dependency set requires `pandas<3` and `scipy<1.16`.

## Dataset

Download and extract the COCO annotations archive and validation images into `data/`, preserving the expected `data/annotations/` and `data/val2017/` structure:

- [COCO annotations](http://images.cocodataset.org/annotations/annotations_trainval2017.zip)
- [COCO val2017 images](http://images.cocodataset.org/zips/val2017.zip)

The runtime evaluator loads captions and image pairs through `load_coco_pairs` in [src/dataset.py](src/dataset.py). The COCO archives are not included in this repository.

## Run

Start the Gradio app:

```powershell
python app.py
```

Expose the local app through Cloudflare Tunnel:

```powershell
cloudflared tunnel --url http://localhost:7860
```

Build and run the Docker image:

```powershell
docker build -t flicker .
docker run -p 7860:7860 flicker
```

## Reproduce results

Run the main COCO evaluation:

```powershell
python -m src.evaluate --n 300 --configs baseline,fp16,fast,tiny
```

Run the fast steps ablation:

```powershell
python -m src.evaluate --n 300 --configs fast --steps 2
python -m src.evaluate --n 300 --configs fast --steps 4
python -m src.evaluate --n 300 --configs fast --steps 8
```

Compare post-processing and complex prompts:

```powershell
python -m src.evaluate --n 300 --configs fast --postprocess
python -m src.evaluate --n 25 --configs baseline,fp16,fast,tiny --prompts complex
```

Download the training subset, fine-tune LoRA, and evaluate it:

```powershell
python -m src.download_train
python -m src.train_lora
python -m src.evaluate --n 300 --configs fp16_lora
```

Evaluation runs use seed 42. A warm-up generation is excluded from reported latency; latency measures denoising only. The evaluator writes per-run scores and aggregates to `outputs/`.

## Results headline

On COCO val, DreamShaper reached 34.15 CLIP versus 33.33 for fp16 SD v1.5 (+0.82), the best score of all configs, with 135.4 FID and the same 2.97 s latency, 3258 MB peak VRAM, and 2034 MB model size. This gives better prompt adherence at no extra measured compute, so DreamShaper is used for Max. The full results and ablations are in the [P3 evaluation report](eval_P3_T18.md).

Across 35 Auto-tier app requests with a 10 s budget and the two most-used pipelines kept loaded, mean total was 4.69 s, max 7.96 s, and all finished under 10 s; per-image denoising was 0.49–0.59 s on High and 2.8–3.3 s on Max.

The rank-8 COCO LoRA adaptation scored 33.29 CLIP and 134.0 FID versus 33.33 and 137.3 for fp16 without LoRA; the FID improvement is encouraging but inconclusive on a 300-image sample.

## Repo structure

| Path | Purpose |
|---|---|
| [app.py](app.py) | Gradio app and UI-to-generation integration |
| [src/adaptive.py](src/adaptive.py) | Tier selection, fallback, candidate generation, and post-processing orchestration |
| [src/generate.py](src/generate.py) | Diffusers model loading and image generation |
| [src/prompt_analyzer.py](src/prompt_analyzer.py) | Prompt concept and complexity analysis |
| [src/prompt_enhancer.py](src/prompt_enhancer.py) | Prompt cleanup, concept expansion, and style terms |
| [src/rerank.py](src/rerank.py) | CLIP candidate scoring |
| [src/postprocess.py](src/postprocess.py) | Classical CV pipeline, quality reporting, and artifact detection |
| [src/dataset.py](src/dataset.py) | COCO image-caption sampling |
| [src/evaluate.py](src/evaluate.py) | Offline generation and evaluation |
| [src/ui_theme.py](src/ui_theme.py) | Flicker theme, hero, animation, and optional mosaic |
| [docs/DESIGN.md](docs/DESIGN.md) | Design and implementation notes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Runtime and evaluation flow diagrams |
| [docs/FAILURES.md](docs/FAILURES.md) | Documented failure cases |

## Limitations

- Text-to-image models can miss object counts, attributes, and their bindings.
- Text rendered in images is unreliable.
- Small faces can be distorted at the evaluated image size.
- CLIP and FID are proxies and do not establish correctness or safety.
- The complex-prompt evaluation covers a small set of multi-object prompts.
- The reported FID values are based on a small sample and should be compared relatively.
- Model downloads and GPU memory availability affect startup and generation.

## Ethics

The safety checker handles NSFW content only. The system can imitate copyrighted characters and brands. COCO and LAION-derived model data contain biases that can affect outputs. Stable Diffusion v1.5 and related model components are distributed under the CreativeML OpenRAIL-M licence; users must follow the applicable model terms. Flicker does not store user data.

## Links

- [Design](docs/DESIGN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Failure cases](docs/FAILURES.md)
- [Evaluation report](eval_P3_T18.md)
