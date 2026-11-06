import gc
import math
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
from diffusers.pipelines.stable_diffusion.safety_checker import (
    StableDiffusionSafetyChecker,
)
from transformers import CLIPImageProcessor


SAFETY_COMPONENTS_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"

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
    "fp16_lora": {
        "model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "dtype": torch.float16,
        "steps": 25,
        "guidance": 7.5,
        "scheduler": None,
        "lora": None,
        "lora_path": "outputs/lora_coco",
    },
    "dream": {
        "model": "Lykon/dreamshaper-8",
        "dtype": torch.float16,
        "steps": 25,
        "guidance": 7.5,
        "scheduler": "dpm",
        "lora": None,
        "safety_components_model": SAFETY_COMPONENTS_MODEL,
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
        lora_path = None
        if config == "fp16_lora":
            lora_path = Path(__file__).resolve().parent.parent / settings["lora_path"]
            if not lora_path.is_dir():
                raise FileNotFoundError(
                    f"LoRA weights not found at {lora_path}; "
                    "run python -m src.train_lora first."
                )

        dtype = settings["dtype"] if self.device.type == "cuda" else torch.float32
        pipeline_kwargs = {}
        safety_model = settings.get("safety_components_model")
        if safety_model is not None:
            pipeline_kwargs["safety_checker"] = (
                StableDiffusionSafetyChecker.from_pretrained(
                    safety_model,
                    subfolder="safety_checker",
                    torch_dtype=dtype,
                )
            )
            pipeline_kwargs["feature_extractor"] = CLIPImageProcessor.from_pretrained(
                safety_model,
                subfolder="feature_extractor",
            )
        pipeline = StableDiffusionPipeline.from_pretrained(
            settings["model"],
            dtype=dtype,
            **pipeline_kwargs,
        )

        if lora_path is not None:
            pipeline.load_lora_weights(str(lora_path))

        if settings["scheduler"] == "lcm":
            pipeline.scheduler = LCMScheduler.from_config(pipeline.scheduler.config)
            pipeline.load_lora_weights(settings["lora"])
        elif settings["scheduler"] == "dpm":
            pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                pipeline.scheduler.config,
                algorithm_type="dpmsolver++",
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

    def _encode_prompt_with_emphasis(self, prompt, negative_prompt, emphasis):
        if not isinstance(emphasis, dict):
            raise TypeError("emphasis must be a dict mapping words to weights")

        tokenizer = self.pipeline.tokenizer
        tokenized = tokenizer(
            prompt,
            max_length=77,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        input_ids = tokenized.input_ids.to(self.device)
        attention_mask = tokenized.attention_mask.to(self.device)

        text_encoder_kwargs = {}
        if getattr(self.pipeline.text_encoder.config, "use_attention_mask", False):
            text_encoder_kwargs["attention_mask"] = attention_mask

        with torch.no_grad():
            prompt_embeds = self.pipeline.text_encoder(
                input_ids,
                **text_encoder_kwargs,
            )[0]
            original_mean = prompt_embeds.mean()
            weighted_embeds = prompt_embeds.clone()

            for word, weight in emphasis.items():
                if not isinstance(word, str) or not word.strip():
                    raise ValueError("emphasis keys must be non-empty words")
                if not isinstance(weight, (int, float)) or isinstance(weight, bool):
                    raise TypeError(f"emphasis weight for {word!r} must be numeric")
                if not math.isfinite(weight):
                    raise ValueError(f"emphasis weight for {word!r} must be finite")

                word_pattern = re.compile(
                    r"(?<!\w)" + re.escape(word.strip()) + r"(?!\w)",
                    flags=re.IGNORECASE,
                )
                for match in word_pattern.finditer(prompt):
                    prefix_ids = tokenizer(
                        prompt[:match.start()],
                        add_special_tokens=False,
                        truncation=False,
                    )["input_ids"]
                    end_ids = tokenizer(
                        prompt[:match.end()],
                        add_special_tokens=False,
                        truncation=False,
                    )["input_ids"]
                    token_start = 1 + len(prefix_ids)
                    token_end = 1 + len(end_ids)
                    token_end = min(token_end, input_ids.shape[1] - 1)
                    if token_start < token_end:
                        weighted_embeds[:, token_start:token_end, :] *= float(weight)

            weighted_mean = weighted_embeds.mean()
            if torch.isfinite(weighted_mean) and abs(float(weighted_mean)) > 1e-8:
                weighted_embeds *= original_mean / weighted_mean

            negative_text = negative_prompt or ""
            negative_tokens = tokenizer(
                negative_text,
                max_length=77,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            negative_ids = negative_tokens.input_ids.to(self.device)
            negative_kwargs = {}
            if getattr(self.pipeline.text_encoder.config, "use_attention_mask", False):
                negative_kwargs["attention_mask"] = negative_tokens.attention_mask.to(
                    self.device
                )
            negative_prompt_embeds = self.pipeline.text_encoder(
                negative_ids,
                **negative_kwargs,
            )[0]

        return weighted_embeds, negative_prompt_embeds

    def generate(
        self,
        config,
        prompt,
        seed=42,
        size=512,
        steps=None,
        negative_prompt=None,
        guidance=None,
        emphasis=None,
    ):
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
        actual_guidance = settings["guidance"] if guidance is None else guidance
        generator = torch.Generator(device=self.device).manual_seed(seed)

        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
            torch.cuda.reset_peak_memory_stats(self.device)

        if emphasis is not None:
            prompt_embeds, negative_prompt_embeds = self._encode_prompt_with_emphasis(
                prompt,
                negative_prompt,
                emphasis,
            )
        start = time.perf_counter()
        if emphasis is not None:
            result = pipeline(
                prompt_embeds=prompt_embeds,
                negative_prompt_embeds=negative_prompt_embeds,
                height=size,
                width=size,
                num_inference_steps=actual_steps,
                guidance_scale=actual_guidance,
                generator=generator,
            )
        else:
            result = pipeline(
                prompt,
                height=size,
                width=size,
                num_inference_steps=actual_steps,
                guidance_scale=actual_guidance,
                negative_prompt=negative_prompt,
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
