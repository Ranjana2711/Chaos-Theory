from pathlib import Path

import open_clip
import torch
import torch.nn.functional as functional
from PIL import Image


_MODEL = None
_PREPROCESS = None
_TOKENIZER = None
_DEVICE = None


def _load_model():
    global _MODEL, _PREPROCESS, _TOKENIZER, _DEVICE

    if _MODEL is None:
        _DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _MODEL, _, _PREPROCESS = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k",
        )
        _MODEL = _MODEL.to(device=_DEVICE)
        if _DEVICE.type == "cuda":
            _MODEL = _MODEL.half()
        _MODEL.eval()
        _TOKENIZER = open_clip.get_tokenizer("ViT-B-32")
    return _MODEL, _PREPROCESS, _TOKENIZER, _DEVICE


def _to_pil_image(image):
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    if isinstance(image, (str, Path)):
        with Image.open(image) as opened:
            return opened.convert("RGB")
    raise TypeError("image must be a PIL image or an image file path")


def _score_images(images, prompt):
    model, preprocess, tokenizer, device = _load_model()
    image_tensors = torch.stack(
        [preprocess(_to_pil_image(image)) for image in images]
    ).to(device)
    text_tokens = tokenizer([prompt]).to(device)
    if device.type == "cuda":
        image_tensors = image_tensors.half()

    with torch.inference_mode():
        image_features = functional.normalize(model.encode_image(image_tensors), dim=-1)
        text_features = functional.normalize(model.encode_text(text_tokens), dim=-1)
        cosine_scores = (image_features @ text_features.T).squeeze(1)
        return [100.0 * max(float(score), 0.0) for score in cosine_scores.cpu()]


def clip_score(image, prompt):
    """Return the CLIP similarity score scaled to 0-100."""
    return _score_images([image], prompt)[0]


def pick_best(images, prompt):
    """Return the index of the highest-scoring image and all candidate scores."""
    if not images:
        raise ValueError("images must contain at least one candidate")
    scores = _score_images(images, prompt)
    return max(range(len(scores)), key=scores.__getitem__), scores


if __name__ == "__main__":
    outputs_dir = Path(__file__).resolve().parent.parent / "outputs"
    candidates = sorted(
        path
        for path in outputs_dir.glob("*.png")
        if path.name.startswith("test_")
    )[:2]
    if len(candidates) < 2:
        raise FileNotFoundError(
            f"Expected two test PNG images in {outputs_dir}, found {len(candidates)}"
        )

    prompt = "a red apple on a wooden table"
    best_index, candidate_scores = pick_best(candidates, prompt)
    for path, score in zip(candidates, candidate_scores):
        print(f"{path.name}: {score:.2f}")
    print(f"Best: {candidates[best_index].name}")
