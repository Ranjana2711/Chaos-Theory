import gc
import math
import re
from collections import deque

import cv2
import numpy as np
import psutil
import torch
from PIL import Image

from src.generate import Generator
from src.prompt_analyzer import analyze_prompt
from src.prompt_enhancer import ANIMALS, CONCEPT_MAP, NEGATIVE_PROMPT, enhance_prompt
from src.postprocess import (
    detect_artifacts,
    lanczos_resize,
    quality_report,
    run_pipeline,
)
from src.rerank import pick_best


TIERS = {
    "Max": {
        "config": "dream",
        "size": 512,
        "steps": 25,
        "guidance": 7.5,
        "negative_prompt": NEGATIVE_PROMPT,
    },
    # Steps ablation (CLIP): 2 steps 30.83, 4 steps 31.56, 8 steps 30.65.
    "High": {"config": "fast", "size": 512, "steps": 4},
    "Medium": {"config": "fast", "size": 512, "steps": 2},
    "Low": {"config": "tiny", "size": 384, "steps": 15},
}

_TIER_ORDER = ("Max", "High", "Medium", "Low")
_GENERATOR = Generator()
_LATENCY_HISTORY = deque(maxlen=5)
_CONFIG_LATENCY_ESTIMATES = {
    ("dream", 25): 2.9,
    ("fp16", 25): 3.0,
    ("fast", 4): 0.55,
    ("fast", 2): 0.4,
    ("tiny", 15): 1.4,
}
_RARE_CONCEPTS = ("ghost", "headphones", "dragon", "spirit")
FRANCHISE_TERMS = (
    "marvel",
    "spider-man",
    "spiderman",
    "iron man",
    "avengers",
    "batman",
    "superman",
    "disney",
    "pixar",
    "pokemon",
    "pikachu",
    "mickey mouse",
    "harry potter",
    "naruto",
)
IP_WARNING = (
    "This prompt names a copyrighted character or franchise. Try describing an "
    "original character instead, e.g. 'a masked superhero in a red and blue suit'."
)


def _process_image(raw_image, postprocess):
    if postprocess:
        final_image, intermediates, quality_before, quality_after = run_pipeline(
            raw_image,
            target_size=512,
            adaptive=True,
        )
    else:
        final_image = raw_image
        intermediates = []
        if final_image.size != (512, 512):
            final_image = lanczos_resize(final_image, 512)
            intermediates.append(("lanczos_resize", final_image.copy()))
        quality_before = quality_report(raw_image)
        quality_after = quality_report(final_image)
    return final_image, intermediates, quality_before, quality_after


def _correct_artifacts(image, artifacts):
    corrected = image.convert("RGB")
    corrections = []

    if artifacts["oversaturated"]:
        rgb = np.asarray(corrected)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * 0.7, 0, 255).astype(
            np.uint8
        )
        corrected = Image.fromarray(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB))
        corrections.append(("reduce_saturation", corrected.copy()))

    if artifacts["overexposed"] or artifacts["underexposed"]:
        gamma = 1.25 if artifacts["overexposed"] else 0.75
        rgb = np.asarray(corrected).astype(np.float32) / 255.0
        corrected = Image.fromarray(
            np.clip(np.power(rgb, gamma) * 255.0, 0, 255).astype(np.uint8)
        )
        corrections.append(("gamma_correction", corrected.copy()))

    return corrected, corrections


def profile_resources():
    """Return available GPU and system-memory information."""
    memory = psutil.virtual_memory()
    resources = {
        "device_type": "cuda" if torch.cuda.is_available() else "cpu",
        "free_vram_mb": None,
        "total_vram_mb": None,
        "system_ram_free_mb": memory.available / (1024**2),
        "system_ram_total_mb": memory.total / (1024**2),
        "gpu_utilization_percent": None,
    }

    if resources["device_type"] == "cuda":
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        resources["free_vram_mb"] = free_bytes / (1024**2)
        resources["total_vram_mb"] = total_bytes / (1024**2)
        try:
            resources["gpu_utilization_percent"] = torch.cuda.utilization()
        except Exception:
            resources["gpu_utilization_percent"] = None

    return resources


