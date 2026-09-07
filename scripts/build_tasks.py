#!/usr/bin/env python3
"""Turn the canonical GPQA-Diamond CSV into 198 Harbor tasks.

The task format, the deterministic choice shuffle, the instruction text and the
verifier all come from Harbor's own `adapters/gpqa-diamond` — this script only
(1) fetches the gated CSV, (2) validates it, and (3) hands the rows to Harbor's
adapter. Nothing about the benchmark itself is reimplemented here.

Usage:
    HF_TOKEN=hf_... python3 scripts/build_tasks.py
    python3 scripts/build_tasks.py --csv /path/to/gpqa_diamond.csv
"""

import argparse
import csv
import importlib.util
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_URL = "https://huggingface.co/datasets/Idavidrein/gpqa/resolve/main/gpqa_diamond.csv"
EXPECTED_ROWS = 198

# Column names Harbor's GPQAAdapter reads off each record.
REQUIRED_COLUMNS = [
    "Question",
    "Correct Answer",
    "Incorrect Answer 1",
    "Incorrect Answer 2",
    "Incorrect Answer 3",
]


def download_csv(dest: Path) -> Path:
    """Fetch the gated GPQA-Diamond CSV from Hugging Face into `dest`."""
    if dest.exists():
        print(f"Using cached CSV: {dest}")
        return dest

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit(
            "HF_TOKEN is not set. GPQA is gated: accept the terms at\n"
            "  https://huggingface.co/datasets/Idavidrein/gpqa\n"
            "then export a token with read access (or pass --csv)."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        CSV_URL, headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request) as response:
        dest.write_bytes(response.read())
    print(f"Downloaded {dest} ({dest.stat().st_size} bytes)")
    return dest


def load_and_validate(csv_path: Path) -> list[dict]:
    """Read the CSV and assert it is the canonical 198-question Diamond set.

    Row order matters: Harbor's adapter derives both the task id and the
    per-question shuffle seed from the row index, so a reordered file would
    produce a different (still valid, but non-comparable) task set.
    """
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    missing = [c for c in REQUIRED_COLUMNS if c not in (rows[0] if rows else {})]
    if missing:
        sys.exit(f"CSV is missing expected GPQA columns: {missing}")

    problems = []
    if len(rows) != EXPECTED_ROWS:
        problems.append(f"expected {EXPECTED_ROWS} questions, found {len(rows)}")

    questions = [r["Question"].strip() for r in rows]
    duplicates = len(questions) - len(set(questions))
    if duplicates:
        problems.append(f"{duplicates} duplicate question(s)")

    for index, row in enumerate(rows):
        choices = [row[c].strip() for c in REQUIRED_COLUMNS[1:]]
        if not all(choices):
            problems.append(f"row {index}: blank answer choice")
        elif len(set(choices)) != 4:
            problems.append(f"row {index}: answer choices are not 4 distinct strings")

    if problems:
        sys.exit("Dataset validation failed:\n  - " + "\n  - ".join(problems))

    print(f"Validated {len(rows)} questions, 4 distinct choices each, no duplicates.")
    return rows


def load_harbor_adapter(harbor_root: Path):
    """Import GPQAAdapter straight from the pinned Harbor checkout."""
    adapter_py = harbor_root / "adapters" / "gpqa-diamond" / "adapter.py"
    if not adapter_py.exists():
        sys.exit(f"Harbor adapter not found at {adapter_py}. Run scripts/setup.sh.")

    spec = importlib.util.spec_from_file_location("gpqa_adapter", adapter_py)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GPQAAdapter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=REPO_ROOT / ".cache" / "gpqa_diamond.csv",
        help="Local CSV path (downloaded from Hugging Face if absent).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "datasets" / "gpqa-diamond",
        help="Where to write the generated Harbor tasks.",
    )
    parser.add_argument(
        "--harbor-root",
        type=Path,
        default=Path(os.environ.get("HARBOR_ROOT", REPO_ROOT / "harbor")),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Choice-shuffle seed. 42 is the Harbor adapter default; changing "
        "it produces a different task set and a different experiment.",
    )
    args = parser.parse_args()

    rows = load_and_validate(download_csv(args.csv))
    adapter_cls = load_harbor_adapter(args.harbor_root)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = adapter_cls(task_dir=args.output_dir, dataset=rows, seed=args.seed)
    adapter.generate_all_tasks()

    # Ground-truth letters are spread over A-D by the shuffle; a wildly skewed
    # distribution would mean the shuffle silently failed.
    letters = sorted(t.correct_letter for t in adapter.tasks)
    counts = {letter: letters.count(letter) for letter in "ABCD"}
    print(f"Generated {len(adapter.tasks)} tasks in {args.output_dir}")
    print(f"Ground-truth letter distribution: {counts}")


if __name__ == "__main__":
    main()
