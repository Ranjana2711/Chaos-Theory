import csv
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional
from diffusers import (
    AutoencoderKL,
    DDPMScheduler,
    StableDiffusionPipeline,
    UNet2DConditionModel,
)
from diffusers.utils import convert_state_dict_to_diffusers
from peft import LoraConfig
from peft.utils import get_peft_model_state_dict
from PIL import Image
from transformers import CLIPTextModel, CLIPTokenizer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
METADATA_PATH = PROJECT_ROOT / "data" / "train_subset" / "metadata.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lora_coco"
IMAGE_SIZE = 512
MAX_TEXT_LENGTH = 77
BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 4
OPTIMIZER_STEPS = 1000
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-2
SEED = 42


def _load_metadata():
    if not METADATA_PATH.is_file():
        raise FileNotFoundError(f"Training metadata not found: {METADATA_PATH}")

    with METADATA_PATH.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"No training examples found in {METADATA_PATH}")
    if any(not row.get("file_name") or not row.get("caption") for row in rows):
        raise ValueError(f"Metadata must contain file_name and caption: {METADATA_PATH}")
    return rows


def _image_tensor(path):
    with Image.open(path) as source:
        image = source.convert("RGB")
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize(
            (IMAGE_SIZE, IMAGE_SIZE),
            Image.Resampling.LANCZOS,
        )
        array = np.asarray(image, dtype=np.float32) / 127.5 - 1.0
    return torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)


def _cache_training_data(rows, device):
    tokenizer = CLIPTokenizer.from_pretrained(MODEL_ID, subfolder="tokenizer")
    vae = AutoencoderKL.from_pretrained(
        MODEL_ID,
        subfolder="vae",
        torch_dtype=torch.float16,
    ).to(device)
    text_encoder = CLIPTextModel.from_pretrained(
        MODEL_ID,
        subfolder="text_encoder",
        torch_dtype=torch.float16,
    ).to(device)
    vae.eval()
    text_encoder.eval()

    latents = []
    text_embeddings = []
    try:
        with torch.inference_mode():
            for index, row in enumerate(rows, start=1):
                image_path = METADATA_PATH.parent / row["file_name"]
                pixels = _image_tensor(image_path).to(
                    device=device,
                    dtype=torch.float16,
                )
                latent = (
                    vae.encode(pixels).latent_dist.sample()
                    * vae.config.scaling_factor
                )
                tokens = tokenizer(
                    row["caption"],
                    max_length=MAX_TEXT_LENGTH,
                    padding="max_length",
                    truncation=True,
                    return_tensors="pt",
                ).input_ids.to(device)
                embedding = text_encoder(tokens)[0]
                latents.append(latent.squeeze(0).to(device="cpu", dtype=torch.float16))
                text_embeddings.append(
                    embedding.squeeze(0).to(device="cpu", dtype=torch.float16)
                )
                if index % 100 == 0:
                    print(f"Cached {index}/{len(rows)} training examples.")
    finally:
        del vae
        del text_encoder
        torch.cuda.empty_cache()

    return latents, text_embeddings


def _train_unet(latents, text_embeddings, device):
    scheduler = DDPMScheduler.from_pretrained(MODEL_ID, subfolder="scheduler")
    unet = UNet2DConditionModel.from_pretrained(
        MODEL_ID,
        subfolder="unet",
        torch_dtype=torch.float16,
    ).to(device)
    unet.requires_grad_(False)
    unet.enable_gradient_checkpointing()
    unet.add_adapter(
        LoraConfig(
            r=8,
            lora_alpha=8,
            init_lora_weights="gaussian",
            target_modules=["to_k", "to_q", "to_v", "to_out.0"],
        )
    )

    trainable_parameters = []
    for parameter in unet.parameters():
        if parameter.requires_grad:
            parameter.data = parameter.data.float()
            trainable_parameters.append(parameter)
    if not trainable_parameters:
        raise RuntimeError("LoRA adapter did not expose any trainable parameters.")

    optimizer = torch.optim.AdamW(
        trainable_parameters,
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )
    scaler = torch.amp.GradScaler("cuda")
    unet.train()
    rng = random.Random(SEED)
    order = list(range(len(latents)))
    rng.shuffle(order)
    cursor = 0
    history = []
    interval_loss = 0.0
    interval_microbatches = 0
    started_at = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)

    for optimizer_step in range(1, OPTIMIZER_STEPS + 1):
        for _ in range(GRADIENT_ACCUMULATION_STEPS):
            if cursor >= len(order):
                rng.shuffle(order)
                cursor = 0
            sample_index = order[cursor]
            cursor += 1

            clean_latents = latents[sample_index].unsqueeze(0).to(
                device=device,
                dtype=torch.float16,
            )
            encoder_hidden_states = text_embeddings[sample_index].unsqueeze(0).to(
                device=device,
                dtype=torch.float16,
            )
            noise = torch.randn_like(clean_latents)
            timesteps = torch.randint(
                0,
                scheduler.config.num_train_timesteps,
                (BATCH_SIZE,),
                device=device,
                dtype=torch.long,
            )
            noisy_latents = scheduler.add_noise(clean_latents, noise, timesteps)

            with torch.autocast(device_type="cuda", dtype=torch.float16):
                prediction = unet(
                    noisy_latents,
                    timesteps,
                    encoder_hidden_states=encoder_hidden_states,
                ).sample
                loss = functional.mse_loss(
                    prediction.float(),
                    noise.float(),
                    reduction="mean",
                )

            scaler.scale(loss / GRADIENT_ACCUMULATION_STEPS).backward()
            interval_loss += float(loss.detach())
            interval_microbatches += 1

        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(trainable_parameters, max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)

        if optimizer_step % 50 == 0:
            elapsed = time.perf_counter() - started_at
            average_loss = interval_loss / interval_microbatches
            eta_seconds = elapsed / optimizer_step * (OPTIMIZER_STEPS - optimizer_step)
            history.append(
                {
                    "optimizer_step": optimizer_step,
                    "average_loss": average_loss,
                    "elapsed_seconds": elapsed,
                    "eta_seconds": eta_seconds,
                }
            )
            print(
                f"Step {optimizer_step}/{OPTIMIZER_STEPS}: "
                f"average loss={average_loss:.6f}, ETA={eta_seconds / 60:.1f} min"
            )
            interval_loss = 0.0
            interval_microbatches = 0

    return unet, history


def _save_training_output(unet, history):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    peft_state = get_peft_model_state_dict(unet)
    diffusers_state = convert_state_dict_to_diffusers(peft_state)
    StableDiffusionPipeline.save_lora_weights(
        str(OUTPUT_DIR),
        unet_lora_layers=diffusers_state,
    )

    loss_path = OUTPUT_DIR / "loss.csv"
    with loss_path.open("w", newline="", encoding="utf-8") as file:
        fieldnames = (
            "optimizer_step",
            "average_loss",
            "elapsed_seconds",
            "eta_seconds",
        )
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history)


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("LoRA training requires a CUDA-enabled GPU.")

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    device = torch.device("cuda")

    rows = _load_metadata()
    latents, text_embeddings = _cache_training_data(rows, device)
    unet, history = _train_unet(latents, text_embeddings, device)
    _save_training_output(unet, history)
    print(f"Saved LoRA weights and loss log to {OUTPUT_DIR}.")


if __name__ == "__main__":
    main()
