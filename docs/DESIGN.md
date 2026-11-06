# Flicker Design

## 1. Overview

Flicker is a resource-efficient text-to-image application for Problem Statement P3. A Gradio interface accepts a prompt and generation controls. The adaptive generation layer chooses a model tier, generates candidates, reranks them, optionally post-processes the selected image, and returns images and diagnostic information to the UI.

## 2. Problem and goals

The project targets text-to-image use under mobile-oriented resource constraints. The design seeks to reduce generation latency and memory use while retaining prompt alignment. It also exposes resource and quality information, uses fallback when generation fails from memory or runtime errors, and includes a lightweight classical CV pipeline.

## 3. Requirements traceability

| P3 requirement | Implementation |
|---|---|
| Generate images from user prompts | `generate` in [app.py](../app.py); `generate_with_fallback` in [src/adaptive.py](../src/adaptive.py); `Generator.generate` in [src/generate.py](../src/generate.py) |
| Offer resource-efficient model options | `CONFIGS` and `Generator.load` in [src/generate.py](../src/generate.py); `TIERS` in [src/adaptive.py](../src/adaptive.py) |
| Adapt model tier to current conditions | `profile_resources` and `choose_tier` in [src/adaptive.py](../src/adaptive.py) |
| Recover from generation resource failures | `generate_with_fallback` and `_drop_pipeline` in [src/adaptive.py](../src/adaptive.py) |
| Improve alignment among generated candidates | `pick_best` in [src/rerank.py](../src/rerank.py), called by `generate_with_fallback` |
| Analyze and enrich prompts | `analyze_prompt` in [src/prompt_analyzer.py](../src/prompt_analyzer.py); `enhance_prompt` in [src/prompt_enhancer.py](../src/prompt_enhancer.py) |
| Report image quality and flag artifacts | `quality_report` and `detect_artifacts` in [src/postprocess.py](../src/postprocess.py) |
| Provide optional image enhancement | `run_pipeline` in [src/postprocess.py](../src/postprocess.py), invoked through `_process_image` in [src/adaptive.py](../src/adaptive.py) |
| Evaluate configurations reproducibly | `parse_args`, `load_prompts`, `evaluate_config`, and `append_results` in [src/evaluate.py](../src/evaluate.py) |
| Provide a mobile-friendly interface | `demo` in [app.py](../app.py), themed by `make_theme` and `HERO_HTML` in [src/ui_theme.py](../src/ui_theme.py) |

## 4. System pipeline

The UI validates input and invokes `generate_with_fallback`. Prompt enhancement and analysis feed tier selection. `Generator.generate` creates candidates; `pick_best` scores them with CLIP. The chosen image passes through optional `run_pipeline`, quality reporting, artifact detection, and correction before the UI receives the outputs.

## 5. Components

### `src/__init__.py`

Marks `src` as the project package; it defines no callable API.

### `src/adaptive.py`

`profile_resources` reports available GPU and system-memory information. `choose_tier` selects an automatic tier from resources, prompt complexity, time budget, and recent latency. `generate_with_fallback` handles enhancement, candidate generation, reranking, fallback, post-processing, and result assembly. `_process_image` applies optional post-processing and ensures output sizing. `_correct_artifacts` applies saturation and gamma corrections to flagged images. `_drop_pipeline` frees the loaded pipeline before fallback.

### `src/dataset.py`

`load_coco_pairs` loads COCO captions and images, samples reproducibly from the requested split, and returns image-caption pairs.

### `src/evaluate.py`

`parse_args` reads evaluation options. `load_prompts` loads COCO or complex prompts. `load_clip_model` and `score_images` provide evaluation CLIP scoring. `evaluate_config` generates or reuses images and computes metrics. `load_score_records` and `save_scores` manage cached records. `append_results` writes aggregate rows; `print_table` displays them. `remove_unexpected_images` cleans stale image files from evaluation folders, `mean_std` computes summary statistics, and `main` orchestrates the evaluation.

### `src/generate.py`

`CONFIGS` describes model settings. `Generator.load` loads and configures a Diffusers pipeline. `Generator._truncate_prompt` handles the text encoder token limit. `Generator.generate` validates input, performs inference, and returns the image and generation metrics. `Generator.model_stats` reports parameter and model-size information.

### `src/postprocess.py`

