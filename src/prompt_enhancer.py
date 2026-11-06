import re

from src.prompt_analyzer import analyze_prompt


NEGATIVE_PROMPT = (
    "blurry, distorted, low quality, deformed, extra limbs, watermark, text, "
    "jpeg artifacts"
)

CONCEPT_MAP = {
    "ghost": "translucent glowing white ghostly figure, spectral apparition",
    "spirit": "glowing ethereal figure",
    "listening to music": "wearing large over-ear headphones, musical notes in the air",
    "music": "wearing large over-ear headphones, musical notes in the air",
    "headphones": "large over-ear headphones clearly visible on the head",
    "dragon": "large scaly dragon with wings",
    "angel": "figure with large white feathered wings and halo",
    "robot": "metallic humanoid robot",
}

_LEADING_INSTRUCTIONS = (
    "show me",
    "an image of",
    "a picture of",
    "give me",
    "generate",
    "create",
    "draw",
    "make",
    "please",
)

_SUBJECT_BOUNDARIES = (
    "flying", "standing", "sitting", "holding", "wearing", "looking",
    "running", "walking", "playing", "with", "in", "on", "at", "beside",
    "near", "under", "over", "against", "during", "while", "and",
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


def _remove_leading_instructions(prompt):
    cleaned = prompt.strip()
    instruction_pattern = re.compile(
        r"^(?:" + "|".join(
            re.escape(instruction) for instruction in _LEADING_INSTRUCTIONS
        ) + r")\b[\s,:-]*",
        flags=re.IGNORECASE,
    )
    while True:
        match = instruction_pattern.match(cleaned)
        if not match:
            return cleaned
        cleaned = cleaned[match.end():].lstrip()


def _find_subject(prompt, analysis):
    noun_terms = set(analysis["objects"]) | set(CONCEPT_MAP)
    noun_pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(
            re.escape(term) for term in sorted(noun_terms, key=len, reverse=True)
        ) + r")(?!\w)",
        flags=re.IGNORECASE,
    ) if noun_terms else None
    noun_match = noun_pattern.search(prompt) if noun_pattern else None

    if noun_match:
        subject_end = noun_match.end()
    else:
        boundary_pattern = re.compile(
            r"\b(?:" + "|".join(
                re.escape(word) for word in _SUBJECT_BOUNDARIES
            ) + r")\b|[,.;:]",
            flags=re.IGNORECASE,
        )
        boundary_match = boundary_pattern.search(prompt)
        subject_end = boundary_match.start() if boundary_match else len(prompt)

    return prompt[:subject_end].strip(" ,.;:").strip()


def enhance_prompt(prompt):
    """Expand concepts and append style-appropriate descriptive terms."""
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")

    analysis_prompt = " ".join(_remove_leading_instructions(prompt).split())
    analysis = analyze_prompt(analysis_prompt)
    subject = _find_subject(analysis_prompt, analysis)

    concept_matches = []
    occupied = []
    for concept in sorted(CONCEPT_MAP, key=len, reverse=True):
        pattern = re.compile(
            r"(?<!\w)" + re.escape(concept) + r"(?!\w)",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(analysis_prompt):
            if any(match.start() < end and match.end() > start for start, end in occupied):
                continue
            concept_matches.append((match.start(), concept))
            occupied.append((match.start(), match.end()))
    concept_terms = [
        concept for _, concept in sorted(concept_matches)
    ]

    expanded_prompt = analysis_prompt
    expansions = [CONCEPT_MAP[concept] for concept in concept_terms]
    if expansions and subject:
        insertion_point = len(subject)
        expanded_prompt = (
            f"{analysis_prompt[:insertion_point]}, {', '.join(expansions)}"
            f"{analysis_prompt[insertion_point:]}"
        )
    elif expansions:
        expanded_prompt = ", ".join(expansions + ([analysis_prompt] if analysis_prompt else []))

    detected_styles = set(analysis["style"])
    if re.search(
        r"\b(?:ghost|dragon|fairy|monster|spirit|magic|alien|wizard|demon|unicorn)\b",
        analysis_prompt,
        flags=re.IGNORECASE,
    ):
        terms = ("digital art", "dramatic lighting", "highly detailed", "atmospheric")
    elif "anime" in detected_styles:
        terms = _STYLE_TERMS["anime"]
    elif detected_styles.intersection(("painting", "illustration", "watercolor", "oil painting")):
        terms = _STYLE_TERMS[
            "painting" if "painting" in detected_styles or "oil painting" in detected_styles
            else "illustration"
        ]
    else:
        terms = _STYLE_TERMS["photo"]

    has_lighting_or_time_of_day = re.search(
        r"lighting|\b(?:night|sunset|dark|foggy|moonlight)\b",
        analysis_prompt,
        flags=re.IGNORECASE,
    )
    added_terms = []
    for term in terms[:4]:
        if term == "natural lighting" and has_lighting_or_time_of_day:
            continue
        pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
        if not re.search(pattern, expanded_prompt, flags=re.IGNORECASE):
            added_terms.append(term)

    included_terms = added_terms
    enhanced_prompt = expanded_prompt
    if included_terms:
        separator = ", " if expanded_prompt.strip() else ""
        enhanced_prompt = f"{expanded_prompt}{separator}{', '.join(included_terms)}"

    return enhanced_prompt, NEGATIVE_PROMPT, included_terms, concept_terms, subject


if __name__ == "__main__":
    example_prompt = (
        "A red sports car parked beside a lake, with mountains in the background, "
        "during sunset, cinematic photography"
    )
    enhanced, negative, added, concepts, subject = enhance_prompt(example_prompt)
    print(f"Enhanced: {enhanced}")
    print(f"Negative: {negative}")
    print(f"Added terms: {added}")
    print(f"Concepts: {concepts}")
    print(f"Subject: {subject}")
