<USNS>

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
| fast | Stable Diffusion v1.5 fp16 | 4 steps | 1.0 | LCM-LoRA |
| tiny | BK-SDM-Tiny fp16 | 20 steps | 7.5 | DPM-Solver |

## 1. CLIP similarity

| Config | COCO val CLIP | Complex prompts CLIP |
|---|---:|---:|
| baseline | 33.31 | 35.20 |
| fp16 | 33.33 | 35.28 |
| fast | 31.56 | 33.71 |
| tiny | 31.16 | 33.46 |

Complex-prompt results use the supplied set of 25 multi-object prompts.

## 2. FID

| Config | clean-fid |
|---|---:|
| baseline | 138.0 |
| fp16 | 137.3 |
| fast | 141.9 |
| tiny | 142.4 |

FID was computed against the COCO val reference images. Given the 300-image sample, the absolute FID values are high; the relative comparison is more informative.

## 3. Image generation latency

| Config | Mean denoising latency |
|---|---:|
| baseline | 6.97 s |
| fp16 | 2.97 s |
| fast | 0.52 s |
| tiny | 1.37 s |

## 4. Peak memory

| Config | Peak VRAM |
|---|---:|
| baseline | 6226 MB |
| fp16 | 3257 MB |
| fast | 3398 MB |
| tiny | 2231 MB |

## 5. Model size

| Config | Parameters | Size |
|---|---:|---:|
| baseline | 1.066B | 4067 MB |
| fp16 | 1.066B | 2034 MB |
| fast | 1.133B, including unfused LoRA | 2162 MB |
| tiny | 0.530B | 1011 MB |

## 6. Quality vs computational cost

| Config | Speedup vs baseline | COCO CLIP retained | Complex-prompt CLIP retained |
|---|---:|---:|---:|
| fp16 | 2.3× | 100% | — |
| fast | 13.4× | 94.7% | 95.8% |
| tiny | 5.1× | 93.5% | 95.1% |

The fast config gives the largest measured speedup while retaining 94.7% of baseline COCO CLIP similarity. The tiny config has the lowest peak memory and model size among the evaluated configs.

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
