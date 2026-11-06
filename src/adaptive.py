import gc

import torch
from PIL import Image

from src.generate import Generator
from src.postprocess import (
    detect_artifacts,
    lanczos_resize,
    quality_report,
    run_pipeline,
)


TIERS = {
    "High": {"config": "fast", "size": 512, "steps": 8},
    "Medium": {"config": "fast", "size": 512, "steps": 4},
    "Low": {"config": "tiny", "size": 384, "steps": 15},
}

_TIER_ORDER = ("High", "Medium", "Low")
_GENERATOR = Generator()


def choose_tier(time_budget_s=10, prompt=""):
    """Choose a tier from available VRAM, prompt complexity, and time budget."""
    if not torch.cuda.is_available():
        return "Low", "CPU detected; selecting Low to use the smaller model."

    free_bytes, _ = torch.cuda.mem_get_info()
    effective_free_bytes = free_bytes + torch.cuda.memory_reserved()
    effective_free_gb = effective_free_bytes / (1024**3)
    if effective_free_gb >= 6.0:
        tier_index = 0
        reason = f"{effective_free_gb:.1f} GB effective free VRAM supports High."
    elif effective_free_gb >= 3.0:
        tier_index = 1
        reason = f"{effective_free_gb:.1f} GB effective free VRAM supports Medium."
    else:
        tier_index = 2
        reason = f"Only {effective_free_gb:.1f} GB effective free VRAM; selecting Low."

    words = prompt.split()
    complexity = (
        len(words) > 20
        or prompt.count(",") >= 2
        or prompt.lower().split().count("and") >= 2
    )
    if complexity and tier_index < len(_TIER_ORDER) - 1:
        tier_index += 1
        reason += " Complex prompt reduces the tier one level."

    if time_budget_s < 8 and tier_index == 0:
        tier_index = 1
        reason += " The time budget favors Medium over High."
    elif time_budget_s < 4 and tier_index == 1:
        tier_index = 2
        reason += " The short time budget selects Low."

    return _TIER_ORDER[tier_index], reason


def _drop_pipeline(generator):
    if generator.pipeline is not None:
        del generator.pipeline
        generator.pipeline = None
        generator.current_config = None
    gc.collect()
    torch.cuda.empty_cache()


def generate_with_fallback(
    prompt,
    tier="auto",
    seed=42,
    postprocess=True,
    time_budget_s=10,
):
    if tier == "auto":
        initial_tier, reason = choose_tier(time_budget_s, prompt)
    elif tier in TIERS:
        initial_tier = tier
        reason = f"Requested {tier} tier."
    else:
        raise ValueError(f"Unknown tier {tier!r}; choose 'auto' or one of {tuple(TIERS)}")

    start_index = _TIER_ORDER.index(initial_tier)
    fallback_happened = False
    fallback_reasons = []
    peak_mem_mb = 0.0

    for tier_name in _TIER_ORDER[start_index:]:
        settings = TIERS[tier_name]
        try:
            generated = _GENERATOR.generate(
                config=settings["config"],
                prompt=prompt,
                seed=seed,
                size=settings["size"],
                steps=settings["steps"],
            )
        except (torch.cuda.OutOfMemoryError, RuntimeError) as error:
            if tier_name == _TIER_ORDER[-1]:
                raise
            fallback_happened = True
            fallback_reasons.append(f"{tier_name} failed ({error});")
            _drop_pipeline(_GENERATOR)
            continue

        peak_mem_mb = max(peak_mem_mb, generated["peak_mem_mb"])
        raw_image = generated["image"]
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

        if fallback_happened:
            reason += " " + " ".join(fallback_reasons)
            reason += f" Fell back to {tier_name}."

        return {
            "raw_image": raw_image,
            "final_image": final_image,
            "intermediates": intermediates,
            "tier_used": tier_name,
            "reason": reason,
            "fallback_happened": fallback_happened,
            "latency_s": generated["latency_s"],
            "load_time_s": generated["load_time_s"],
            "peak_mem_mb": peak_mem_mb,
            "quality_before": quality_before,
            "quality_after": quality_after,
            "artifacts": detect_artifacts(final_image),
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
