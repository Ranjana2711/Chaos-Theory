1RUA24CSE0343,1RUA24CSE0349,1RUA24CSE0359

# Flicker — Problem Statement P3 Evaluation

## Setup

| Item | Configuration |
|---|---|
| Project | Flicker by Team Chaos Theory |
| Problem statement | P3: resource-efficient text-to-image for mobile |
| Team | Team Chaos Theory (<MEMBERS>) |
| Hardware | RTX 5060 Laptop, 8 GB VRAM |
| Operating system | Windows |
| Runtime | torch 2.11 cu128 |
| Evaluation data | COCO 2017 val, 300 captions, seed 42 |
| Image size | 512×512 |
| Warm-up | One warm-up generation per config; excluded from reported measurements |
| Latency | Denoising-only generation latency |
| CLIP | open_clip ViT-B-32 laion2b; 100 × cosine similarity |
| FID | clean-fid on 300 images; absolute values are high for this small sample, so compare relatively |

## Config definitions

| Config | Model and precision | Sampling | Guidance | Additional settings |
|---|---|---|---|---|
| baseline | Stable Diffusion v1.5 fp32 | 25 steps | 7.5 | Reference config |
| fp16 | Stable Diffusion v1.5 fp16 | 25 steps | 7.5 | Half precision |
| dream | Lykon/dreamshaper-8 fp16 | 25 steps | 7.5 | DPM-Solver++; SD v1.5 safety checker attached |
| fast | Stable Diffusion v1.5 fp16 | 4 steps | 1.0 | LCM-LoRA |
| tiny | BK-SDM-Tiny fp16 | 20 steps | 7.5 | DPM-Solver |

DreamShaper-8 is a community fine-tune of SD v1.5 with the same architecture and is distributed under CreativeML OpenRAIL-M.

## 1. CLIP similarity

| Config | COCO val CLIP | Complex prompts CLIP |
|---|---:|---:|
| baseline | 33.31 | 35.20 |
| fp16 | 33.33 | 35.28 |
| dream | 34.15 | 37.26 |
| fast | 31.56 | 33.71 |
| tiny | 31.16 | 33.46 |

On the 25 complex multi-object prompts, dream scored 37.26 CLIP versus 35.28 for fp16 and 35.20 for baseline, a +1.98 gain over SD v1.5, with 2.82 s latency. The gain over SD v1.5 is larger on complex prompts (+1.98) than on COCO captions (+0.82).

### Base checkpoint comparison

On COCO val, DreamShaper scored 34.15 CLIP versus 33.33 for fp16 SD v1.5 (+0.82), the best CLIP score of all configs. It is a same-architecture SD v1.5 fine-tune, so the prompt-adherence gain came with no extra measured compute.

## 2. FID

| Config | clean-fid |
|---|---:|
| baseline | 138.0 |
| fp16 | 137.3 |
| dream | 135.4 |
| fast | 141.9 |
| tiny | 142.4 |

FID was computed against the COCO val reference images. Given the 300-image sample, the absolute FID values are high; the relative comparison is more informative.

## 3. Image generation latency

| Config | Mean denoising latency |
|---|---:|
| baseline | 6.97 s |
| fp16 | 2.97 s |
| dream | 2.97 s |
| fast | 0.52 s |
| tiny | 1.37 s |

### End-to-end app latency

Across 35 `generate_with_fallback` requests with tier Auto and a 10 s budget (25 complex prompts plus 10 long prompts of 34–41 words), after a warm-up, mean total was 4.69 s, max was 7.96 s (the first request, including initial model loading), and 100% were under 10 s. The two most-used pipelines, DreamShaper for Max and LCM for High, stayed loaded together. Typical totals were 2.1–2.6 s for High (4 candidates) and 5.7–6.8 s for Max (2 candidates). Per-image latency was 0.49–0.59 s for High and 2.8–3.3 s for Max, consistent with the benchmark tables. Benchmark latency is per image (denoising only); app total includes all candidates, CLIP reranking and post-processing. Before keeping both pipelines loaded, a tier switch reloaded the model (about 5 s; mean 6.06 s, max 9.32 s).

## 4. Peak memory

| Config | Peak VRAM |
|---|---:|
| baseline | 6226 MB |
| fp16 | 3257 MB |
| dream | 3258 MB |
| fast | 3398 MB |
| tiny | 2231 MB |

## 5. Model size

| Config | Parameters | Size |
|---|---:|---:|
| baseline | 1.066B | 4067 MB |
| fp16 | 1.066B | 2034 MB |
| dream | — | 2034 MB |
| fast | 1.133B, including unfused LoRA | 2162 MB |
| tiny | 0.530B | 1011 MB |

## 6. Quality vs computational cost

| Config | Speedup vs baseline | COCO CLIP retained | Complex-prompt CLIP retained |
|---|---:|---:|---:|
| fp16 | 2.3× | 100% | — |
| fast | 13.4× | 94.7% | 95.8% |
| tiny | 5.1× | 93.5% | 95.1% |

The fast config gives the largest measured speedup while retaining 94.7% of baseline COCO CLIP similarity. The tiny config has the lowest peak memory and model size among the evaluated configs.

### Model adaptation (LoRA)

| Training setup | Result |
|---|---|
| Adapter | Rank-8 LoRA with PEFT on attention `to_q`, `to_k`, `to_v`, and `to_out.0` |
| Training data | 1000 COCO train2017 images |
| Training steps | 1000 optimizer steps |
| Batch and accumulation | Batch size 1; gradient accumulation 4 |
| Optimizer settings | Learning rate 1e-4 |
| Precision and memory | fp16 mixed precision; gradient checkpointing |
| Training time | About 25 minutes on the RTX 5060 Laptop 8 GB |
| Evaluation split | Same 300 val2017 captions, separate from the training split |

| Metric | fp16 without LoRA | fp16 with LoRA | Observation |
|---|---:|---:|---|
| CLIP | 33.33 | 33.29 | Near the fp16 result |
| FID | 137.3 | 134.0 | 3.3 better |
| Latency | 2.97 s | 3.10 s | Unfused LoRA; `fuse_lora` would remove this overhead |
| Peak VRAM | 3257 MB | 3261 MB |  |
| Parameter increase | — | +1.6M (0.15%) |  |
| Size increase | — | +3 MB |  |

FID on 300 images is noisy, so the gain is encouraging but not conclusive.

## 7. Ablations

### Steps

| Fast steps | CLIP | FID | Latency |
|---|---:|---:|---:|
| 2 | 30.83 | 150.3 | 0.36 s |
| 4 | 31.56 | 141.9 | 0.52 s |
| 8 | 30.65 | 144.9 | 0.83 s |

Four steps gave the best measured CLIP and FID balance; High therefore uses fast at 4 steps.

### Guidance

| Guidance | CLIP | FID | Latency |
|---|---:|---:|---:|
| 1.0 | 31.56 | 141.9 | 0.53 s |
| 1.8 | 31.42 | 149.8 | 0.71 s |

Guidance 1.0 was retained. Guidance above 1 requires a second UNet pass.

### Post-processing

| Setting | CLIP | FID | Latency |
|---|---:|---:|---:|
| Off | 31.56 | 141.93 | 0.52 s |
| On | 31.52 | 141.84 | 0.53 s |

Post-processing was neutral on CLIP and FID in this comparison.

### Reproducibility

Repeated fast-4 runs gave identical CLIP and FID results, indicating that the evaluation is reproducible under the stated setup.
