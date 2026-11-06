import json
import random
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_coco_pairs(n=500, seed=42, split="val"):
    """Load up to ``n`` COCO image-caption pairs, with one caption per image."""
    if n < 0:
        raise ValueError("n must be non-negative")

    annotations_path = (
        PROJECT_ROOT / "data" / "annotations" / f"captions_{split}2017.json"
    )
    images_dir = PROJECT_ROOT / "data" / f"{split}2017"
    missing_paths = [
        path for path in (annotations_path, images_dir) if not path.exists()
    ]
    if missing_paths:
        missing = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"Required COCO dataset path(s) not found: {missing}")

    with annotations_path.open(encoding="utf-8") as file:
        data = json.load(file)

    captions_by_image = {}
    for annotation in data["annotations"]:
        captions_by_image.setdefault(annotation["image_id"], []).append(
            annotation["caption"]
        )

    images_with_captions = [
        image
        for image in data["images"]
        if image["id"] in captions_by_image
    ]
    rng = random.Random(seed)
    selected_images = rng.sample(
        images_with_captions, min(n, len(images_with_captions))
    )

    pairs = []
    for image in selected_images:
        image_path = images_dir / image["file_name"]
        if not image_path.is_file():
            raise FileNotFoundError(f"COCO image file not found: {image_path}")
        caption = rng.choice(captions_by_image[image["id"]])
        pairs.append((str(image_path), caption))

    return pairs


if __name__ == "__main__":
    for image_path, caption in load_coco_pairs(n=5):
        print((image_path, caption))
