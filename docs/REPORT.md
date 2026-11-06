# Hackathon Technical Solution Report

| Field | Details |
| :--- | :--- |
| **Problem ID** | P3 |
| **Problem Title** | Resource-Efficient Text-to-Image Generation for Mobile Devices |
| **Team Name** | Chaos Theory (Team ID: T18) |
| **Team Members** | `[Full name – USN]`, `[Full name – USN]`, `[Full name – USN]`, `[Full name – USN]` |
| **GitHub Repository** | https://github.com/Ranjana2711/Chaos-Theory (evaluated commit: `[paste output of git rev-parse --short HEAD]`) |
| **Live Demo / Deployment** | `[trycloudflare.com link]` (Gradio app served from our RTX 5060 laptop through a Cloudflare Tunnel) |

Project name: **Flicker**.

---

## 1. Problem Understanding & Solution Strategy

* **Core Technical Challenge:** Diffusion text-to-image models are too slow and memory-hungry for phones. Our unoptimized reference, Stable Diffusion v1.5 in fp32 with 25 steps, takes 6.97 s per image and 6.2 GB of VRAM on an 8 GB laptop GPU, with a 4 GB model. The target was a response within about 10 s on modest hardware, low peak memory, and a small model, while keeping prompt alignment and image quality. Failure modes we targeted: quality loss from compression and fewer sampling steps, concept neglect on unusual prompts (missing objects, wrong counts and colours), visual artifacts (blank, over-saturated or badly exposed images) and running out of memory on constrained devices.

* **Proposed Methodology:** We combine three model optimizations (fp16 inference, LCM-LoRA step distillation from 25 to 4 steps, and the BK-SDM-Tiny compressed UNet) with an adaptive controller. For each request the controller analyses the prompt, profiles the device and recent latencies, then picks one of four tiers. It can fall back to a lighter tier on failure, enhance the prompt, generate several candidates and rerank them with CLIP, and finish with classical CV quality checks and corrections. A single fixed configuration is either fast but weak on hard prompts, or good but too slow; adapting per request gets both speed on easy prompts and quality on hard ones within one time budget.

---

## 2. Technical Architecture & Implementation

> Architecture diagram: `docs/ARCHITECTURE.md`. Full design: `docs/DESIGN.md`.

### 2.1 Classical Algorithmic Baseline

* **Algorithms Utilized** (`src/postprocess.py`, OpenCV and NumPy only):
  * Gray-world white balance for colour casts.
  * CLAHE on the L channel of LAB for local contrast.
  * Bilateral filtering for edge-preserving denoising.
  * Unsharp masking for controlled sharpening.
  * Lanczos resizing for resolution optimization (the Low tier upscales 384 → 512).
  * Canny edge maps for visualizing structure.
  * A no-reference quality report: sharpness (Laplacian variance), contrast (L standard deviation), Hasler–Süsstrunk colourfulness, clipped-pixel ratio, channel imbalance, noise estimate and mean luminance.
  * Artifact detection: blank or black frames, over-saturation, over- and under-exposure, and checkerboard patterns via an FFT high-frequency ratio.

* **Adaptive Selection Logic:** No step runs blindly. The quality report is computed first, and each correction runs only when its statistic crosses a threshold. For example, white balance applies only when channel imbalance exceeds 40, and is blended at 30% strength so intentionally colourful scenes (a red apple) are not washed out. CLAHE applies only to low-contrast images. In `src/adaptive.py`, flagged artifacts trigger targeted fixes: HSV saturation reduction for over-saturation, gamma correction for exposure problems, and one regeneration with a new seed for blank frames. When nothing is flagged the image passes through unchanged, and the before and after reports are identical.

### 2.2 Deep Learning Pipeline

* **Model Architecture** (`src/generate.py`): latent diffusion with a CLIP text encoder, UNet denoiser and VAE decoder. Configurations:

