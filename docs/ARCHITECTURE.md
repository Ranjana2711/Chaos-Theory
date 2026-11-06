# Flicker Architecture

## Runtime flow

```mermaid
flowchart TD
    UI["app.py: Gradio demo"] --> APP["generate"]
    APP --> ADAPT["generate_with_fallback"]
    ADAPT --> ENHANCE["enhance_prompt"]
    ADAPT --> ANALYZE["analyze_prompt"]
    ADAPT --> PROFILE["profile_resources"]
    PROFILE --> CHOOSE["choose_tier"]
    ANALYZE --> CHOOSE
    CHOOSE --> GEN["Generator.generate"]
    GEN --> CANDIDATES["Generated candidates"]
    CANDIDATES --> RERANK["pick_best"]
    RERANK --> PROCESS["_process_image"]
    PROCESS --> PIPELINE["run_pipeline"]
    PIPELINE --> QUALITY["quality_report"]
    QUALITY --> ARTIFACTS["detect_artifacts"]
    ARTIFACTS --> CORRECT["_correct_artifacts"]
    CORRECT --> OUTPUT["Result images, reports, and metadata"]
    OUTPUT --> UI
    GEN -->|OOM or RuntimeError| DROP["_drop_pipeline"]
    DROP --> FALLBACK["Next lower tier"]
    FALLBACK --> GEN
    ADAPT -->|append latency| HISTORY["_LATENCY_HISTORY"]
    HISTORY -->|recent latency feedback| CHOOSE
```

## Offline evaluation flow

```mermaid
flowchart TD
    CLI["parse_args"] --> PROMPTS["load_prompts"]
    PROMPTS --> COCO["load_coco_pairs"]
    PROMPTS --> EVAL["evaluate_config"]
    COCO --> EVAL
    EVAL --> WARMUP["Generator.generate warm-up; excluded"]
    EVAL --> GENERATE["Generator.generate"]
    GENERATE --> SCORES["score_images: CLIP"]
    GENERATE --> METRICS["denoising latency and peak VRAM"]
    EVAL --> FID["clean-fid on generated and real images"]
    SCORES --> SAVE["save_scores"]
    METRICS --> SAVE
    FID --> AGGREGATE["aggregate evaluation row"]
    SAVE --> AGGREGATE
    AGGREGATE --> CSV["append_results: outputs/results.csv"]
    CSV --> REPORT["P3 evaluation report prepared from recorded results"]
```

The evaluator computes the aggregate result data and writes `outputs/results.csv`. The Markdown report is a separate deliverable prepared from those recorded results.

## Component map

| Component | File | Responsibility |
|---|---|---|
| Gradio interface | [app.py](../app.py) | Collect prompts/options, invoke generation, display images and reports |
| Adaptive orchestration | [src/adaptive.py](../src/adaptive.py) | Resource profile, tier choice, fallback, candidates, reranking, post-processing |
| Model generation | [src/generate.py](../src/generate.py) | Load Diffusers models and generate images |
| Prompt analysis | [src/prompt_analyzer.py](../src/prompt_analyzer.py) | Extract prompt concepts and complexity |
| Prompt enhancement | [src/prompt_enhancer.py](../src/prompt_enhancer.py) | Remove instruction lead-ins and expand visual concepts |
| Candidate scoring | [src/rerank.py](../src/rerank.py) | Score candidate images against text with CLIP |
| CV and quality | [src/postprocess.py](../src/postprocess.py) | Classical image operations, quality reports, artifact detection |
| Dataset loading | [src/dataset.py](../src/dataset.py) | Sample COCO validation image-caption pairs |
| Offline evaluation | [src/evaluate.py](../src/evaluate.py) | Generate evaluation images, compute metrics, write aggregate results |
| Visual layer | [src/ui_theme.py](../src/ui_theme.py) | Hero, butterfly background, optional mosaic, CSS, and Gradio theme |
| Package marker | [src/__init__.py](../src/__init__.py) | Declare the `src` package |
