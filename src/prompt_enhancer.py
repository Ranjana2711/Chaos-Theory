import re

from src.prompt_analyzer import analyze_prompt


NEGATIVE_PROMPT = (
    "blurry, distorted, low quality, deformed, extra limbs, watermark, text, "
    "jpeg artifacts"
)

_STYLE_TERMS = {
    "photo": (
        "professional photograph",
        "sharp focus",
        "natural lighting",
        "highly detailed",
    ),
    "cinematic": (
        "professional photograph",
        "sharp focus",
        "natural lighting",
        "highly detailed",
    ),
    "painting": ("detailed brushwork", "rich colours"),
    "illustration": ("detailed brushwork", "rich colours"),
    "anime": ("clean lineart", "vibrant colours"),
}


def enhance_prompt(prompt):
    """Append style-appropriate descriptive terms without duplicating prompt words."""
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")

    original = " ".join(prompt.strip().split())
    analysis = analyze_prompt(original)
    detected_styles = set(analysis["style"])
    if "anime" in detected_styles:
        terms = _STYLE_TERMS["anime"]
    elif detected_styles.intersection(("painting", "illustration", "watercolor", "oil painting")):
        terms = _STYLE_TERMS[
            "painting" if "painting" in detected_styles or "oil painting" in detected_styles
            else "illustration"
        ]
    else:
        terms = _STYLE_TERMS["photo"]

    added_terms = []
    for term in terms[:4]:
        pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
        if not re.search(pattern, original, flags=re.IGNORECASE):
            added_terms.append(term)

    prompt_words = original.split()[:69]
    original = " ".join(prompt_words)
    available_words = max(0, 69 - len(prompt_words))
    included_terms = []
    for term in added_terms:
        term_word_count = len(term.split())
        if term_word_count <= available_words:
            included_terms.append(term)
            available_words -= term_word_count

    enhanced_prompt = original
    if included_terms:
        enhanced_prompt = f"{original}, {', '.join(included_terms)}" if original else ", ".join(included_terms)

    return enhanced_prompt, NEGATIVE_PROMPT, included_terms


if __name__ == "__main__":
    example_prompt = (
        "A red sports car parked beside a lake, with mountains in the background, "
        "during sunset, cinematic photography"
    )
    enhanced, negative, added = enhance_prompt(example_prompt)
    print(f"Enhanced: {enhanced}")
    print(f"Negative: {negative}")
    print(f"Added terms: {added}")
