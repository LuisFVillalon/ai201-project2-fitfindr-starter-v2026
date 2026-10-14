"""
Scores the Milestone 5 improvement: does every suggest_outfit result follow one
fixed format?

    python check_outfit_format.py results/run_..._before.md

A suggestion passes when every non-blank line starts with "Outfit N:",
"Pieces:" or "Why:", the first line is "Outfit 1:", and there are the same
number (1 to 3) of each.
"""

import re
import sys
from pathlib import Path


def follows_format(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not re.match(r"^Outfit 1:", lines[0]):
        return False
    outfits = sum(bool(re.match(r"^Outfit \d+:", line)) for line in lines)
    pieces = sum(line.startswith("Pieces:") for line in lines)
    whys = sum(line.startswith("Why:") for line in lines)
    if outfits + pieces + whys != len(lines):
        return False
    return 1 <= outfits <= 3 and outfits == pieces == whys


def main(path: str) -> None:
    text = Path(path).read_text(encoding="utf-8")
    total = passed = 0
    for section in re.split(r"(?m)^### ", text)[1:]:
        name = section.splitlines()[0].strip()
        results = [
            follows_format(m.group(1))
            for m in re.finditer(r"(?s)Outfit suggestion:\s*```\s*(.*?)\s*```", section)
        ]
        if not results:
            continue
        marks = " ".join("PASS" if r else "FAIL" for r in results)
        print(f"{name}: {sum(results)}/{len(results)}  [{marks}]")
        total += len(results)
        passed += sum(results)
    print(f"\nTotal: {passed}/{total} suggestions follow the format")


if __name__ == "__main__":
    main(sys.argv[1])