def choose_tier(time_budget_s=10, prompt=""):
    """Choose a tier using resources, prompt complexity, time, and recent latency."""
    resources = profile_resources()
    prompt_analysis = analyze_prompt(prompt)
    complexity_score = prompt_analysis["complexity_score"]
    effective_free_gb = 0.0
    if resources["device_type"] == "cpu":
        tier_index = _TIER_ORDER.index("Low")
        reason = "CPU detected; selecting Low to use the smaller model."
    else:
        effective_free_bytes = (
            resources["free_vram_mb"] * (1024**2) + torch.cuda.memory_reserved()
        )
        effective_free_gb = effective_free_bytes / (1024**3)
        if (
            complexity_score >= 0.5
            and time_budget_s >= 5
            and effective_free_gb >= 4.0
        ):
            tier_index = _TIER_ORDER.index("Max")
            reason = (
                f"Selecting Max: prompt complexity {complexity_score:.2f} >= 0.50, "
                f"time budget {time_budget_s:.1f}s >= 5s, and "
                f"{effective_free_gb:.1f} GB effective free VRAM >= 4 GB."
            )
        elif effective_free_gb >= 6.0:
            tier_index = _TIER_ORDER.index("High")
            reason = f"{effective_free_gb:.1f} GB effective free VRAM supports High."
        elif effective_free_gb >= 3.0:
            tier_index = _TIER_ORDER.index("Medium")
            reason = f"{effective_free_gb:.1f} GB effective free VRAM supports Medium."
        else:
            tier_index = _TIER_ORDER.index("Low")
            reason = f"Only {effective_free_gb:.1f} GB effective free VRAM; selecting Low."

    max_selected = tier_index == _TIER_ORDER.index("Max")
    if (
        not max_selected
        and complexity_score >= 0.6
        and tier_index < _TIER_ORDER.index("Low")
    ):
        tier_index += 1
        reason += f" Prompt complexity ({complexity_score:.2f}) reduces the tier one level."

    if time_budget_s < 8 and tier_index == _TIER_ORDER.index("High"):
        tier_index = _TIER_ORDER.index("Medium")
        reason += " The time budget favors Medium over High."
    elif time_budget_s < 4 and tier_index == _TIER_ORDER.index("Medium"):
        tier_index = _TIER_ORDER.index("Low")
        reason += " The short time budget selects Low."

    if _LATENCY_HISTORY and _LATENCY_HISTORY[-1] > time_budget_s:
        if tier_index < len(_TIER_ORDER) - 1:
            tier_index += 1
            reason += " The previous generation exceeded the time budget; lowering one tier."
        else:
            reason += " The previous generation exceeded the time budget; already at Low."
    elif (
        len(_LATENCY_HISTORY) >= 3
        and all(latency < 0.4 * time_budget_s for latency in list(_LATENCY_HISTORY)[-3:])
        and tier_index > _TIER_ORDER.index("High")
    ):
        tier_index -= 1
        reason += " The last three generations were under 40% of budget; raising one tier."

    return _TIER_ORDER[tier_index], reason


def _drop_pipeline(generator):
    if generator.pipeline is not None:
        del generator.pipeline
        generator.pipeline = None
        generator.current_config = None
    gc.collect()
    torch.cuda.empty_cache()


def _record_config_latency(settings, latency_s):
    key = (settings["config"], settings["steps"])
    _CONFIG_LATENCY_ESTIMATES[key] = latency_s


def _emphasis_terms(prompt, prompt_analysis, concept_terms, subject=""):
    terms = list(concept_terms)
    animal_search_text = subject or prompt
    for animal in ANIMALS:
        if re.search(
            r"(?<!\w)" + re.escape(animal) + r"(?!\w)",
            animal_search_text,
            flags=re.IGNORECASE,
        ):
            terms.append(animal)
            break
    for term in _RARE_CONCEPTS:
        if term in prompt_analysis["objects"] or re.search(
            r"(?<!\w)" + re.escape(term) + r"(?!\w)",
            prompt,
            flags=re.IGNORECASE,
        ):
            terms.append(term)
    return list(dict.fromkeys(terms))


