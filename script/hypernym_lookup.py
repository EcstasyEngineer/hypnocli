#!/usr/bin/env python3
"""
hypernym_lookup.py
------------------

Prototype for WordNet-based hypernym lookup with property type classification.

This module provides functions to:
1. Look up hypernyms for words using NLTK WordNet
2. Classify words into sensory/experiential property types
3. Map concrete words to abstract sensory qualities

Use cases in the hypnosis generation pipeline:
- Abstract "velvet" → "soft texture" for thematic consistency
- Map "cathedral" → "sacred register" for tone/atmosphere
- Convert "whisper" → "quiet volume" for audio direction

Quickstart:
    from hypernym_lookup import get_word_property, classify_property_type

    result = get_word_property("velvet")
    # Returns: {"word": "velvet", "hypernym": "fabric", "property": "soft", "property_type": "texture"}

Dependencies:
    pip install nltk
    python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Set, Tuple

try:
    from nltk.corpus import wordnet as wn
    from nltk.corpus.reader.wordnet import Synset
except ImportError:
    print("Error: nltk not found. Install with: pip install nltk")
    print("Then run: python -c \"import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')\"")
    raise


# =============================================================================
# Property Type Definitions
# =============================================================================

@dataclass
class PropertyType:
    """Definition of a sensory/experiential property type."""
    name: str
    description: str
    hypernym_markers: Set[str]  # WordNet synset names that indicate this type
    keyword_markers: Set[str]   # Direct word associations
    example_words: List[str]    # Example words that map to this type


PROPERTY_TYPES: Dict[str, PropertyType] = {
    "texture": PropertyType(
        name="texture",
        description="Tactile surface quality",
        hypernym_markers={"fabric.n.01", "material.n.01", "surface.n.01", "cloth.n.01"},
        keyword_markers={"soft", "rough", "smooth", "silky", "velvet", "satin", "leather",
                        "fuzzy", "coarse", "plush", "velvety", "satiny", "cottony"},
        example_words=["velvet", "silk", "sandpaper", "wool", "feather"]
    ),
    "register": PropertyType(
        name="register",
        description="Tonal/atmospheric quality (sacred, profane, formal, intimate)",
        hypernym_markers={"building.n.01", "structure.n.01", "place_of_worship.n.01",
                         "church.n.01", "temple.n.01"},
        keyword_markers={"sacred", "holy", "profane", "formal", "intimate", "cathedral",
                        "temple", "chapel", "sanctuary", "throne", "altar", "shrine"},
        example_words=["cathedral", "temple", "throne", "altar", "sanctuary"]
    ),
    "volume": PropertyType(
        name="volume",
        description="Auditory intensity level",
        hypernym_markers={"sound.n.01", "noise.n.01", "auditory_communication.n.01"},
        keyword_markers={"whisper", "shout", "murmur", "boom", "quiet", "loud", "soft",
                        "thundering", "hushed", "muted", "roaring", "gentle"},
        example_words=["whisper", "shout", "murmur", "thunder", "hush"]
    ),
    "pacing": PropertyType(
        name="pacing",
        description="Temporal rhythm/speed quality",
        hypernym_markers={"motion.n.03", "movement.n.02", "change.n.03"},
        keyword_markers={"slow", "fast", "gradual", "sudden", "steady", "rhythmic",
                        "languid", "rapid", "flowing", "measured", "deliberate", "drift"},
        example_words=["drift", "rush", "crawl", "surge", "pulse"]
    ),
    "temperature": PropertyType(
        name="temperature",
        description="Thermal quality",
        hypernym_markers={"temperature.n.01", "heat.n.01", "coldness.n.01"},
        keyword_markers={"warm", "cold", "hot", "cool", "icy", "burning", "frozen",
                        "tepid", "scorching", "chilly", "frigid", "toasty"},
        example_words=["fire", "ice", "sun", "frost", "ember"]
    ),
    "luminosity": PropertyType(
        name="luminosity",
        description="Light/darkness quality",
        hypernym_markers={"light.n.01", "illumination.n.01", "visible_radiation.n.01"},
        keyword_markers={"bright", "dark", "dim", "glowing", "shadowy", "radiant",
                        "luminous", "murky", "brilliant", "dusky", "gleaming"},
        example_words=["candle", "sun", "shadow", "glow", "twilight"]
    ),
    "weight": PropertyType(
        name="weight",
        description="Heaviness/lightness quality",
        hypernym_markers={"weight.n.01", "mass.n.01", "heaviness.n.01"},
        keyword_markers={"heavy", "light", "weightless", "leaden", "floating", "anchored",
                        "buoyant", "dense", "airy", "substantial"},
        example_words=["feather", "anchor", "stone", "cloud", "lead"]
    ),
    "depth": PropertyType(
        name="depth",
        description="Spatial depth quality (deep/shallow, surface/abyss)",
        hypernym_markers={"body_of_water.n.01", "natural_depression.n.01", "depth.n.01"},
        keyword_markers={"deep", "shallow", "surface", "abyss", "profound", "bottomless",
                        "fathomless", "submerged", "sunken"},
        example_words=["ocean", "well", "abyss", "pool", "chasm"]
    ),
    "enclosure": PropertyType(
        name="enclosure",
        description="Containment/openness quality",
        hypernym_markers={"container.n.01", "enclosure.n.01", "space.n.01"},
        keyword_markers={"enclosed", "open", "contained", "expansive", "confined", "vast",
                        "cozy", "spacious", "intimate", "boundless"},
        example_words=["cocoon", "womb", "cave", "sky", "chamber"]
    ),
    "consciousness": PropertyType(
        name="consciousness",
        description="Mental state quality (alert/dreamy, focused/diffuse)",
        hypernym_markers={"state.n.02", "psychological_state.n.01", "cognitive_state.n.01"},
        keyword_markers={"dreamy", "alert", "focused", "diffuse", "foggy", "clear",
                        "hazy", "sharp", "blurred", "crisp", "trance", "hypnotic"},
        example_words=["dream", "fog", "mist", "clarity", "haze"]
    )
}


# =============================================================================
# Domain-Specific Exclusions
# =============================================================================

# Words that should NOT be abstracted (keep concrete for hypnosis context)
DOMAIN_SPECIFIC_WORDS: Set[str] = {
    # Hypnosis-specific terms
    "trance", "hypnosis", "suggestion", "induction", "deepening", "emergence",
    "trigger", "mantra", "anchor", "conditioning", "compliance",

    # Body parts (important for progressive relaxation)
    "eyes", "mind", "body", "breath", "muscles", "arms", "legs", "shoulders",
    "neck", "face", "jaw", "forehead", "chest", "stomach", "hands", "feet",

    # D/s terminology (context-specific meaning)
    "obey", "submit", "surrender", "serve", "please", "kneel",
    "master", "mistress", "owner", "slave", "pet", "puppet", "doll",

    # Core experience words
    "relax", "calm", "peace", "pleasure", "bliss", "empty", "blank", "focus",
    "deep", "deeper", "down", "drop", "sink", "float", "drift"
}


# =============================================================================
# WordNet Utilities
# =============================================================================

def get_synsets(word: str, pos: Optional[str] = None) -> List[Synset]:
    """
    Get all synsets for a word, optionally filtered by POS.

    Args:
        word: The word to look up
        pos: Part of speech filter (wn.NOUN, wn.VERB, wn.ADJ, wn.ADV)

    Returns:
        List of Synset objects
    """
    if pos:
        return wn.synsets(word, pos=pos)
    return wn.synsets(word)


def get_hypernym_chain(synset: Synset, max_depth: int = 5) -> List[Synset]:
    """
    Get the hypernym chain for a synset (most specific to most general).

    Args:
        synset: The starting synset
        max_depth: Maximum chain length to return

    Returns:
        List of hypernym synsets from immediate parent to root
    """
    chain = []
    current = synset

    for _ in range(max_depth):
        hypernyms = current.hypernyms()
        if not hypernyms:
            break
        # Take the first (most common) hypernym
        current = hypernyms[0]
        chain.append(current)

    return chain


def synset_matches_markers(synset: Synset, markers: Set[str]) -> bool:
    """Check if a synset name matches any of the marker patterns."""
    synset_name = synset.name()
    return synset_name in markers


def get_primary_sense(word: str, context_pos: Optional[str] = None) -> Optional[Synset]:
    """
    Get the most relevant sense for a word in hypnosis context.

    Heuristics:
    1. Prefer noun senses (most concrete/imageable)
    2. Prefer more frequent senses (lower sense number)
    3. Consider adjective senses for quality words

    Args:
        word: The word to analyze
        context_pos: Hint about expected POS

    Returns:
        Most relevant Synset or None
    """
    # Try noun first (most concrete)
    synsets = get_synsets(word, wn.NOUN)
    if synsets:
        return synsets[0]

    # Try adjective (for quality words)
    synsets = get_synsets(word, wn.ADJ)
    if synsets:
        return synsets[0]

    # Try verb
    synsets = get_synsets(word, wn.VERB)
    if synsets:
        return synsets[0]

    # Fall back to any sense
    synsets = get_synsets(word)
    return synsets[0] if synsets else None


# =============================================================================
# Property Type Classification
# =============================================================================

def classify_property_type(word: str) -> Optional[str]:
    """
    Classify a word into a property type category.

    Uses multiple strategies:
    1. Direct keyword matching (highest priority)
    2. WordNet hypernym chain analysis
    3. Gloss (definition) keyword matching

    Args:
        word: The word to classify

    Returns:
        Property type name or None if unclassifiable
    """
    word_lower = word.lower()

    # Strategy 1: Direct keyword match (fast path)
    for prop_type, prop_def in PROPERTY_TYPES.items():
        if word_lower in prop_def.keyword_markers:
            return prop_type

    # Strategy 2: WordNet hypernym analysis
    synset = get_primary_sense(word)
    if synset:
        chain = get_hypernym_chain(synset)

        # Check synset and hypernyms against markers
        for prop_type, prop_def in PROPERTY_TYPES.items():
            # Check the synset itself
            if synset_matches_markers(synset, prop_def.hypernym_markers):
                return prop_type

            # Check hypernym chain
            for hypernym in chain:
                if synset_matches_markers(hypernym, prop_def.hypernym_markers):
                    return prop_type

        # Strategy 3: Gloss keyword matching
        gloss = synset.definition().lower()
        for prop_type, prop_def in PROPERTY_TYPES.items():
            for keyword in prop_def.keyword_markers:
                if keyword in gloss:
                    return prop_type

    return None


def extract_property_from_word(word: str, property_type: str) -> Optional[str]:
    """
    Extract the specific property value for a word given its type.

    For example:
    - "velvet" with type "texture" → "soft"
    - "whisper" with type "volume" → "quiet"

    Args:
        word: The word to analyze
        property_type: The classified property type

    Returns:
        Property value string or None
    """
    word_lower = word.lower()

    # Predefined mappings for common words
    PROPERTY_MAPPINGS: Dict[str, Dict[str, str]] = {
        "texture": {
            "velvet": "soft", "silk": "smooth", "satin": "silky",
            "sandpaper": "rough", "wool": "fuzzy", "feather": "soft",
            "leather": "supple", "cotton": "soft", "fur": "soft"
        },
        "register": {
            "cathedral": "sacred", "temple": "sacred", "church": "sacred",
            "chapel": "sacred", "altar": "sacred", "throne": "regal",
            "sanctuary": "sacred", "shrine": "sacred", "palace": "regal"
        },
        "volume": {
            "whisper": "quiet", "murmur": "quiet", "shout": "loud",
            "thunder": "loud", "boom": "loud", "hush": "quiet",
            "roar": "loud", "sigh": "quiet"
        },
        "pacing": {
            "drift": "slow", "rush": "fast", "crawl": "slow",
            "surge": "fast", "pulse": "rhythmic", "flow": "steady",
            "glide": "smooth"
        },
        "temperature": {
            "fire": "hot", "ice": "cold", "sun": "warm",
            "frost": "cold", "ember": "warm", "snow": "cold",
            "flame": "hot"
        },
        "luminosity": {
            "candle": "dim", "sun": "bright", "shadow": "dark",
            "glow": "soft", "twilight": "dim", "star": "bright",
            "moon": "soft"
        },
        "weight": {
            "feather": "light", "anchor": "heavy", "stone": "heavy",
            "cloud": "light", "lead": "heavy", "balloon": "light"
        },
        "depth": {
            "ocean": "deep", "well": "deep", "abyss": "bottomless",
            "pool": "shallow", "chasm": "deep", "puddle": "shallow"
        },
        "enclosure": {
            "cocoon": "enclosed", "womb": "enclosed", "cave": "enclosed",
            "sky": "open", "chamber": "enclosed", "room": "enclosed"
        },
        "consciousness": {
            "dream": "dreamy", "fog": "hazy", "mist": "hazy",
            "clarity": "clear", "haze": "foggy", "sleep": "unconscious"
        }
    }

    type_mappings = PROPERTY_MAPPINGS.get(property_type, {})
    if word_lower in type_mappings:
        return type_mappings[word_lower]

    # Try to extract from WordNet gloss
    synset = get_primary_sense(word)
    if synset:
        gloss = synset.definition().lower()
        prop_def = PROPERTY_TYPES.get(property_type)
        if prop_def:
            for keyword in prop_def.keyword_markers:
                if keyword in gloss:
                    return keyword

    return None


# =============================================================================
# Main Lookup Function
# =============================================================================

@dataclass
class WordProperty:
    """Result of word property lookup."""
    word: str
    hypernym: Optional[str]
    property_value: Optional[str]
    property_type: Optional[str]
    is_domain_specific: bool
    synset_name: Optional[str]
    confidence: str  # "high", "medium", "low"

    def to_dict(self) -> Dict:
        return {
            "word": self.word,
            "hypernym": self.hypernym,
            "property": self.property_value,
            "property_type": self.property_type,
            "is_domain_specific": self.is_domain_specific,
            "synset": self.synset_name,
            "confidence": self.confidence
        }

    def __str__(self) -> str:
        if self.is_domain_specific:
            return f"{self.word} → [domain-specific, not abstracted]"
        if self.property_type and self.property_value:
            return f"{self.word} → {self.property_value} {self.property_type}"
        if self.hypernym:
            return f"{self.word} → {self.hypernym}"
        return f"{self.word} → [not found]"


def get_word_property(word: str) -> WordProperty:
    """
    Main lookup function: get hypernym and property type for a word.

    Args:
        word: The word to analyze

    Returns:
        WordProperty with all available information
    """
    word_lower = word.lower()

    # Check domain-specific exclusions
    if word_lower in DOMAIN_SPECIFIC_WORDS:
        return WordProperty(
            word=word,
            hypernym=None,
            property_value=None,
            property_type=None,
            is_domain_specific=True,
            synset_name=None,
            confidence="high"
        )

    # Get primary synset
    synset = get_primary_sense(word)

    if not synset:
        return WordProperty(
            word=word,
            hypernym=None,
            property_value=None,
            property_type=None,
            is_domain_specific=False,
            synset_name=None,
            confidence="low"
        )

    # Get immediate hypernym
    hypernyms = synset.hypernyms()
    hypernym_name = hypernyms[0].lemmas()[0].name() if hypernyms else None

    # Classify property type
    property_type = classify_property_type(word)

    # Extract property value
    property_value = None
    confidence = "medium"

    if property_type:
        property_value = extract_property_from_word(word, property_type)
        if property_value:
            confidence = "high"

    return WordProperty(
        word=word,
        hypernym=hypernym_name,
        property_value=property_value,
        property_type=property_type,
        is_domain_specific=False,
        synset_name=synset.name(),
        confidence=confidence
    )


def get_word_properties_batch(words: List[str]) -> List[WordProperty]:
    """
    Batch lookup for multiple words.

    Args:
        words: List of words to analyze

    Returns:
        List of WordProperty results
    """
    return [get_word_property(word) for word in words]


# =============================================================================
# Utility Functions for Generation Pipeline
# =============================================================================

def abstract_to_property(word: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Quick helper for generation pipeline: word → (property_value, property_type)

    Args:
        word: Word to abstract

    Returns:
        Tuple of (property_value, property_type) or (None, None)
    """
    result = get_word_property(word)
    return (result.property_value, result.property_type)


