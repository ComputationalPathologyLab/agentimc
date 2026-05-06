from __future__ import annotations

import argparse
from pathlib import Path

from imc_copilot import answer_roi_query, generate_batch_report, generate_roi_report


APP_HOME = Path(__file__).resolve().parent
OUTPUTS_DIR = APP_HOME / "outputs"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Terminal copilot for IMC ROI outputs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Ask a question about one ROI output folder.")
    ask_parser.add_argument(
        "--output-dir",
        default=str(OUTPUTS_DIR / "ROI001_D13"),
        help="Path to one ROI output folder.",
    )
    ask_parser.add_argument(
        "query",
        help="Question to ask about the ROI results.",
    )

    report_parser = subparsers.add_parser("report", help="Generate a text report for one ROI output folder.")
    report_parser.add_argument(
        "--output-dir",
        default=str(OUTPUTS_DIR / "ROI001_D13"),
        help="Path to one ROI output folder.",
    )

    batch_parser = subparsers.add_parser("batch-report", help="Generate a report across multiple ROI output folders.")
    batch_parser.add_argument(
        "--outputs-root",
        default=str(OUTPUTS_DIR),
        help="Parent folder containing ROI output subfolders.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ask":
        print(answer_roi_query(Path(args.output_dir), args.query))
        return

    if args.command == "report":
        print(generate_roi_report(Path(args.output_dir)))
        return

    if args.command == "batch-report":
        outputs_root = Path(args.outputs_root)
        output_dirs = sorted(path for path in outputs_root.iterdir() if path.is_dir())
        print(generate_batch_report(output_dirs))
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
