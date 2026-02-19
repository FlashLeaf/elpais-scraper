"""
analyzer.py
-----------
Analyses a list of translated (English) article headers and reports
any word that appears more than twice across all headers combined.
"""

import re
from collections import Counter
from typing import List, Dict

# Common English stop-words to exclude from the frequency count
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "it", "its", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "my", "your",
    "his", "her", "our", "their", "as", "not", "no", "so", "if", "than",
    "then", "about", "into", "up", "out", "more", "also", "just", "can",
    "which", "who", "what", "how", "when", "where", "why",
}

MIN_WORD_LENGTH = 3


def tokenize(text: str) -> List[str]:
    """Lower-case and split on any non-alphabetic character."""
    raw_tokens = re.split(r"[^a-zA-Z]+", text.lower())
    return [
        t for t in raw_tokens
        if t and len(t) >= MIN_WORD_LENGTH and t not in STOP_WORDS
    ]


def count_words(headers: List[str]) -> Dict[str, int]:
    """Return frequency map of all words across all headers."""
    counter: Counter = Counter()
    for header in headers:
        counter.update(tokenize(header))
    return dict(counter)


def find_repeated_words(headers: List[str], threshold: int = 2) -> Dict[str, int]:
    """
    Return a dict of {word: count} for words that appear MORE THAN
    *threshold* times across all headers combined.
    """
    freq = count_words(headers)
    return {word: cnt for word, cnt in freq.items() if cnt > threshold}


def print_analysis(headers: List[str], threshold: int = 2) -> None:
    """Pretty-print the word-frequency analysis."""
    print("\n" + "=" * 60)
    print("  WORD FREQUENCY ANALYSIS (translated headers)")
    print("=" * 60)

    repeated = find_repeated_words(headers, threshold)

    if not repeated:
        print(f"  No words appear more than {threshold} times.\n")
        return

    # Sort by count descending, then alphabetically
    sorted_words = sorted(repeated.items(), key=lambda x: (-x[1], x[0]))
    print(f"  Words appearing more than {threshold} time(s):\n")
    print(f"  {'WORD':<25} {'COUNT':>5}")
    print(f"  {'-'*25} {'-'*5}")
    for word, cnt in sorted_words:
        print(f"  {word:<25} {cnt:>5}")
    print()


if __name__ == "__main__":
    # Quick self-test
    test_headers = [
        "Political crisis in Europe and the political fallout",
        "The future of artificial intelligence and democracy",
        "Democracy under pressure in Europe",
        "Europe and the future of political reform",
        "Artificial intelligence reshapes democracy and political systems",
    ]
    print("Headers under test:")
    for h in test_headers:
        print(f"  • {h}")
    print_analysis(test_headers, threshold=2)
