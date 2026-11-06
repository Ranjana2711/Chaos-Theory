import re


_OBJECTS = (
    "sports car",
    "traffic light",
    "fire hydrant",
    "dining table",
    "potted plant",
    "teddy bear",
    "tennis racket",
    "mountain",
    "mountains",
    "lake",
    "ocean",
    "river",
    "waterfall",
    "forest",
    "tree",
    "flower",
    "house",
    "building",
    "bridge",
    "road",
    "street",
    "car",
    "truck",
    "bicycle",
    "motorcycle",
    "bus",
    "train",
    "airplane",
    "boat",
    "person",
    "people",
    "man",
    "woman",
    "child",
    "dog",
    "cat",
    "bird",
    "horse",
    "table",
    "chair",
    "sofa",
    "lamp",
    "book",
    "cup",
    "bowl",
    "plate",
    "apple",
    "banana",
    "ball",
    "cube",
    "sphere",
    "cloud",
    "sun",
    "moon",
)

_ATTRIBUTES = {
    "colours": (
        "red",
        "orange",
        "yellow",
        "green",
        "blue",
        "purple",
        "pink",
        "brown",
        "black",
        "white",
        "gray",
        "grey",
        "gold",
        "silver",
    ),
    "sizes": (
        "tiny",
        "small",
        "little",
        "medium",
        "large",
        "big",
        "huge",
        "giant",
        "tall",
        "short",
    ),
    "materials": (
        "wood",
        "wooden",
        "metal",
        "metallic",
        "glass",
        "plastic",
        "stone",
        "marble",
        "leather",
        "paper",
        "fabric",
        "cotton",
        "ceramic",
    ),
}

_RELATIONSHIPS = (
    "in front of",
    "in the background",
    "to the left of",
    "to the right of",
    "left of",
    "right of",
    "next to",
    "beside",
    "above",
    "behind",
    "under",
    "on",
)

_LIGHTING = (
    "sunset",
    "sunrise",
    "golden hour",
    "daylight",
    "daytime",
    "sunny",
    "overcast",
    "cloudy",
    "night",
    "nighttime",
    "moonlight",
    "dusk",
    "dawn",
    "dim",
    "soft light",
    "dramatic lighting",
    "studio lighting",
    "backlit",
)

_STYLES = (
    "photography",
    "photograph",
    "photo",
    "photorealistic",
    "realistic",
    "cinematic",
    "painting",
    "oil painting",
    "watercolor",
    "illustration",
    "anime",
    "cartoon",
    "sketch",
    "3d render",
    "pixel art",
    "surreal",
    "vintage",
)

_COUNTS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _find_terms(text, terms):
    return [term for _, _, term in _find_matches(text, terms)]


def _find_matches(text, terms):
    matches = []
    occupied = []
    for term in sorted(terms, key=len, reverse=True):
        pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(text):
            if any(match.start() < end and match.end() > start for start, end in occupied):
                continue
            matches.append((match.start(), match.end(), match.group(0).lower()))
            occupied.append((match.start(), match.end()))
    return sorted(matches)


def _find_relationship_phrases(text):
    relations = []
    relation_pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(
            re.escape(term) for term in sorted(_RELATIONSHIPS, key=len, reverse=True)
        ) + r")(?!\w)",
        re.IGNORECASE,
    )
    object_spans = [(start, end) for start, end, _ in _find_matches(text, _OBJECTS)]

    for relation in relation_pattern.finditer(text):
        preceding = [span for span in object_spans if span[1] <= relation.start()]
        following = [span for span in object_spans if span[0] >= relation.end()]
        start = preceding[-1][0] if preceding else relation.start()
        end = following[0][1] if following else relation.end()
        phrase = text[start:end].strip(" ,.;:").lower()
        relations.append(phrase)

    return list(dict.fromkeys(relations))


def analyze_prompt(prompt):
    """Extract basic visual concepts and a normalized prompt-complexity score."""
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")

    text = prompt.lower()
    objects = _find_terms(text, _OBJECTS)
    attributes = {
        category: _find_terms(text, terms)
        for category, terms in _ATTRIBUTES.items()
    }

    counts = []
    count_pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(
            [re.escape(word) for word in _COUNTS]
            + [r"\d+"]
        ) + r")(?!\w)",
        re.IGNORECASE,
    )
    for match in count_pattern.finditer(text):
        value_text = match.group(0).lower()
        counts.append(
            {
                "text": value_text,
                "value": _COUNTS.get(value_text, int(value_text) if value_text.isdigit() else 0),
            }
        )

    relationships = _find_relationship_phrases(text)
    lighting = _find_terms(text, _LIGHTING)
    style = _find_terms(text, _STYLES)
    complexity_score = min(
        1.0,
        (len(objects) + 2 * len(relationships) + len(counts)) / 10.0,
    )

    return {
        "objects": objects,
        "attributes": attributes,
        "relationships": relationships,
        "lighting": lighting,
        "style": style,
        "counts": counts,
        "complexity_score": complexity_score,
    }


if __name__ == "__main__":
    example = (
        "A red sports car parked beside a lake, with mountains in the background, "
        "during sunset, cinematic photography"
    )
    print(analyze_prompt(example))
