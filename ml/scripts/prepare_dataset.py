"""Run validation, feature engineering, preprocessing, and chronological exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.preprocessing.pipeline import prepare_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare SmartER synthetic ER data")
    parser.add_argument("--input", type=Path, default=Path("dataset/generated/synthetic_er_hourly.csv"))
    parser.add_argument("--output", type=Path, default=Path("dataset/processed"))
    args = parser.parse_args()
    print(json.dumps(prepare_dataset(args.input, args.output), indent=2, default=str))


if __name__ == "__main__":
    main()