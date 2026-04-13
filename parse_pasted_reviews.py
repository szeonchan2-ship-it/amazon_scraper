import argparse
import csv
import re
import sys
from typing import Dict, List


RATING_LINE_RE = re.compile(r"^\s*(\d(?:\.\d)?) out of 5 stars\s+(.+?)\s*$")


def parse_reviews(raw_text: str) -> List[Dict[str, str]]:
    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    reviews: List[Dict[str, str]] = []
    i = 0

    while i < len(lines):
        rating_match = RATING_LINE_RE.match(lines[i])
        if not rating_match:
            i += 1
            continue

        rating = rating_match.group(1).strip()
        title = rating_match.group(2).strip()
        i += 1

        # Skip metadata lines between rating/title and the actual review content.
        while i < len(lines):
            current = lines[i].strip()
            if not current:
                i += 1
                continue
            if current.startswith("Reviewed in "):
                i += 1
                continue
            if "Verified Purchase" in current:
                i += 1
                continue
            break

        content_lines: List[str] = []
        while i < len(lines):
            current_raw = lines[i]
            current = current_raw.strip()

            # Common end markers in Amazon review sections.
            if current in {"Helpful", "Report"}:
                break

            # If the next review starts unexpectedly, stop current review.
            if RATING_LINE_RE.match(current_raw):
                break

            content_lines.append(current_raw.rstrip())
            i += 1

        while content_lines and not content_lines[-1].strip():
            content_lines.pop()

        content = "\n".join(content_lines).strip()
        if title and content:
            reviews.append({"rating": rating, "title": title, "content": content})

        # Skip separators before the next review block.
        while i < len(lines) and lines[i].strip() in {"", "Helpful", "Report"}:
            i += 1

    return reviews


def write_reviews_csv(records: List[Dict[str, str]], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["rating", "title", "content"],
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Amazon review title/content from pasted text."
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Input txt file path. If omitted, reads from stdin.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="parsed_reviews.csv",
        help="Output CSV file path (default: parsed_reviews.csv).",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            raw_text = f.read()
    else:
        raw_text = sys.stdin.read()

    records = parse_reviews(raw_text)
    write_reviews_csv(records, args.output)

    print(f"Parsed {len(records)} reviews -> {args.output}")


if __name__ == "__main__":
    main()
