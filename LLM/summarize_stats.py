#!/usr/bin/env python3
"""
Summarize simple statistics from a CSV as a short paragraph, using a local
Qwen2.5-0.5B model via llama.cpp. Designed for a Raspberry Pi 3 (1 GB RAM).

Usage:
    python3 summarize_stats.py data.csv            # print the summary
    python3 summarize_stats.py data.csv -o out.txt # also write it to a file
    python3 summarize_stats.py data.csv --lang sv  # write in Swedish

The CSV needs a header row. Every numeric column is summarized; the first
column is treated as a label/date column if it is not numeric.

Python does ALL the arithmetic. The model only turns finished numbers into
sentences, and the script verifies that every number it was given actually
appears in the text (regenerating once if not).
"""

import argparse
import csv
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = HERE / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
LLAMA_DIR = HERE / "llama.cpp" / "build" / "bin"

# Generation settings tuned for a Pi 3: small context, few threads, low temperature.
CTX_SIZE = 512
THREADS = 4
MAX_TOKENS = 100
TEMPERATURE = 0.2


# ---------------------------------------------------------------- statistics

def fmt(x: float) -> str:
    """Format a number the way we want it to appear in both prompt and output."""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.1f}"


def compute_stats(csv_path: Path) -> list[tuple[str, str]]:
    """Return a list of (label, value-as-string) pairs, e.g. ('Average temperature', '13.3')."""
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("CSV is empty")

    columns = list(rows[0].keys())
    facts: list[tuple[str, str]] = [("Number of records", str(len(rows)))]

    # Mention the period if the first column looks like a label/date.
    first = columns[0]
    try:
        float(rows[0][first])
    except ValueError:
        facts.append(("Period", f"{rows[0][first]} to {rows[-1][first]}"))

    for col in columns:
        values = []
        for r in rows:
            try:
                values.append(float(r[col]))
            except (ValueError, TypeError):
                break
        else:
            if not values:
                continue
            facts.append((f"Average {col}", fmt(statistics.fmean(values))))
            facts.append((f"Lowest {col}", fmt(min(values))))
            facts.append((f"Highest {col}", fmt(max(values))))
            if len(values) >= 2 and values[0] != 0:
                change = (values[-1] - values[0]) / abs(values[0]) * 100
                sign = "+" if change >= 0 else ""
                facts.append((f"Change in {col} from first to last record", f"{sign}{fmt(change)}%"))
    return facts


# -------------------------------------------------------------------- prompt

def build_prompt(facts: list[tuple[str, str]], lang: str) -> str:
    lines = "\n".join(f"{k}: {v}" for k, v in facts)
    if lang == "sv":
        instruction = (
            "Skriv 3-4 meningar på svenska som sammanfattar statistiken nedan för en "
            "icke-teknisk läsare. Använd varje siffra exakt som den står. Hitta inte på "
            "några siffror som inte finns i listan. Skriv bara sammanfattningen."
        )
    else:
        instruction = (
            "Write 3-4 sentences summarizing the statistics below for a non-technical "
            "reader. Use every number exactly as given. Do not invent numbers that are "
            "not in the list. Output only the summary."
        )
    # Qwen2.5 chat template (ChatML)
    return (
        "<|im_start|>system\nYou are a concise assistant that writes short, accurate "
        "summaries of data.<|im_end|>\n"
        f"<|im_start|>user\n{instruction}\n\n{lines}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


# ------------------------------------------------------------------ llama.cpp

def find_binary() -> list[str]:
    """Return the command prefix for a one-shot completion with llama.cpp."""
    for name in ("llama-completion", "llama-cli"):
        path = LLAMA_DIR / name
        if path.exists():
            cmd = [str(path)]
        elif shutil.which(name):
            cmd = [name]
        else:
            continue
        if name == "llama-cli":
            cmd.append("-no-cnv")  # older llama-cli: disable interactive chat mode
        return cmd
    sys.exit(f"No llama.cpp binary found in {LLAMA_DIR}. Run setup.sh first.")


def generate(prompt: str, seed: int) -> str:
    cmd = find_binary() + [
        "-m", str(MODEL),
        "-p", prompt,
        "-n", str(MAX_TOKENS),
        "-c", str(CTX_SIZE),
        "-t", str(THREADS),
        "--temp", str(TEMPERATURE),
        "--seed", str(seed),
        "--no-display-prompt",
        "--log-disable",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        sys.exit(f"llama.cpp failed:\n{result.stderr[-2000:]}")
    text = result.stdout
    # Strip any trailing end-of-turn marker and whitespace.
    text = text.split("<|im_end|>")[0]
    return " ".join(text.split())


# --------------------------------------------------------------- verification

def missing_numbers(facts: list[tuple[str, str]], text: str) -> list[str]:
    """Numbers from the facts that do not appear in the generated text."""
    wanted = set()
    for _, value in facts:
        # Only check plain numeric facts (e.g. "13.3", "+5.6%"), not dates/labels,
        # since the model may legitimately rephrase "2026-10-01" as "1 October".
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?%?", value):
            continue
        for num in re.findall(r"-?\d+(?:\.\d+)?", value):
            wanted.add(num.lstrip("-"))
    present = {n.lstrip("-") for n in re.findall(r"-?\d+(?:[.,]\d+)?", text.replace(",", "."))}
    return sorted(n for n in wanted if n not in present)


# ----------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="write the summary to this file")
    ap.add_argument("--lang", choices=["en", "sv"], default="en")
    ap.add_argument("--show-facts", action="store_true", help="print the computed statistics too")
    args = ap.parse_args()

    if not MODEL.exists():
        sys.exit(f"Model not found at {MODEL}. Run setup.sh first.")

    facts = compute_stats(args.csv)
    if args.show_facts:
        for k, v in facts:
            print(f"  {k}: {v}")
        print()

    prompt = build_prompt(facts, args.lang)

    best_text, best_missing = "", None
    for attempt, seed in enumerate((42, 7), start=1):
        text = generate(prompt, seed)
        missing = missing_numbers(facts, text)
        if best_missing is None or len(missing) < len(best_missing):
            best_text, best_missing = text, missing
        if not missing:
            break
        print(f"[attempt {attempt}] numbers missing from summary: {', '.join(missing)} - retrying",
              file=sys.stderr)

    print(best_text)
    if best_missing:
        print(f"\nWARNING: these numbers never appeared in the text: {', '.join(best_missing)}",
              file=sys.stderr)

    if args.output:
        args.output.write_text(best_text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