`gray_world_white_balance`, `clahe_luminance`, `bilateral_denoise`, `unsharp_mask`, and `lanczos_resize` implement image operations. `edge_map` produces an edge image. `quality_report` calculates image quality measurements; `detect_artifacts` returns artifact flags and diagnostics. `run_pipeline` conditionally applies the operations and returns the processed image, named intermediates, and before/after reports.

### `src/prompt_analyzer.py`

`analyze_prompt` extracts supported objects, attributes, relationships, counts, lighting, styles, and a complexity score. `_find_terms`, `_find_matches`, and `_find_relationship_phrases` support extraction.

### `src/prompt_enhancer.py`

`enhance_prompt` removes leading instruction phrasing, expands mapped visual concepts, chooses style terms, and returns the enhanced prompt, negative prompt, added terms, concept terms, and subject. `_remove_leading_instructions` and `_find_subject` support this flow. `CONCEPT_MAP` contains the supported concept descriptions.

### `src/rerank.py`

`clip_score` scores one image against a prompt. `pick_best` scores candidates and returns the highest-scoring candidate index with all scores. `_load_model`, `_to_pil_image`, and `_score_images` manage the CLIP model and scoring inputs.

### `src/ui_theme.py`

`mosaic_html` builds an optional image mosaic from `assets/gallery`; `_thumb_data_uri` prepares embedded thumbnails. `HEAD`, `CSS`, and `HERO_HTML` provide the page assets and hero. `make_theme` constructs the Gradio theme.

### `app.py`

`generate` validates UI input, calls `generate_with_fallback`, formats returned metrics, and prepares galleries and reports. `demo` defines the Gradio controls and outputs and launches with the Flicker visual layer.

## 6. Models and optimizations and why

| Config | Role | Optimization |
|---|---|---|
| baseline | Stable Diffusion v1.5 reference | fp32 sampling |
| fp16 | Quality-preserving lower-memory option | Half-precision sampling |
| fast | Low-latency option | LCM-LoRA, 4 steps, guidance 1.0 |
| tiny | Small-model option | BK-SDM-Tiny fp16 with DPM-Solver |

Fast was selected for the High tier because the supplied steps ablation found the best measured CLIP and FID balance at 4 steps. The fp16 tier provides a higher-quality option; tiny supplies the lighter model path.

### LoRA model adaptation

The additional `fp16_lora` config uses the fp16 Stable Diffusion v1.5 model with a rank-8 PEFT LoRA adapter on attention `to_q`, `to_k`, `to_v`, and `to_out.0`. It was trained on 1000 COCO train2017 images for 1000 optimizer steps using batch size 1, gradient accumulation 4, learning rate 1e-4, fp16 mixed precision, and gradient checkpointing. Training took about 25 minutes on the RTX 5060 Laptop 8 GB. Evaluation used the same 300 val2017 captions, preserving the train/validation split.

| Metric | fp16 without LoRA | fp16 with LoRA | Observation |
|---|---:|---:|---|
| CLIP | 33.33 | 33.29 | Near the fp16 result |
| FID | 137.3 | 134.0 | 3.3 better; noisy at 300 images |
| Latency | 2.97 s | 3.10 s | Unfused LoRA; `fuse_lora` would remove this overhead |
| Peak VRAM | 3257 MB | 3261 MB | Similar peak use |
| Parameter increase | — | +1.6M (0.15%) | Small adapter overhead |
| Size increase | — | +3 MB |  |

The FID change is encouraging but not conclusive because FID on 300 images is noisy.

## 7. Adaptive controller

| Tier | Configuration |
|---|---|
| Max | fp16, 512px, 25 steps, guidance 7.5 |
| High | fast, 512px, 4 steps, CLIP best-of-N reranking |
| Medium | fast, 512px, 2 steps |
| Low | tiny, 384px, 15 steps, then Lanczos upscale to 512px |

`choose_tier` combines resource profiling, prompt complexity, time budget, and recent latency. The latency history provides feedback to later choices. `generate_with_fallback` moves to a lower tier when generation raises an OOM or `RuntimeError`; `_drop_pipeline` releases the current model before trying again. For automatic concept-grounding requests, the implementation chooses Max with 3 candidates when VRAM and time permit, otherwise High with 4 candidates. `pick_best` reranks candidate images against the prompt or the subject and expanded concepts.

## 8. Classical CV pipeline

`run_pipeline` measures image properties and conditionally applies gray-world white balance, CLAHE on luminance, bilateral denoising, unsharp masking, Lanczos resizing, and edge extraction. It returns named intermediate images and before/after `quality_report` results. `detect_artifacts` flags blank/black, over/underexposed, oversaturated, and checkerboard-like output. `_correct_artifacts` in `src/adaptive.py` adjusts saturation or gamma for the applicable flags.

