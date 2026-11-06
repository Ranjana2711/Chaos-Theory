import argparse
import csv
import math
import shutil
import time
from pathlib import Path

import open_clip
import torch
import torch.nn.functional as functional
from PIL import Image

from src.dataset import load_coco_pairs
from src.generate import Generator
from src.postprocess import run_pipeline


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STEPS = {"baseline": 25, "fp16": 25, "fast": 4, "tiny": 20}
SEED = 42


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate text-to-image configs.")
    parser.add_argument("--n", type=int, default=300)
    parser.add_argument("--configs", default="baseline,fp16,fast,tiny")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--postprocess", action="store_true")
    parser.add_argument("--prompts", choices=("coco", "complex"), default="coco")
    args = parser.parse_args()
    if args.n < 0:
        parser.error("--n must be non-negative")
    args.configs = [config.strip() for config in args.configs.split(",") if config.strip()]
    if not args.configs:
        parser.error("--configs must include at least one config")
    unknown = set(args.configs) - set(DEFAULT_STEPS)
    if unknown:
        parser.error(f"unknown config(s): {', '.join(sorted(unknown))}")
    if args.steps is not None and args.steps <= 0:
        parser.error("--steps must be positive")
    return args


def load_prompts(args):
    if args.prompts == "coco":
        pairs = load_coco_pairs(n=args.n, seed=SEED, split="val")
        return [caption for _, caption in pairs], pairs

    prompts_path = PROJECT_ROOT / "prompts" / "complex_prompts.txt"
    if not prompts_path.is_file():
        raise FileNotFoundError(f"Complex prompts file not found: {prompts_path}")
    with prompts_path.open(encoding="utf-8") as file:
        prompts = [line.strip() for line in file if line.strip()]
    return prompts[: args.n], None


def load_clip_model():
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="laion2b_s34b_b79k",
    )
    model = model.to("cpu").eval()
    return model, preprocess, open_clip.get_tokenizer("ViT-B-32")


def score_images(model, preprocess, tokenizer, image_paths, prompts):
    scores = []
    with torch.inference_mode():
        for image_path, prompt in zip(image_paths, prompts):
            with Image.open(image_path) as image:
                image_tensor = preprocess(image.convert("RGB")).unsqueeze(0)
            text_tokens = tokenizer([prompt]).to("cpu")
            image_features = functional.normalize(model.encode_image(image_tensor), dim=-1)
            text_features = functional.normalize(model.encode_text(text_tokens), dim=-1)
            cosine = functional.cosine_similarity(image_features, text_features).item()
            scores.append(100.0 * max(cosine, 0.0))
    return scores


def load_score_records(path):
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as file:
        return {row["file"]: row for row in csv.DictReader(file)}


def save_scores(path, records):
    with path.open("w", newline="", encoding="utf-8") as file:
        fieldnames = ("file", "prompt", "clip_score", "latency_s", "peak_mem_mb")
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def remove_unexpected_images(directory, expected_names):
    image_suffixes = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() in image_suffixes:
            if path.name not in expected_names:
                path.unlink()


def mean_std(values):
    if not values:
        return math.nan, math.nan
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance)


