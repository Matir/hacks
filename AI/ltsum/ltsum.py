#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
# ]
# ///
"""Run a common prompt over every HTML file in a directory as a Gemini batch job."""

import argparse
import json
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_POLL_INTERVAL = 30.0
TERMINAL_STATES = {
    "JOB_STATE_SUCCEEDED",
    "JOB_STATE_FAILED",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_EXPIRED",
    "JOB_STATE_PARTIALLY_SUCCEEDED",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply a common prompt to every HTML file in a directory via the "
            "Gemini API batch mode, and write the results to a JSONL file."
        )
    )
    parser.add_argument("directory", type=Path, help="Directory containing HTML files")

    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Prompt text applied to every file")
    prompt_group.add_argument(
        "--prompt-file", type=Path, help="File containing the prompt text applied to every file"
    )

    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Gemini model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--requests-file",
        type=Path,
        default=None,
        help="Where to write the batch request JSONL (default: <directory>/ltsum_requests.jsonl)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the batch result JSONL (default: <directory>/ltsum_results.jsonl)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help=f"Seconds between batch job status checks (default: {DEFAULT_POLL_INTERVAL})",
    )
    return parser.parse_args()


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt
    return args.prompt_file.read_text(encoding="utf-8")


def find_html_files(directory: Path) -> list[Path]:
    return sorted(
        p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in (".html", ".htm")
    )


def build_requests_file(html_files: list[Path], prompt: str, requests_path: Path) -> None:
    with requests_path.open("w", encoding="utf-8") as f:
        for path in html_files:
            content = path.read_text(encoding="utf-8", errors="replace")
            request = {
                "key": path.name,
                "request": {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": f"{prompt}\n\n{content}"}],
                        }
                    ]
                },
            }
            f.write(json.dumps(request) + "\n")


def run_batch_job(client: genai.Client, model: str, requests_path: Path) -> types.BatchJob:
    uploaded = client.files.upload(
        file=str(requests_path),
        config=types.UploadFileConfig(display_name=requests_path.stem, mime_type="jsonl"),
    )
    batch_job = client.batches.create(
        model=model,
        src=uploaded.name,
        config={"display_name": f"{requests_path.stem}-batch"},
    )
    print(f"Created batch job: {batch_job.name}")
    return batch_job


def wait_for_completion(
    client: genai.Client, batch_job: types.BatchJob, poll_interval: float
) -> types.BatchJob:
    job_name = batch_job.name
    last_state = None
    while batch_job.state is None or batch_job.state.name not in TERMINAL_STATES:
        state_name = batch_job.state.name if batch_job.state else "UNKNOWN"
        if state_name != last_state:
            print(f"Batch job state: {state_name}")
            last_state = state_name
        time.sleep(poll_interval)
        batch_job = client.batches.get(name=job_name)
    print(f"Batch job finished: {batch_job.state.name}")
    return batch_job


def write_results(client: genai.Client, batch_job: types.BatchJob, output_path: Path) -> None:
    if batch_job.dest is None or not batch_job.dest.file_name:
        raise RuntimeError(f"Batch job produced no output file (state={batch_job.state.name})")
    result_bytes = client.files.download(file=batch_job.dest.file_name)
    output_path.write_bytes(result_bytes)


def main() -> None:
    args = parse_args()
    directory = args.directory
    if not directory.is_dir():
        sys.exit(f"Not a directory: {directory}")

    prompt = load_prompt(args)
    html_files = find_html_files(directory)
    if not html_files:
        sys.exit(f"No HTML files found in {directory}")

    requests_path = args.requests_file or directory / "ltsum_requests.jsonl"
    output_path = args.output or directory / "ltsum_results.jsonl"

    print(f"Found {len(html_files)} HTML file(s) in {directory}")
    build_requests_file(html_files, prompt, requests_path)
    print(f"Wrote batch requests to {requests_path}")

    client = genai.Client()
    batch_job = run_batch_job(client, args.model, requests_path)
    batch_job = wait_for_completion(client, batch_job, args.poll_interval)

    if batch_job.state.name in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"):
        sys.exit(f"Batch job did not succeed: {batch_job.state.name} ({batch_job.error})")

    write_results(client, batch_job, output_path)
    print(f"Wrote batch results to {output_path}")


if __name__ == "__main__":
    main()
