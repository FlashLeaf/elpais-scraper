"""
src/analyzer.py
---------------
WordAnalyzer — counts word frequency across translated article headers
and reports words that appear more than the configured threshold.
"""

import re
from collections import Counter

import config


# Common English words to ignore
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "it", "its",
    "this", "that", "not", "no", "as", "if", "so", "be", "been", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "can",
    "may", "who", "what", "how", "when", "where", "which", "than", "also",
}


class WordAnalyzer:
    """Analyses word frequency in a list of translated headers."""

    def __init__(self, threshold: int = config.REPEAT_THRESHOLD):
        """
        Args:
            threshold: Report words that appear STRICTLY MORE THAN this number.
        """
        self.threshold = threshold

    def analyze(self, headers: list[str]) -> dict[str, int]:
        """Return {word: count} for words appearing > threshold times."""
        counter: Counter = Counter()
        for header in headers:
            tokens = re.split(r"[^a-zA-Z]+", header.lower())
            counter.update(
                t for t in tokens
                if t and len(t) >= 3 and t not in STOP_WORDS
            )
        return {w: c for w, c in counter.items() if c > self.threshold}

    def print_report(self, headers: list[str]) -> None:
        """Print a formatted frequency table to the console."""
        repeated = self.analyze(headers)

        print("\n" + "=" * 55)
        print("  WORD FREQUENCY ANALYSIS (translated headers)")
        print("=" * 55)

        if not repeated:
            print(f"  No words appear more than {self.threshold} time(s).\n")
            return

        sorted_words = sorted(repeated.items(), key=lambda x: (-x[1], x[0]))
        print(f"  Words appearing more than {self.threshold} time(s):\n")
        print(f"  {'WORD':<25} {'COUNT':>5}")
        print(f"  {'-'*25} {'-'*5}")
        for word, count in sorted_words:
            print(f"  {word:<25} {count:>5}")
        print()
