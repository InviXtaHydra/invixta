"""Cleaning and chunking of extracted PDF text. Pure functions, so they're easy to unit test.

Pipeline per page:  raw text → clean_lines → split_sections → chunk_sections
Each chunk keeps the heading of the section it comes from ("Refunds: We refund …"), so a chunk
taken out of context still says what it is about — that makes retrieval noticeably more precise.
"""

import re
from dataclasses import dataclass

DEFAULT_MAX_CHARS = 800
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_PAGE_NUMBER = re.compile(r"(page\s+)?\d+(\s+of\s+\d+)?", re.IGNORECASE)
_LIST_ITEM = re.compile(r"^([-•*]|\d+[.)])\s")


@dataclass
class Section:
    heading: str | None
    paragraphs: list[str]


def clean_lines(text: str) -> list[str]:
    """Normalise raw page text into stripped lines.

    - joins words hyphenated across line breaks ("deliv-\\nery" → "delivery")
    - drops lines that are only a page number ("3", "Page 3 of 5")
    - collapses repeated whitespace; keeps blank lines as paragraph breaks ("")
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return [line for line in lines if not _PAGE_NUMBER.fullmatch(line)]


def is_heading(line: str, previous: str | None) -> bool:
    """A short line that starts with a capital, doesn't end like a sentence fragment, and follows
    the end of a sentence (or the top of the page). FAQ questions ("…?") count as headings."""
    if not line or len(line) > 90 or _LIST_ITEM.match(line):
        return False
    if not line[0].isupper() or line[-1] in ".,;:":
        return False
    if line.endswith("?"):
        return True
    return len(line) <= 70 and (previous is None or previous == "" or previous[-1] in ".!?")


def split_sections(lines: list[str]) -> list[Section]:
    """Group lines into sections (heading + paragraphs). Wrapped lines are joined back together."""
    sections: list[Section] = [Section(heading=None, paragraphs=[])]
    current: list[str] = []
    previous: str | None = None

    def flush() -> None:
        if current:
            sections[-1].paragraphs.append(" ".join(current))
            current.clear()

    for line in lines:
        if not line:
            flush()
        elif is_heading(line, previous):
            flush()
            sections.append(Section(heading=line, paragraphs=[]))
        else:
            if _LIST_ITEM.match(line):
                flush()  # each list item becomes its own paragraph
            current.append(line)
        previous = line
    flush()
    return [s for s in sections if s.paragraphs or s.heading]


def split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(paragraph) if s.strip()]


def chunk_sections(sections: list[Section], max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Turn sections into chunks of at most ~max_chars, built from whole sentences.

    A new section always starts a new chunk. A long section is split into several chunks; each
    repeats the section heading and starts with the last sentence of the previous chunk (overlap),
    so a fact that spans the boundary is still found.
    A heading without text (e.g. the document title) is carried over to the next section.
    """
    chunks: list[str] = []
    carry: str | None = None
    for section in sections:
        heading = " — ".join(h for h in (carry, section.heading) if h) or None
        sentences = [s for p in section.paragraphs for s in split_sentences(p)]
        if not sentences:
            carry = heading
            continue
        carry = None
        prefix = "" if not heading else f"{heading} " if heading.endswith("?") else f"{heading}: "
        current: list[str] = []
        has_new = False  # whether `current` holds anything beyond the overlap sentence
        for sentence in sentences:
            for piece in _split_long(sentence, max_chars - len(prefix)) if len(prefix) + len(sentence) > max_chars else [sentence]:
                if has_new and len(prefix) + len(" ".join([*current, piece])) > max_chars:
                    chunks.append(prefix + " ".join(current))
                    overlap = current[-1]
                    current = [overlap] if len(overlap) < max_chars // 3 else []
                    has_new = False
                current.append(piece)
                has_new = True
        if has_new:
            chunks.append(prefix + " ".join(current))
    if carry and not chunks:  # a page with only a heading
        chunks.append(carry)
    return chunks


def chunk_page(raw_text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Convenience: the full pipeline for one page of extracted text."""
    return chunk_sections(split_sections(clean_lines(raw_text)), max_chars)


def _split_long(sentence: str, max_chars: int) -> list[str]:
    words, pieces, current = sentence.split(), [], ""
    for word in words:
        if current and len(current) + len(word) + 1 > max_chars:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces
