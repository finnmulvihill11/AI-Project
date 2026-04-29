import re

# ── TTS text sanitiser ────────────────────────────────────────────────────────
#
# Transforms LLM output into clean spoken-language text before it reaches
# ElevenLabs.  Two-layer defence:
#   Layer 1 — system prompt tells Haiku to output plain speech
#   Layer 2 — this function strips anything that slipped through
#
# Order matters: complexity notation must be converted before stripping
# parentheses; bold/italic markers before stripping bare asterisks; etc.


def sanitize_for_tts(text: str) -> str:
    """
    Convert LLM output to clean speech-ready text.

    Handles, in order:
      1. Internal signal tags  ([HINT], [MOVE_ON])
      2. Fenced code blocks    (``` ... ```)
      3. Big-O / complexity    O(n²) → "O of n squared"
      4. Mathematical symbols  ≤ → "less than or equal to", etc.
      5. Exponent notation     n^2 → "n squared"
      6. Markdown formatting   **bold**, *italic*, `code`, # headers, - bullets
      7. Markdown links        [text](url) → text
      8. Leftover brackets     [tag] → stripped
      9. Whitespace            newlines → spaces, double-spaces collapsed
    """

    # 1. Internal signal tags
    for tag in ("[HINT]", "[MOVE_ON]"):
        text = text.replace(tag, "")

    # 2. Fenced code blocks — strip entirely (content is unreadable as speech)
    text = re.sub(r"```[\s\S]*?```", "", text)

    # 3. Big-O / complexity notation
    #    Handles: O(1), O(n), O(n²), O(n^2), O(n^3), O(log n), O(n log n),
    #             O(2^n), O(n!), O(sqrt(n)), O(n*m), Θ(...), Ω(...)
    text = re.sub(r"\bO\(([^)]+)\)",  lambda m: _complexity("O",     m.group(1)), text)
    text = re.sub(r"\bΘ\(([^)]+)\)",  lambda m: _complexity("theta", m.group(1)), text)
    text = re.sub(r"\bΩ\(([^)]+)\)",  lambda m: _complexity("omega", m.group(1)), text)

    # 4. Mathematical / comparison symbols
    _symbol_map = [
        # multi-char first to avoid partial matches
        (">=",  " greater than or equal to "),
        ("<=",  " less than or equal to "),
        ("!=",  " not equal to "),
        ("->",  " "),
        ("<-",  " "),
        ("=>",  " "),
        ("≥",   " greater than or equal to "),
        ("≤",   " less than or equal to "),
        ("≠",   " not equal to "),
        ("→",   " "),
        ("←",   " "),
        ("⇒",   " "),
        ("∞",   " infinity "),
        ("√",   " square root of "),
        ("π",   " pi "),
        ("∑",   " sum of "),
        ("∏",   " product of "),
        ("∈",   " in "),
        ("∉",   " not in "),
        ("∩",   " intersect "),
        ("∪",   " union "),
        ("×",   " times "),
        ("÷",   " divided by "),
        ("²",   " squared"),
        ("³",   " cubed"),
        ("°",   " degrees "),
        ("±",   " plus or minus "),
    ]
    for sym, spoken in _symbol_map:
        text = text.replace(sym, spoken)

    # 5. Remaining exponent notation (outside O() which is already handled)
    #    n^2 → "n squared", n^3 → "n cubed", n^k → "n to the k"
    text = re.sub(r"(\w)\^2\b",       r"\1 squared",      text)
    text = re.sub(r"(\w)\^3\b",       r"\1 cubed",        text)
    text = re.sub(r"(\w)\^(\w+)",     r"\1 to the \2",    text)

    # 6. Markdown formatting
    # Bold+italic (***) before bold (**) before italic (*)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\*\*(.+?)\*\*",     r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__",          r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*",          r"\1", text)
    text = re.sub(r"_(.+?)_",            r"\1", text)

    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Headers (# Foo → Foo)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Bullet/numbered lists — strip the marker, keep the text
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)

    # Block quotes
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r"^[-=_]{3,}$", "", text, flags=re.MULTILINE)

    # 7. Markdown links — keep display text
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)

    # 8. Leftover square-bracket tags (e.g. residual [HINT] variants)
    text = re.sub(r"\[[^\]]*\]", "", text)

    # 9. Whitespace — convert to linear speech
    text = re.sub(r"\n+",   " ", text)   # newlines → space
    text = re.sub(r"\s{2,}", " ", text)  # collapse runs
    text = text.strip()

    return text


# ── Internal helpers ──────────────────────────────────────────────────────────

def _complexity(prefix: str, inner: str) -> str:
    """Convert the contents of O(...) / Θ(...) / Ω(...) to spoken form."""
    s = inner.strip()

    # Unicode superscripts first
    s = s.replace("²", "^2").replace("³", "^3")

    # sqrt(x) → "root x"
    s = re.sub(r"sqrt\(([^)]+)\)", r"root \1", s)

    # n! → "n factorial"
    s = re.sub(r"(\w)!", r"\1 factorial", s)

    # Exponents
    s = re.sub(r"\^2\b",     " squared",        s)
    s = re.sub(r"\^3\b",     " cubed",          s)
    s = re.sub(r"\^(\w+)",   r" to the \1",     s)

    # Multiplication: n*m → "n times m"
    s = re.sub(r"(\w)\s*\*\s*(\w)", r"\1 times \2", s)

    # Collapse extra spaces
    s = re.sub(r"\s{2,}", " ", s).strip()

    return f"{prefix} of {s}"