| Config | Model | Precision | Steps | Role |
|---|---|---|---|---|
| baseline | Stable Diffusion v1.5 | fp32 | 25 | Unoptimized reference |
| fp16 | Stable Diffusion v1.5 | fp16 | 25 | Reduced-precision optimization |
| fast | SD v1.5 + LCM-LoRA | fp16 | 4 | Step distillation; High and Medium tiers |
| tiny | BK-SDM-Tiny (pruned and distilled UNet) | fp16 | 20 | Lightweight architecture; Low tier |
| dream | DreamShaper 8 (SD v1.5 fine-tune) | fp16 | 25 | Better prompt adherence; Max tier |
| fp16_lora | SD v1.5 + our COCO LoRA | fp16 | 25 | Our own model adaptation |

  Rationale: SD v1.5 has mature lightweight variants (LCM-LoRA, BK-SDM) and fits mobile-class memory, whereas SDXL-class models exceed it. The SD v1.5 safety checker stays enabled on every config, attached explicitly for DreamShaper.

* **Loss Functions & Training** (`src/download_train.py`, `src/train_lora.py`): we fine-tuned a rank-8 LoRA on the UNet attention projections (to_q, to_k, to_v, to_out.0) using **1,000 COCO train2017** image–caption pairs, with the standard epsilon-prediction MSE diffusion loss. Settings: AdamW at lr 1e-4, batch 1 with gradient accumulation 4, 1,000 optimizer steps, fp16 mixed precision and gradient checkpointing. Latents and text embeddings were cached first so training fit in 8 GB; it took about 25 minutes. Evaluation uses the held-out **val2017** split. The adapter adds 1.6 M parameters (0.15%) and about 3 MB.

### 2.3 Hybrid Integration & Adaptive Mechanism

* **Fusion Strategy:** classical analysis guides the neural generator before and after generation.
  * **Before:** a rule-based prompt analyzer (`src/prompt_analyzer.py`) extracts objects, attributes, spatial relations, counts, lighting and style, and computes a complexity score. The enhancer (`src/prompt_enhancer.py`) then:
    * removes instruction words ("create", "draw")
    * expands hard concepts into visual descriptions (ghost → "translucent glowing white ghostly figure")
    * adds each object's defining feature (apple tree → "with ripe red apples")
    * protects animal subjects with negative prompts against human substitution
    * adds mood-appropriate style terms
    * applies **token emphasis** (×1.3–1.4 on key nouns in the text embeddings)
  * **After:** CLIP reranking (`src/rerank.py`) scores each candidate against the subject and concept terms. The classical quality report and artifact detector then decide which corrections to apply.

* **Decision Logic** (`src/adaptive.py`):
  * Resource profiling measures free VRAM (counting memory held by our own pipeline as available), system RAM, device type and GPU utilization.
  * Tier selection:
    * **Max** (DreamShaper, 25 steps): for complex or hard-concept prompts when VRAM is at least 4 GB and the budget allows.
    * **High** (LCM, 4 steps, with candidates): for normal prompts with enough VRAM.
    * **Medium** (LCM, 2 steps).
    * **Low** (BK-SDM-Tiny at 384 px with Lanczos upscaling): for low memory or CPU.
  * The number of candidates is budget-aware: n = max(1, min(4, ⌊0.8 × budget / per-image latency estimate⌋)), so Max gets 2 candidates within the default 10 s budget.
  * A feedback controller keeps the last 5 latencies. It reduces candidates, then drops a tier, after a generation exceeds the budget, and may step up after three fast generations.
  * Fallback: on CUDA out-of-memory or a runtime error, the request drops one tier.
  * A franchise-name filter refuses prompts that name copyrighted characters.

---

## 3. Experimental Benchmarks & Evaluation

**Setup:**
* 300 COCO 2017 validation captions, seed 42, 512×512, on an RTX 5060 Laptop GPU (8 GB) with PyTorch 2.11 (CUDA 12.8).
* CLIP score uses OpenCLIP ViT-B/32 (LAION-2B), reported as 100 × cosine similarity.
* FID uses clean-fid against the matching real images.
* Latency covers denoising only, after a warm-up run.

PSNR, SSIM and LPIPS from the template need a ground-truth image for each output. Text-to-image generation has no single correct image, so we use the P3 metrics instead: CLIP for text–image alignment and FID for distribution-level realism, plus latency, memory and size. FID on 300 images is noisy in absolute terms, so the comparison between configs is what matters.

### 3.1 Quantitative Benchmarks

