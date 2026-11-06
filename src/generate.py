import gc
import os
import re
import time
import warnings
from pathlib import Path

import psutil
import torch
from diffusers import (
    DPMSolverMultistepScheduler,
    LCMScheduler,
    StableDiffusionPipeline,
)


CONFIGS = {
    "baseline": {
        "model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "dtype": torch.float32,
        "steps": 25,
        "guidance": 7.5,
        "scheduler": None,
        "lora": None,
    },
    "fp16": {
        "model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "dtype": torch.float16,
        "steps": 25,
        "guidance": 7.5,
        "scheduler": None,
        "lora": None,
    },
    "fast": {
        "model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "dtype": torch.float16,
        "steps": 4,
        "guidance": 1.0,
        "scheduler": "lcm",
        "lora": "latent-consistency/lcm-lora-sdv1-5",
    },
    "tiny": {
        "model": "nota-ai/bk-sdm-tiny",
        "dtype": torch.float16,
        "steps": 20,
        "guidance": 7.5,
        "scheduler": "dpm",
        "lora": None,
    },
}


class Generator:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.pipeline = None
        self.current_config = None

    def load(self, config):
        if config not in CONFIGS:
            raise ValueError(
                f"Unknown config {config!r}. Choose from: {', '.join(CONFIGS)}"
            )
        if self.current_config == config and self.pipeline is not None:
            return self.pipeline

        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            self.current_config = None
            gc.collect()
            torch.cuda.empty_cache()

        settings = CONFIGS[config]
        dtype = settings["dtype"] if self.device.type == "cuda" else torch.float32
        pipeline = StableDiffusionPipeline.from_pretrained(
            settings["model"],
            dtype=dtype,
        )

        if settings["scheduler"] == "lcm":
            pipeline.scheduler = LCMScheduler.from_config(pipeline.scheduler.config)
            pipeline.load_lora_weights(settings["lora"])
        elif settings["scheduler"] == "dpm":
            pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                pipeline.scheduler.config
            )

        pipeline = pipeline.to(self.device)
        self.pipeline = pipeline
        self.current_config = config
        return pipeline

    def _truncate_prompt(self, prompt):
        token_ids = self.pipeline.tokenizer(
            prompt,
            add_special_tokens=True,
            truncation=False,
        )["input_ids"]
        if len(token_ids) > 77:
            warnings.warn(
                "Prompt exceeds 77 CLIP tokens; truncating it.",
                UserWarning,
                stacklevel=3,
            )
            prompt = self.pipeline.tokenizer.decode(
                token_ids[:77],
                skip_special_tokens=True,
            )
        return prompt

    def generate(self, config, prompt, seed=42, size=512, steps=None):
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("prompt must not be empty")
        if len(prompt) > 500:
            raise ValueError(
                "Prompt is too long; please keep it under 500 characters."
            )
        if not re.search(r"[A-Za-z0-9]", prompt):
            raise ValueError("Prompt must contain at least one word.")

        load_start = time.perf_counter()
        pipeline = self.load(config)
        load_time_s = time.perf_counter() - load_start
        prompt = self._truncate_prompt(prompt)
        settings = CONFIGS[config]
        actual_steps = settings["steps"] if steps is None else steps
        generator = torch.Generator(device=self.device).manual_seed(seed)

        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
            torch.cuda.reset_peak_memory_stats(self.device)

        start = time.perf_counter()
        result = pipeline(
            prompt,
            height=size,
            width=size,
            num_inference_steps=actual_steps,
            guidance_scale=settings["guidance"],
            generator=generator,
        )
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
            peak_mem_mb = torch.cuda.max_memory_allocated(self.device) / (1024**2)
        else:
            peak_mem_mb = (
                psutil.Process(os.getpid()).memory_info().rss / (1024**2)
            )

        return {
            "image": result.images[0],
            "load_time_s": load_time_s,
            "latency_s": time.perf_counter() - start,
            "peak_mem_mb": peak_mem_mb,
            "steps": actual_steps,
            "config": config,
        }

    def model_stats(self, config):
        pipeline = self.load(config)
        stats = {}
        total_parameters = 0
        total_size_bytes = 0

        for component_name in ("unet", "text_encoder", "vae"):
            component = getattr(pipeline, component_name)
            parameters = list(component.parameters())
            parameter_count = sum(parameter.numel() for parameter in parameters)
            size_bytes = sum(
                parameter.numel() * parameter.element_size()
                for parameter in parameters
            )
            stats[component_name] = {
                "parameters": parameter_count,
                "size_mb": size_bytes / (1024**2),
            }
            total_parameters += parameter_count
            total_size_bytes += size_bytes

        stats["total_parameters"] = total_parameters
        stats["total_size_mb"] = total_size_bytes / (1024**2)
        return stats


if __name__ == "__main__":
    generator = Generator()
    output_dir = Path(__file__).resolve().parent.parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    for config_name in CONFIGS:
        result = generator.generate(
            config_name,
            "a red apple on a wooden table",
        )
        result["image"].save(output_dir / f"test_{config_name}.png")
        print(
            f"{config_name}: {result['latency_s']:.2f}s, "
            f"{result['peak_mem_mb']:.1f} MB"
        )
        print(generator.model_stats(config_name))
