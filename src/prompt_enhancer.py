import re

from src.prompt_analyzer import analyze_prompt


NEGATIVE_PROMPT = (
    "blurry, distorted, low quality, deformed, extra limbs, watermark, text, "
    "jpeg artifacts"
)

ANIMALS = [
    "cat", "dog", "kitten", "puppy", "rabbit", "bird", "horse",
    "fox", "bear", "owl", "panda", "tiger", "lion",
]
_ANIMAL_NEGATIVE_TERMS = (
    "human, person, girl, woman, man, humanoid, anthropomorphic, cat ears, "
    "animal ears, anime"
)

CONCEPT_MAP = {
    "apple tree": "with ripe red apples hanging from the branches",
    "orange tree": "with ripe oranges on the branches",
    "lemon tree": "with bright yellow lemons on the branches",
    "mango tree": "with ripe mangoes on the branches",
    "cherry tree": "with red cherries on the branches",
    "fruit tree": "with ripe fruit on the branches",
    "coconut tree": "tall palm with coconuts",
    "sunflower": "with large yellow petals and a dark center",
    "cactus": "green spiny cactus",
    "bonsai": "miniature tree in a shallow pot",
    "rose": "red rose with layered petals",
    "birthday cake": "with lit candles",
    "pizza": "with melted cheese and toppings",
    "burger": "with a sesame bun, lettuce and cheese",
    "ice cream": "scoops of ice cream in a cone",
    "coffee": "a cup of coffee with steam rising",
    "sushi": "sushi rolls on a wooden plate",
    "biryani": "rice dish with spices served in a bowl",
    "dosa": "thin crispy golden crepe with chutney",
    "beach": "with sand and ocean waves",
    "waterfall": "water cascading down rocks",
    "volcano": "erupting with glowing lava",
    "desert": "sand dunes under a clear sky",
    "snowy mountain": "mountain peaks covered in snow",
    "city at night": "skyline with glowing lit windows",
    "library": "tall shelves full of books",
    "rainforest": "dense green jungle with mist",
    "clock": "with a clear clock face and hands",
    "bicycle": "with two wheels and handlebars",
    "guitar": "acoustic guitar with six strings",
    "umbrella": "open umbrella",
    "lighthouse": "tall striped lighthouse with a glowing lamp",
    "hot air balloon": "colorful hot air balloon floating in the sky",
    "rainbow": "colorful rainbow arc across the sky",
    "candle": "lit candle with a small flame",
    "christmas tree": "decorated with lights and ornaments",
    "jack-o-lantern": "carved pumpkin glowing from inside",
    "diwali": "glowing oil lamps and colorful rangoli",
    "chef": "chef in a white uniform and tall white hat",
    "astronaut": "astronaut in a white spacesuit with helmet",
    "firefighter": "firefighter in a yellow protective suit and helmet",
    "doctor": "doctor in a white coat with a stethoscope",
    "rainy": "rain falling, wet reflective ground",
    "snowing": "snowflakes falling",
    "sunset": "orange and pink sky with the sun near the horizon",
    "night sky": "dark sky full of stars",
    "ghost": "translucent glowing white ghostly figure, spectral apparition",
    "spirit": "glowing ethereal figure",
    "listening to music": "wearing large over-ear headphones, musical notes in the air",
    "music": "wearing large over-ear headphones, musical notes in the air",
    "headphones": "large over-ear headphones clearly visible on the head",
    "dragon": "large scaly dragon with wings",
    "angel": "figure with large white feathered wings and halo",
    "robot": "metallic humanoid robot",
}
_FEATURE_CONCEPTS = frozenset((
    "apple tree",
    "orange tree",
    "lemon tree",
    "mango tree",
    "cherry tree",
    "fruit tree",
    "coconut tree",
    "sunflower",
    "cactus",
    "bonsai",
    "rose",
    "birthday cake",
    "pizza",
    "burger",
    "ice cream",
    "coffee",
    "sushi",
    "biryani",
    "dosa",
    "beach",
    "waterfall",
    "volcano",
    "desert",
    "snowy mountain",
    "city at night",
    "library",
    "rainforest",
    "clock",
    "bicycle",
    "guitar",
    "umbrella",
    "lighthouse",
    "hot air balloon",
    "rainbow",
    "candle",
    "christmas tree",
    "jack-o-lantern",
    "diwali",
    "chef",
    "astronaut",
    "firefighter",
    "doctor",
    "rainy",
    "snowing",
    "sunset",
    "night sky",
))

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
    noun_terms = set(analysis["objects"]) | set(CONCEPT_MAP) | set(ANIMALS)
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
    animal = next(
        (
            candidate
            for candidate in ANIMALS
            if re.search(
                r"(?<!\w)" + re.escape(candidate) + r"(?!\w)",
                subject,
                flags=re.IGNORECASE,
            )
        ),
        None,
    )

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
    expansions = [
        CONCEPT_MAP[concept]
        for concept in concept_terms
        if concept not in _FEATURE_CONCEPTS
    ]
    if expansions and subject:
        insertion_point = len(subject)
        expanded_prompt = (
            f"{analysis_prompt[:insertion_point]}, {', '.join(expansions)}"
            f"{analysis_prompt[insertion_point:]}"
        )
    elif expansions:
        expanded_prompt = ", ".join(expansions + ([analysis_prompt] if analysis_prompt else []))

    for concept in sorted(_FEATURE_CONCEPTS, key=len, reverse=True):
        feature = CONCEPT_MAP[concept]
        if re.search(re.escape(feature), analysis_prompt, flags=re.IGNORECASE):
            continue
        pattern = re.compile(
            r"(?<!\w)" + re.escape(concept) + r"(?!\w)",
            flags=re.IGNORECASE,
        )
        expanded_prompt = pattern.sub(
            lambda match: f"{match.group(0)}, {feature}",
            expanded_prompt,
        )

    if animal:
        expanded_prompt = f"a real {animal}, animal photograph, {expanded_prompt}"

    detected_styles = set(analysis["style"])
    if animal:
        terms = _STYLE_TERMS["photo"]
    elif re.search(
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

    negative_prompt = NEGATIVE_PROMPT
    if animal:
        negative_prompt = f"{negative_prompt}, {_ANIMAL_NEGATIVE_TERMS}"

    return enhanced_prompt, negative_prompt, included_terms, concept_terms, subject


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
