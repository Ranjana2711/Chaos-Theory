import csv
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "annotations" / "captions_train2017.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "train_subset"
IMAGE_COUNT = 1000
SEED = 42
WORKERS = 8
MAX_RETRIES = 3


def _download_image(item):
    image_id, url, caption = item
    destination = OUTPUT_DIR / f"{image_id:012d}.jpg"
    if destination.exists():
        return image_id, caption, True

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as source:
                source.load()
                image = source.convert("RGB")

            width, height = image.size
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            image = image.crop((left, top, left + side, top + side))
            image = image.resize((512, 512), Image.Resampling.LANCZOS)
            image.save(destination, format="JPEG", quality=92)
            return image_id, caption, True
        except (requests.RequestException, OSError, ValueError):
            if attempt == MAX_RETRIES:
                return image_id, caption, False

    return image_id, caption, False


def main():
    if not ANNOTATIONS_PATH.is_file():
        raise FileNotFoundError(f"Training annotations not found: {ANNOTATIONS_PATH}")

    with ANNOTATIONS_PATH.open(encoding="utf-8") as file:
        annotations = json.load(file)

    captions_by_image = {}
    for annotation in annotations["annotations"]:
        captions_by_image.setdefault(annotation["image_id"], []).append(
            annotation["caption"]
        )

    eligible_images = [
        image
        for image in annotations["images"]
        if image.get("id") in captions_by_image and image.get("coco_url")
    ]
    rng = random.Random(SEED)
    selected_images = rng.sample(
        eligible_images,
        min(IMAGE_COUNT, len(eligible_images)),
    )
    selected = [
        (
            image["id"],
            image["coco_url"],
            rng.choice(captions_by_image[image["id"]]),
        )
        for image in selected_images
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    successful = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(_download_image, item) for item in selected]
        for completed, future in enumerate(as_completed(futures), start=1):
            image_id, caption, saved = future.result()
            if saved:
                successful[image_id] = caption
            if completed % 100 == 0:
                print(f"Progress: {completed}/{len(selected)}")

    metadata_path = OUTPUT_DIR / "metadata.csv"
    with metadata_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=("file_name", "caption"))
        writer.writeheader()
        for image_id, _, _ in selected:
            if image_id in successful:
                writer.writerow(
                    {
                        "file_name": f"{image_id:012d}.jpg",
                        "caption": successful[image_id],
                    }
                )

    print(f"Finished: {len(successful)}/{len(selected)} images saved.")


if __name__ == "__main__":
    main()