| Approach / Model Variant | CLIP ↑ | FID ↓ | Latency (s / image) | Peak VRAM (MB) | Model size (MB) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline: SD v1.5 fp32, 25 steps | 33.31 | 138.0 | 6.97 | 6,226 | 4,067 |
| fp16, 25 steps | 33.33 | 137.3 | 2.97 | 3,257 | 2,034 |
| fast: fp16 + LCM-LoRA, 4 steps | 31.56 | 141.9 | **0.52** | 3,398 | 2,162 |
| tiny: BK-SDM-Tiny fp16, 20 steps | 31.16 | 142.4 | 1.37 | **2,231** | **1,011** |
| fp16 + our COCO LoRA | 33.29 | **134.0** | 3.10 | 3,261 | 2,037 |
| dream: DreamShaper 8 fp16, 25 steps | **34.15** | 135.4 | 2.97 | 3,258 | 2,034 |
| fast + adaptive classical post-processing | 31.52 | 141.8 | 0.53 | 3,398 | 2,162 |

**Complex prompts** (25 prompts with multiple objects, colours, counts and spatial relations; CLIP ↑):

| baseline | fp16 | fast | tiny | dream |
|:---:|:---:|:---:|:---:|:---:|
| 35.20 | 35.28 | 33.71 | 33.46 | **37.26** |

* **Analysis:**
  * fp16 halves memory and is 2.3× faster with no measurable quality loss.
  * LCM step distillation gives the largest gain: 13.4× faster than the baseline while keeping 94.7% of its CLIP score (95.8% on complex prompts), at the cost of about 4 FID points.
  * BK-SDM-Tiny is the right choice for constrained devices: 4× smaller and 64% less peak VRAM, keeping 93.5% of CLIP.
  * DreamShaper 8 has the best prompt adherence at no extra compute (+0.82 CLIP on COCO, +1.98 on complex prompts), which is why the Max tier uses it.
  * The adaptive system serves fast configurations for ordinary prompts and spends extra compute only where the prompt needs it.

### 3.2 Visual Outputs & Intermediate Representations

The application and repository show:
1. **Raw versus final image**, side by side for every generation, with the classical post-processing **intermediates gallery** (white balance, CLAHE, denoise, sharpen, Canny edge map) and the before/after quality report.
2. **Candidate gallery** with each candidate's CLIP score and the chosen image marked.
3. **Controller decisions panel:** the prompt analysis (objects, relations, complexity) and resource profile behind each tier choice.
4. **Failure and fixed examples** in `docs/failures/`: concept neglect on High versus a fixed result on Max for the ghost and headphones prompts.

### 3.3 Ablation Study

| Ablation (fast config unless noted) | Variant | CLIP | FID | Latency | Finding |
|---|---|:---:|:---:|:---:|---|
| Sampling steps | 2 / **4** / 8 | 30.83 / **31.56** / 30.65 | 150.3 / **141.9** / 144.9 | 0.36 / 0.52 / 0.83 s | LCM peaks at 4 steps; 8 is slower *and* worse, so High uses 4 |
| Guidance scale | **1.0** / 1.8 | **31.56** / 31.42 | **141.9** / 149.8 | 0.53 / 0.71 s | Above 1.0 needs a second UNet pass: 35% slower and worse, so we kept 1.0 |
| Classical post-processing | off / on | 31.56 / 31.52 | 141.93 / 141.84 | 0.52 / 0.53 s | Neutral on CLIP and FID (+15 ms); it acts on no-reference quality and artifacts |
| Precision (SD v1.5, 25 steps) | fp32 / fp16 | 33.31 / 33.33 | 138.0 / 137.3 | 6.97 / 2.97 s | fp16 has no quality cost |
| Architecture | full UNet / BK-SDM-Tiny | 33.33 / 31.16 | 137.3 / 142.4 | 2.97 / 1.37 s | 4× smaller, −2.2 CLIP |
| Model adaptation (fp16) | none / COCO LoRA | 33.33 / 33.29 | 137.3 / 134.0 | 2.97 / 3.10 s | FID 3.3 better at equal CLIP; encouraging but noisy at 300 images |
| Base checkpoint (fp16) | SD v1.5 / DreamShaper 8 | 33.33 / 34.15 | 137.3 / 135.4 | 2.97 / 2.97 s | Best prompt adherence at the same cost |

Repeated runs of the fast configuration produced identical CLIP and FID values, which confirms the evaluation is reproducible with fixed seeds.

---

## 4. Failure Modes & Limitations

Full analysis with images: `docs/FAILURES.md`.