def format_property_string(word: str) -> str:
    """
    Format a word as its property string for use in prompts.

    Examples:
        "velvet" → "soft texture"
        "cathedral" → "sacred register"
        "whisper" → "quiet volume"
        "trance" → "trance"  (domain-specific, unchanged)

    Args:
        word: Word to format

    Returns:
        Property string or original word if not abstractable
    """
    result = get_word_property(word)

    if result.is_domain_specific:
        return word

    if result.property_value and result.property_type:
        return f"{result.property_value} {result.property_type}"

    if result.hypernym:
        return result.hypernym

    return word


def get_words_by_property_type(property_type: str) -> List[str]:
    """
    Get example words for a property type (useful for generation prompts).

    Args:
        property_type: Name of property type

    Returns:
        List of example words
    """
    prop_def = PROPERTY_TYPES.get(property_type)
    if prop_def:
        return prop_def.example_words
    return []


def list_property_types() -> List[str]:
    """Get all available property type names."""
    return list(PROPERTY_TYPES.keys())


# =============================================================================
# CLI / Testing
# =============================================================================

def run_tests():
    """Run test cases to verify functionality."""
    print("=" * 60)
    print("Hypernym Lookup Test Suite")
    print("=" * 60)

    # Test cases with expected results
    test_cases = [
        # (word, expected_property_type, expected_property_value)
        ("velvet", "texture", "soft"),
        ("cathedral", "register", "sacred"),
        ("whisper", "volume", "quiet"),
        ("drift", "pacing", "slow"),
        ("ice", "temperature", "cold"),
        ("candle", "luminosity", "dim"),
        ("feather", "weight", "light"),
        ("ocean", "depth", "deep"),
        ("cocoon", "enclosure", "enclosed"),
        ("fog", "consciousness", "hazy"),
    ]

    print("\n1. Core Word Mappings:")
    print("-" * 40)

    passed = 0
    for word, expected_type, expected_value in test_cases:
        result = get_word_property(word)
        status = "✓" if (result.property_type == expected_type and
                        result.property_value == expected_value) else "✗"
        if status == "✓":
            passed += 1
        print(f"  {status} {word:15} → {str(result)}")
        if status == "✗":
            print(f"      Expected: {expected_value} {expected_type}")

    print(f"\n  Passed: {passed}/{len(test_cases)}")

    # Test domain-specific words
    print("\n2. Domain-Specific Words (should NOT be abstracted):")
    print("-" * 40)

    domain_tests = ["trance", "obey", "eyes", "relax", "drop"]
    for word in domain_tests:
        result = get_word_property(word)
        status = "✓" if result.is_domain_specific else "✗"
        print(f"  {status} {word:15} → {str(result)}")

    # Test words not in WordNet
    print("\n3. Edge Cases (unknown words, multiple senses):")
    print("-" * 40)

    edge_cases = ["xyzzy123", "bank", "light", "soft", "warm"]
    for word in edge_cases:
        result = get_word_property(word)
        print(f"  {word:15} → {str(result)} (conf: {result.confidence})")

    # Test format_property_string helper
    print("\n4. format_property_string() Output:")
    print("-" * 40)

    format_tests = ["velvet", "cathedral", "whisper", "trance", "unknown_word_xyz"]
    for word in format_tests:
        formatted = format_property_string(word)
        print(f"  {word:15} → \"{formatted}\"")

    # List all property types
    print("\n5. Available Property Types:")
    print("-" * 40)

    for prop_type in list_property_types():
        prop_def = PROPERTY_TYPES[prop_type]
        examples = ", ".join(prop_def.example_words[:3])
        print(f"  {prop_type:15} - {prop_def.description[:40]}...")
        print(f"                    Examples: {examples}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # CLI mode: lookup words from arguments
        words = sys.argv[1:]
        for word in words:
            result = get_word_property(word)
            print(f"{word}: {result.to_dict()}")
    else:
        # Run test suite
        run_tests()
