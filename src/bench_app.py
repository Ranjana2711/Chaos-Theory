import csv
from pathlib import Path

from src.adaptive import generate_with_fallback


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPLEX_PROMPTS_PATH = PROJECT_ROOT / "prompts" / "complex_prompts.txt"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "app_latency.csv"
TIME_BUDGET_S = 10

LONG_PROMPTS = (
    "A small wooden cabin stands beside a quiet lake, with a red canoe near the shore, "
    "two pine trees behind the cabin, soft clouds above distant mountains, and warm "
    "golden evening light reflected across the water.",
    "A brown dog wearing a blue scarf sits beside a wicker basket of yellow flowers, "
    "while a white cat watches from a wooden bench near the garden gate, with leafy "
    "plants, stepping stones, and gentle morning sunlight filling the peaceful yard.",
    "A crowded farmers market has a striped orange canopy over a table of red apples, "
    "green pears, yellow lemons, and purple grapes, with shoppers carrying baskets "
    "between flower stalls beneath bright banners on a clear spring afternoon.",
    "A silver bicycle leans against a brick wall beside a blue mailbox and a small "
    "flowerpot, while a brown paper parcel rests on the pavement and leafy branches "
    "cast dappled shadows across the quiet neighborhood street.",
    "Three children in colorful raincoats jump over puddles beside a park fountain, "
    "while a parent holds a bright umbrella near a row of benches, autumn trees, "
    "fallen leaves, and a distant playground under the cloudy sky.",
    "A ceramic bowl filled with steaming vegetable soup sits on a checked tablecloth, "
    "beside two slices of crusty bread, a wooden spoon, a small vase of daisies, and "
    "a glass of water near a sunlit kitchen window.",
    "A tall lighthouse with red and white stripes stands on a rocky coast above "
    "rolling ocean waves, with a small sailboat near the horizon, seabirds overhead, "
    "and a pale pink sunset glowing behind distant cliffs.",
    "A cozy library reading corner has a green armchair beside a floor lamp, a stack "
    "of old books on a wooden table, a sleeping orange cat on the rug, and tall "
    "shelves filled with colorful books along the warm quiet room.",
    "A brass clock hangs above a narrow writing desk with an open notebook, two ink "
    "pens, a blue ceramic mug, and a small potted cactus, while afternoon light "
    "enters through a window overlooking rooftops and leafy trees.",
    "A colorful hot air balloon floats above a patchwork valley of green fields, "
    "golden crops, winding roads, and a tiny river, with layered mountain ridges "
    "beneath scattered white clouds in the bright morning sky.",
)


def _load_prompts():
    if not COMPLEX_PROMPTS_PATH.is_file():
        raise FileNotFoundError(
            f"Complex prompts file not found: {COMPLEX_PROMPTS_PATH}"
        )
    with COMPLEX_PROMPTS_PATH.open(encoding="utf-8") as file:
        prompts = [line.strip() for line in file if line.strip()]
    return prompts + list(LONG_PROMPTS)


def main():
    prompts = _load_prompts()
    generate_with_fallback(
        "a red apple on a wooden table",
        tier="auto",
        time_budget_s=TIME_BUDGET_S,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        "prompt_length_words",
        "tier_used",
        "n_candidates",
        "per_image_latency_s",
        "total_s",
    )
    total_times = []
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for prompt in prompts:
            result = generate_with_fallback(
                prompt,
                tier="auto",
                time_budget_s=TIME_BUDGET_S,
            )
            row = {
                "prompt_length_words": len(prompt.split()),
                "tier_used": result["tier_used"],
                "n_candidates": result["n_candidates"],
                "per_image_latency_s": result["per_image_latency_s"],
                "total_s": result["total_s"],
            }
            writer.writerow(row)
            file.flush()
            total_times.append(result["total_s"])
            print(
                f"words={row['prompt_length_words']}, tier={row['tier_used']}, "
                f"candidates={row['n_candidates']}, "
                f"per_image={row['per_image_latency_s']:.2f}s, "
                f"total={row['total_s']:.2f}s"
            )

    mean_total = sum(total_times) / len(total_times)
    max_total = max(total_times)
    under_budget_share = sum(
        total < TIME_BUDGET_S for total in total_times
    ) / len(total_times)
    print(f"Mean total_s: {mean_total:.2f}s")
    print(f"Max total_s: {max_total:.2f}s")
    print(
        f"Share under {TIME_BUDGET_S}s: "
        f"{under_budget_share:.1%} ({OUTPUT_PATH})"
    )


if __name__ == "__main__":
    main()