def generate_with_fallback(
    prompt,
    tier="auto",
    seed=42,
    postprocess=True,
    time_budget_s=10,
    enhance=True,
    num_candidates="auto",
):
    original_prompt = prompt
    if any(
        re.search(
            r"(?<!\w)" + re.escape(term) + r"(?!\w)",
            original_prompt,
            flags=re.IGNORECASE,
        )
        for term in FRANCHISE_TERMS
    ):
        return {"ip_warning": IP_WARNING}

    if enhance:
        (
            generation_prompt,
            negative_prompt,
            added_terms,
            concept_terms,
            subject,
        ) = enhance_prompt(prompt)
    else:
        generation_prompt = prompt
        negative_prompt = None
        added_terms = []
        concept_terms = []
        subject = ""

    prompt_analysis = analyze_prompt(generation_prompt)
    weighted_terms = _emphasis_terms(
        generation_prompt, prompt_analysis, concept_terms, subject
    )
    animal_subject = any(term in ANIMALS for term in weighted_terms)
    emphasis_weight = 1.3 if animal_subject else 1.4
    emphasis = {term: emphasis_weight for term in weighted_terms} or None

    if tier == "auto":
        initial_tier, reason = choose_tier(time_budget_s, generation_prompt)
        if weighted_terms:
            resources = profile_resources()
            can_use_max = (
                resources["device_type"] == "cuda"
                and time_budget_s >= 5
                and (
                    resources["free_vram_mb"] * (1024**2)
                    + torch.cuda.memory_reserved()
                ) / (1024**3) >= 4.0
            )
            initial_tier = "Max" if can_use_max else "High"
            reason += (
                " Applying concept grounding: selecting "
                f"{initial_tier} based on available VRAM and time."
            )
    elif tier in TIERS:
        initial_tier = tier
        reason = f"Requested {tier} tier."
    else:
        raise ValueError(f"Unknown tier {tier!r}; choose 'auto' or one of {tuple(TIERS)}")

    if num_candidates == "auto":
        settings = TIERS[initial_tier]
        latency_key = (settings["config"], settings["steps"])
        latency_estimate = _CONFIG_LATENCY_ESTIMATES[latency_key]
        candidate_count = max(
            1,
            min(4, math.floor(0.8 * time_budget_s / latency_estimate)),
        )
        reason += (
            f" {candidate_count} candidates within {time_budget_s:g} s budget."
        )
    elif isinstance(num_candidates, int) and not isinstance(num_candidates, bool):
        if num_candidates < 1:
            raise ValueError("num_candidates must be positive or 'auto'")
        candidate_count = num_candidates
    else:
        raise ValueError("num_candidates must be a positive integer or 'auto'")
    start_index = _TIER_ORDER.index(initial_tier)
    fallback_happened = False
    fallback_reasons = []
    peak_mem_mb = 0.0
    total_latency_s = 0.0
    total_load_time_s = 0.0
    rerank_prompt = original_prompt
    if weighted_terms:
        concept_descriptions = [
            CONCEPT_MAP[concept] for concept in concept_terms if concept in CONCEPT_MAP
        ]
        rerank_prompt = ", ".join(
            part for part in (subject, *concept_descriptions, *weighted_terms) if part
        )

    for tier_name in _TIER_ORDER[start_index:]:
        settings = TIERS[tier_name]
        candidates = []
        try:
            for candidate_index in range(candidate_count):
                generated = _GENERATOR.generate(
                    config=settings["config"],
                    prompt=generation_prompt,
                    seed=seed + candidate_index,
                    size=settings["size"],
                    steps=settings["steps"],
                    negative_prompt=negative_prompt or settings.get("negative_prompt"),
                    guidance=settings.get("guidance"),
                    emphasis=emphasis,
                )
                candidates.append(generated["image"])
                total_latency_s += generated["latency_s"]
                _record_config_latency(settings, generated["latency_s"])
                total_load_time_s += generated["load_time_s"]
                peak_mem_mb = max(peak_mem_mb, generated["peak_mem_mb"])
        except (torch.cuda.OutOfMemoryError, RuntimeError) as error:
            if tier_name == _TIER_ORDER[-1]:
                raise
            fallback_happened = True
            fallback_reasons.append(f"{tier_name} failed ({error});")
            _drop_pipeline(_GENERATOR)
            continue

        chosen_index, candidate_scores = pick_best(candidates, rerank_prompt)
        raw_image = candidates[chosen_index]
        final_image, intermediates, quality_before, quality_after = _process_image(
            raw_image, postprocess
        )
        artifacts = detect_artifacts(final_image)
        artifact_retry = artifacts["blank_or_black"]

        if artifact_retry:
            generated = _GENERATOR.generate(
                config=settings["config"],
                prompt=generation_prompt,
                seed=seed + 1,
                size=settings["size"],
                steps=settings["steps"],
                negative_prompt=negative_prompt or settings.get("negative_prompt"),
                guidance=settings.get("guidance"),
                emphasis=emphasis,
            )
            total_latency_s += generated["latency_s"]
            _record_config_latency(settings, generated["latency_s"])
            total_load_time_s += generated["load_time_s"]
            peak_mem_mb = max(peak_mem_mb, generated["peak_mem_mb"])
            candidates[chosen_index] = generated["image"]
            chosen_index, candidate_scores = pick_best(candidates, rerank_prompt)
            raw_image = candidates[chosen_index]
            final_image, intermediates, quality_before, quality_after = _process_image(
                raw_image, postprocess
            )
            artifacts = detect_artifacts(final_image)

        final_image, corrections = _correct_artifacts(final_image, artifacts)
        intermediates.extend(corrections)
        if corrections:
            quality_after = quality_report(final_image)
            artifacts = detect_artifacts(final_image)

        if fallback_happened:
            reason += " " + " ".join(fallback_reasons)
            reason += f" Fell back to {tier_name}."
        if emphasis:
            reason += f" Applied emphasis to: {', '.join(weighted_terms)}."

        latency_s = total_latency_s
        _LATENCY_HISTORY.append(latency_s)
        return {
            "raw_image": raw_image,
            "final_image": final_image,
            "candidates": candidates,
            "candidate_scores": candidate_scores,
            "chosen_index": chosen_index,
            "intermediates": intermediates,
            "tier_used": tier_name,
            "reason": reason,
            "fallback_happened": fallback_happened,
            "latency_s": latency_s,
            "load_time_s": total_load_time_s,
            "peak_mem_mb": peak_mem_mb,
            "artifact_retry": artifact_retry,
            "original_prompt": original_prompt,
            "enhanced_prompt": generation_prompt,
            "added_terms": added_terms,
            "concept_terms": concept_terms,
            "subject": subject,
            "prompt_analysis": prompt_analysis,
            "resources": profile_resources(),
            "quality_before": quality_before,
            "quality_after": quality_after,
            "artifacts": artifacts,
        }

    raise RuntimeError("No generation tier was available")


if __name__ == "__main__":
    for example_prompt in (
        "a red apple on a wooden table",
        "a busy street market at sunset, with colorful stalls and people shopping",
    ):
        result = generate_with_fallback(example_prompt, tier="auto")
        print(
            f"{example_prompt!r}: tier={result['tier_used']}, "
            f"fallback={result['fallback_happened']}, "
            f"latency={result['latency_s']:.2f}s, "
            f"load={result['load_time_s']:.2f}s, "
            f"peak memory={result['peak_mem_mb']:.1f} MB"
        )
        print(f"Reason: {result['reason']}")
        print(f"Quality before: {result['quality_before']}")
        print(f"Quality after: {result['quality_after']}")
        print(f"Artifacts: {result['artifacts']}")