## 9. Evaluation methodology

`src/evaluate.py` samples 300 COCO 2017 val captions reproducibly with seed 42. Each config receives a warm-up generation that is excluded. Images are 512×512. CLIP is open_clip ViT-B-32 laion2b and is reported as 100 times cosine similarity. Latency is denoising-only; peak VRAM is collected during generation. clean-fid is computed on the 300 generated images and corresponding real images. The complex-prompt comparison uses 25 multi-object prompts. The evaluator stores per-image scores and appends aggregate rows to `outputs/results.csv`.

## 10. Results and ablations

| Config | COCO CLIP | Complex CLIP | FID | Latency | Peak VRAM | Parameters | Model size |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 33.31 | 35.20 | 138.0 | 6.97 s | 6226 MB | 1.066B | 4067 MB |
| fp16 | 33.33 | 35.28 | 137.3 | 2.97 s | 3257 MB | 1.066B | 2034 MB |
| fast | 31.56 | 33.71 | 141.9 | 0.52 s | 3398 MB | 1.133B, including unfused LoRA | 2162 MB |
| tiny | 31.16 | 33.46 | 142.4 | 1.37 s | 2231 MB | 0.530B | 1011 MB |

The `fp16_lora` adaptation measured CLIP 33.29 and FID 134.0 versus CLIP 33.33 and FID 137.3 for fp16 without LoRA. It took 3.10 s versus 2.97 s with the adapter unfused, used 3261 MB versus 3257 MB peak VRAM, and added 1.6M parameters (0.15%) and 3 MB. `fuse_lora` would remove the latency overhead. The FID improvement is encouraging but inconclusive on a 300-image sample.

| Ablation | Result |
|---|---|
| Fast steps | 2 steps: CLIP 30.83, FID 150.3, 0.36 s; 4 steps: CLIP 31.56, FID 141.9, 0.52 s; 8 steps: CLIP 30.65, FID 144.9, 0.83 s |
| Guidance | 1.0: CLIP 31.56, FID 141.9, 0.53 s; 1.8: CLIP 31.42, FID 149.8, 0.71 s |
| Post-processing | Off: CLIP 31.56, FID 141.93, 0.52 s; on: CLIP 31.52, FID 141.84, 0.53 s |
| Reproducibility | Repeated fast-4 runs returned identical CLIP and FID |

Speedups against baseline were 2.3× for fp16, 13.4× for fast, and 5.1× for tiny. COCO CLIP retained was 100%, 94.7%, and 93.5%, respectively. Complex-prompt CLIP retained by fast and tiny was 95.8% and 95.1%. FID absolute values are high at this sample size; comparisons are relative.

## 11. Design decisions and trade-offs

- Keep a full precision reference alongside faster and smaller options.
- Use 4-step LCM for High based on the measured ablation instead of assuming more steps improve quality.
- Keep guidance at 1.0 for fast; the higher tested setting reduced measured CLIP, worsened FID, and increased latency.
- Use best-of-N CLIP reranking to improve candidate selection without changing the generation model.
- Keep classical post-processing optional because its measured effect on CLIP and FID was neutral.
- Return quality, artifact, resource, and candidate details to make generation outcomes inspectable.

## 12. Deployment

The application runs on the team laptop GPU and is exposed publicly through Cloudflare Tunnel. A Dockerfile is provided for container deployment. Hugging Face Docker/Gradio Spaces require a paid plan for the deployment approach described by the team.

## 13. Limitations

The generator can miscount objects and bind colors to the wrong objects. It does not reliably render text and can imitate trademarked or copyrighted characters. Small faces can be distorted at 512×512. The 25-prompt complex set and 300-image FID sample are limited; the absolute FID values should be interpreted relatively.

## 14. Ethics

The safety checker is NSFW-only and does not prevent imitation of copyrighted characters or brands. COCO/LAION biases may be reflected in generations. Model use is subject to the CreativeML OpenRAIL-M licence. Flicker does not store user data.

## 15. Future work

- Evaluate int8 inference.
- Explore on-device export.
- Evaluate a better base model under the same resource constraints.
- Add face restoration for small or distorted faces.

## 16. Team contributions

Team: Team Chaos Theory. Individual member names and contribution assignments were not supplied in the project facts; replace `<MEMBERS>` with the team's roster and contribution details.