* **Observed Failure Cases:**
  1. **Counting and colour binding:** "three blue cups to the left of two yellow bananas" produced about 10 bananas and no blue cups.
  2. **Text rendering:** a franchise-name prompt produced garbled lettering and imitated trademarked characters.
  3. **Concept neglect:** "a cat wearing headphones" lost the headphones on High and even on Max with SD v1.5, and the colour "red" moved onto the sofa (attribute leakage).
  4. **Subject substitution:** after switching Max to DreamShaper, the same prompt produced a girl with cat ears.
  5. **Small-face distortion** at 512 px.
  6. **Abstract subjects omitted:** a ghost prompt produced only the scene.
  7. **Prompt ambiguity:** "an apple tree" gave a blossoming tree with no fruit.

* **Root Cause & Mitigation:**
  * Most failures come from SD v1.5's CLIP text encoder. It binds counts and attributes to objects weakly, sees text as word tokens rather than letters, and resolves each noun toward its most frequent training appearance. Subject substitution reflects DreamShaper's training bias toward people. Small faces simply get too few pixels at 512×512.
  * Mitigations implemented and measured:
    * a stronger checkpoint for the Max tier (complex-prompt CLIP 35.28 → 37.26)
    * concept expansion and defining-feature terms
    * token emphasis
    * animal-subject protection through negative prompts
    * concept-grounded, budget-aware CLIP reranking
    * a mood-aware enhancer that drops photo terms for fantasy prompts
  * With these, the ghost and headphones prompts now succeed. Counting, text rendering and small faces remain limitations.
  * Suggested fixes: an attention-guided method such as Attend-and-Excite for object neglect, a face-restoration stage, and a larger text encoder (an SDXL or SD3-class model) where memory allows. That last option conflicts with the mobile budget this project targets.

* **Other limitations:**
  * FID on 300 images is only indicative.
  * The safety checker blacked out 4 of 300 COCO captions in one run (1.3%), mostly false positives.
  * The live demo depends on our laptop staying online. Hugging Face Docker and Gradio Spaces now need a paid plan.
  * Ethics: models trained on COCO and LAION carry their biases, and the base models are licensed under CreativeML OpenRAIL-M. We store no user data.

---

## 5. Deployment & Quickstart Guide

### Quickstart Commands

```bash
# 1. Clone the repository and install dependencies (Python 3.12, NVIDIA GPU recommended)
git clone https://github.com/Ranjana2711/Chaos-Theory.git
cd Chaos-Theory
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu128

# 2. Download COCO 2017 into data/ (captions + val images)
#    http://images.cocodataset.org/annotations/annotations_trainval2017.zip
#    http://images.cocodataset.org/zips/val2017.zip

# 3. Run the app (http://localhost:7860), or app + public tunnel on Windows
python app.py
.\start.ps1

# 4. Reproduce the benchmarks
python -m src.evaluate --n 300 --configs baseline,fp16,fast,tiny,dream
python -m src.evaluate --n 300 --configs fast --steps 2
python -m src.evaluate --n 300 --configs fast --steps 8
python -m src.evaluate --n 300 --configs fast --steps 4 --postprocess
python -m src.evaluate --configs baseline,fp16,fast,tiny,dream --prompts complex

# 5. Reproduce the LoRA adaptation
python -m src.download_train
python -m src.train_lora
python -m src.evaluate --n 300 --configs fp16_lora
```

### Deployment Format

* A **Gradio 6** web app (`app.py`) with a custom theme (`src/ui_theme.py`): an animated butterfly-and-firefly canvas background, loading and error states, and a phone-friendly layout.
* It runs on a local NVIDIA GPU and is exposed publicly through a **Cloudflare Tunnel**. `start.ps1` starts both with one command.
* A **Dockerfile** (`python:3.12-slim`, non-root user) is included: `docker build -t flicker .` then `docker run --gpus all -p 7860:7860 flicker`. Without a GPU it runs on CPU in the Low tier. Models download on first use; the trained LoRA weights are not baked into the image.

---

### Student Submission Checklist
- [x] Working GitHub repository link included with an updated `README.md`.
- [x] No raw code pasted into this report.
- [x] All table metrics match test runs reproducible via the repository (`outputs/results.csv`, copied to `assets/results.csv`).
- [ ] All team member details accurately recorded. *(fill in names and USNs above)*
