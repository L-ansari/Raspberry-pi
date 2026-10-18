# Stats-to-text on a Raspberry Pi 3

Turns a CSV of numbers into a short written summary, fully offline, using
Qwen2.5-0.5B-Instruct (Q4_K_M) through llama.cpp. Python does the arithmetic;
the model only writes the sentences; the script checks every number made it
into the text.

## Setup (once)

Copy this folder to the Pi, then:

    chmod +x setup.sh
    ./setup.sh

Builds llama.cpp and downloads the ~400 MB model. Expect 20–40 minutes on a Pi 3.
Use 64-bit Raspberry Pi OS Lite. Optionally set GPU memory to 16 MB in
`sudo raspi-config` to free RAM.

## Run

    python3 summarize_stats.py sample.csv
    python3 summarize_stats.py mydata.csv --lang sv -o summary.txt
    python3 summarize_stats.py mydata.csv --show-facts

First run takes ~30–60 s on a Pi 3 (model load + generation).

## CSV format

Header row required. Every numeric column gets average / lowest / highest /
percent change from first to last row. A non-numeric first column (e.g. a date)
is used as the "period". See `sample.csv`.

## Daily report via cron

    crontab -e
    0 7 * * * cd /home/pi/pi3-stats-summary && python3 summarize_stats.py /home/pi/data.csv -o /home/pi/summary.txt

## Tuning

At the top of `summarize_stats.py`:

- `CTX_SIZE` 512 — raise only if you add many more facts (costs RAM)
- `THREADS` 4 — all Pi 3 cores
- `MAX_TOKENS` 100 — about 3–4 sentences
- `TEMPERATURE` 0.2 — keep low so the model sticks to the numbers

To change what gets computed, edit `compute_stats()`; to change the wording
instruction, edit `build_prompt()`.