def evaluate_config(
    generator,
    config,
    prompts,
    pairs,
    args,
    model,
    preprocess,
    tokenizer,
):
    steps = args.steps if args.steps is not None else DEFAULT_STEPS[config]
    postprocess_tag = "pp" if args.postprocess else "no_pp"
    run_name = f"{config}_{steps}_{postprocess_tag}"
    run_dir = PROJECT_ROOT / "outputs" / "eval" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    if torch.cuda.is_available():
        torch.cuda.synchronize()
    load_start = time.perf_counter()
    generator.load(config)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    load_time_s = time.perf_counter() - load_start

    model_stats = generator.model_stats(config)
    warmup = generator.generate(
        config,
        "warm-up image; discard this result",
        seed=SEED,
        steps=steps,
    )
    del warmup

    latencies = []
    peak_vram_mb = 0.0
    image_names = [f"{index:06d}.png" for index in range(len(prompts))]
    image_paths = [run_dir / image_name for image_name in image_names]
    records_by_name = load_score_records(run_dir / "scores.csv")
    ordered_records = []

    for index, prompt in enumerate(prompts):
        image_name = image_names[index]
        image_path = image_paths[index]
        cached = records_by_name.get(image_name)
        cache_is_valid = (
            cached is not None
            and cached.get("prompt") == prompt
            and cached.get("latency_s", "") != ""
            and cached.get("peak_mem_mb", "") != ""
        )

        if image_path.exists() and cache_is_valid:
            try:
                latency_s = float(cached["latency_s"])
                peak_mem = float(cached["peak_mem_mb"])
                float(cached["clip_score"])
            except (KeyError, ValueError) as error:
                raise ValueError(
                    f"Invalid cached metrics in {run_dir / 'scores.csv'} "
                    f"for {image_name}; remove the stale image to regenerate it."
                ) from error
            record = cached
        else:
            generated = generator.generate(
                config,
                prompt,
                seed=SEED,
                steps=steps,
            )
            image = generated["image"]
            if args.postprocess:
                image, _, _, _ = run_pipeline(image, target_size=512, adaptive=True)
            image.save(image_path)
            latency_s = generated["latency_s"]
            peak_mem = generated["peak_mem_mb"]
            clip_score = score_images(
                model,
                preprocess,
                tokenizer,
                [image_path],
                [prompt],
            )[0]
            record = {
                "file": image_name,
                "prompt": prompt,
                "clip_score": clip_score,
                "latency_s": latency_s,
                "peak_mem_mb": peak_mem,
            }

        latencies.append(latency_s)
        peak_vram_mb = max(peak_vram_mb, peak_mem)
        ordered_records.append(record)
        records_by_name[image_name] = record
        progress_records = [
            records_by_name[name]
            for name, current_prompt in zip(image_names, prompts)
            if name in records_by_name
            and records_by_name[name].get("prompt") == current_prompt
            and records_by_name[name].get("latency_s", "") != ""
            and records_by_name[name].get("peak_mem_mb", "") != ""
        ]
        save_scores(run_dir / "scores.csv", progress_records)

    clip_scores = [float(record["clip_score"]) for record in ordered_records]
    clip_mean, clip_std = mean_std(clip_scores)
    latency_mean, latency_std = mean_std(latencies)

    fid_score = math.nan
    if args.prompts == "coco" and pairs:
        real_dir = PROJECT_ROOT / "outputs" / "eval" / "real_ref" / run_name
        real_dir.mkdir(parents=True, exist_ok=True)
        generated_names = set(image_names)
        remove_unexpected_images(run_dir, generated_names)
        expected_real_names = set()
        for index, (real_image_path, _) in enumerate(pairs):
            destination = real_dir / f"{index:06d}{Path(real_image_path).suffix}"
            expected_real_names.add(destination.name)
            shutil.copy2(real_image_path, destination)
        remove_unexpected_images(real_dir, expected_real_names)

        from cleanfid import fid

        fid_score = fid.compute_fid(
            str(run_dir),
            str(real_dir),
            mode="clean",
            num_workers=0,
        )

    return {
        "run_name": run_name,
        "n": len(prompts),
        "clip_mean": clip_mean,
        "clip_std": clip_std,
        "fid": fid_score,
        "latency_mean": latency_mean,
        "latency_std": latency_std,
        "load_time_s": load_time_s,
        "peak_vram_mb": peak_vram_mb,
        "params": model_stats["total_parameters"],
        "size_mb": model_stats["total_size_mb"],
    }


def append_results(path, rows):
    fieldnames = (
        "run_name",
        "n",
        "clip_mean",
        "clip_std",
        "fid",
        "latency_mean",
        "latency_std",
        "load_time_s",
        "peak_vram_mb",
        "params",
        "size_mb",
    )
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def print_table(rows):
    columns = (
        ("run_name", "Run"),
        ("n", "N"),
        ("clip_mean", "CLIP mean"),
        ("clip_std", "CLIP std"),
        ("fid", "FID"),
        ("latency_mean", "Latency mean"),
        ("latency_std", "Latency std"),
        ("load_time_s", "Load s"),
        ("peak_vram_mb", "Peak MB"),
        ("params", "Params"),
        ("size_mb", "Size MB"),
    )
    values = [
        [
            row[key] if not isinstance(row[key], float) or math.isfinite(row[key])
            else ""
            for key, _ in columns
        ]
        for row in rows
    ]
    widths = [
        max(len(header), *(len(str(row[index])) for row in values))
        for index, (_, header) in enumerate(columns)
    ]
    header_line = " | ".join(
        header.ljust(widths[index]) for index, (_, header) in enumerate(columns)
    )
    separator = "-+-".join("-" * width for width in widths)
    print(header_line)
    print(separator)
    for row in values:
        print(
            " | ".join(
                str(value).ljust(widths[index]) for index, value in enumerate(row)
            )
        )


def main():
    args = parse_args()
    prompts, pairs = load_prompts(args)
    model, preprocess, tokenizer = load_clip_model()
    generator = Generator()
    rows = [
        evaluate_config(
            generator,
            config,
            prompts,
            pairs,
            args,
            model,
            preprocess,
            tokenizer,
        )
        for config in args.configs
    ]

    results_path = PROJECT_ROOT / "outputs" / "results.csv"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    append_results(results_path, rows)
    print_table(rows)


if __name__ == "__main__":
    main()
