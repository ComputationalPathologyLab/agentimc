#!/usr/bin/env python3
"""
Starter pipeline for implementing the IMC data-analysis workflow described in
the paper's Methods section.

This script does not replace Steinbock, CellCharter, Squidpy, or QuPath.
Instead, it gives you a practical skeleton for the parts you can orchestrate
in Python around those tools:

1. Validate and organize inputs
2. Normalize single-cell feature tables
3. Train a cell-type classifier from annotated cells
4. Predict labels for unannotated cells
5. Aggregate ROI-level summaries for downstream spatial/outcome analysis

Typical usage:
    python imc_pipeline_starter.py init --root ./project
    python imc_pipeline_starter.py normalize --config ./project/config.json
    python imc_pipeline_starter.py train-classifier --config ./project/config.json
    python imc_pipeline_starter.py predict --config ./project/config.json
    python imc_pipeline_starter.py summarize-rois --config ./project/config.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from pathlib import Path
from statistics import mean
from typing import Iterable


DEFAULT_CONFIG = {
    "project_root": "./project",
    "raw_mcd_dir": "./project/raw_mcd",
    "tables_dir": "./project/tables",
    "annotations_dir": "./project/annotations",
    "models_dir": "./project/models",
    "results_dir": "./project/results",
    "normalized_table": "./project/tables/cells_normalized.csv",
    "training_table": "./project/tables/cells_training.csv",
    "unlabeled_table": "./project/tables/cells_unlabeled.csv",
    "predictions_table": "./project/results/cells_predicted.csv",
    "roi_summary_table": "./project/results/roi_summary.csv",
    "classifier_path": "./project/models/cell_type_classifier.pkl",
    "area_column": "cell_area",
    "label_column": "cell_type",
    "roi_column": "roi_id",
    "patient_column": "patient_id",
    "marker_columns": [
        "CD3",
        "CD8",
        "CD45",
        "CD68",
        "CD138",
        "IRF4",
        "HLA_DR",
        "GLUT1",
        "PKM2",
        "ATP5A",
        "CPT1A",
        "CS",
    ],
    "min_cell_area": 4,
    "clip_quantile": 0.99,
    "arcsinh_cofactor": 1.0,
}


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def load_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_columns(rows: list[dict], columns: list[str], table_name: str) -> None:
    if not rows:
        raise ValueError(f"{table_name} is empty.")
    missing = [column for column in columns if column not in rows[0]]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns in {table_name}: {missing_str}")


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute a quantile from an empty list.")
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[lower]
    fraction = index - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def clr_normalize_row(values: list[float], pseudocount: float = 1e-9) -> list[float]:
    adjusted = [value + pseudocount for value in values]
    geometric_mean = math.exp(mean(math.log(value) for value in adjusted))
    return [math.log(value / geometric_mean) for value in adjusted]


def filter_and_normalize_cells(config: dict) -> Path:
    input_path = Path(config["training_table"])
    output_path = Path(config["normalized_table"])
    marker_columns = config["marker_columns"]
    area_column = config["area_column"]

    rows = load_csv_rows(input_path)
    validate_columns(rows, [area_column, *marker_columns], str(input_path))

    filtered = [row.copy() for row in rows if float(row[area_column]) >= config["min_cell_area"]]
    if not filtered:
        raise ValueError("All rows were filtered out by the minimum cell area threshold.")

    clip_values = {
        column: quantile([float(row[column]) for row in filtered], config["clip_quantile"])
        for column in marker_columns
    }

    for row in filtered:
        transformed = []
        for column in marker_columns:
            clipped = min(float(row[column]), clip_values[column])
            arcsinh_value = math.asinh(clipped / config["arcsinh_cofactor"])
            transformed.append(arcsinh_value)
        normalized = clr_normalize_row(transformed)
        for column, value in zip(marker_columns, normalized):
            row[column] = value

    fieldnames = list(filtered[0].keys())
    write_csv_rows(output_path, filtered, fieldnames)
    return output_path


def train_centroid_classifier(config: dict) -> Path:
    input_path = Path(config["normalized_table"])
    model_path = Path(config["classifier_path"])
    marker_columns = config["marker_columns"]
    label_column = config["label_column"]

    rows = load_csv_rows(input_path)
    validate_columns(rows, [label_column, *marker_columns], str(input_path))

    labeled = []
    for row in rows:
        label = str(row[label_column]).strip()
        if label:
            labeled.append(row)
    if not labeled:
        raise ValueError("No labeled cells found in the normalized training table.")

    centroids = {}
    grouped: dict[str, list[dict]] = {}
    for row in labeled:
        grouped.setdefault(str(row[label_column]).strip(), []).append(row)
    for label, group in grouped.items():
        centroids[label] = [
            mean(float(row[column]) for row in group)
            for column in marker_columns
        ]

    payload = {
        "marker_columns": marker_columns,
        "label_column": label_column,
        "centroids": centroids,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(payload, handle)
    return model_path


def predict_from_centroids(config: dict) -> Path:
    input_path = Path(config["unlabeled_table"])
    model_path = Path(config["classifier_path"])
    output_path = Path(config["predictions_table"])

    with model_path.open("rb") as handle:
        model = pickle.load(handle)

    marker_columns = model["marker_columns"]
    rows = load_csv_rows(input_path)
    validate_columns(rows, marker_columns, str(input_path))

    labels = list(model["centroids"].keys())

    for row in rows:
        features = [float(row[column]) for column in marker_columns]
        scored = []
        for label in labels:
            centroid = model["centroids"][label]
            squared_distance = sum((value - center) ** 2 for value, center in zip(features, centroid))
            scored.append((label, math.sqrt(squared_distance)))
        best_label, best_distance = min(scored, key=lambda item: item[1])
        row["predicted_cell_type"] = best_label
        row["prediction_distance"] = best_distance

    fieldnames = list(rows[0].keys())
    write_csv_rows(output_path, rows, fieldnames)
    return output_path


def summarize_rois(config: dict) -> Path:
    input_path = Path(config["predictions_table"])
    output_path = Path(config["roi_summary_table"])
    roi_column = config["roi_column"]
    patient_column = config["patient_column"]

    rows = load_csv_rows(input_path)
    label_column = "predicted_cell_type" if "predicted_cell_type" in rows[0] else config["label_column"]
    validate_columns(rows, [roi_column, patient_column, label_column], str(input_path))

    counts: dict[tuple[str, str, str], int] = {}
    roi_totals: dict[tuple[str, str], int] = {}
    for row in rows:
        patient = str(row[patient_column])
        roi = str(row[roi_column])
        label = str(row[label_column])
        counts[(patient, roi, label)] = counts.get((patient, roi, label), 0) + 1
        roi_totals[(patient, roi)] = roi_totals.get((patient, roi), 0) + 1

    summary_rows = []
    for (patient, roi, label), cell_count in sorted(counts.items()):
        roi_total = roi_totals[(patient, roi)]
        summary_rows.append(
            {
                patient_column: patient,
                roi_column: roi,
                label_column: label,
                "cell_count": cell_count,
                "roi_total": roi_total,
                "cell_fraction": cell_count / roi_total,
            }
        )

    fieldnames = [patient_column, roi_column, label_column, "cell_count", "roi_total", "cell_fraction"]
    write_csv_rows(output_path, summary_rows, fieldnames)
    return output_path


def init_project(root: Path) -> Path:
    config = DEFAULT_CONFIG.copy()
    project_root = root.resolve()
    config["project_root"] = str(project_root)
    config["raw_mcd_dir"] = str(project_root / "raw_mcd")
    config["tables_dir"] = str(project_root / "tables")
    config["annotations_dir"] = str(project_root / "annotations")
    config["models_dir"] = str(project_root / "models")
    config["results_dir"] = str(project_root / "results")
    config["normalized_table"] = str(project_root / "tables" / "cells_normalized.csv")
    config["training_table"] = str(project_root / "tables" / "cells_training.csv")
    config["unlabeled_table"] = str(project_root / "tables" / "cells_unlabeled.csv")
    config["predictions_table"] = str(project_root / "results" / "cells_predicted.csv")
    config["roi_summary_table"] = str(project_root / "results" / "roi_summary.csv")
    config["classifier_path"] = str(project_root / "models" / "cell_type_classifier.pkl")

    ensure_dirs(
        [
            Path(config["raw_mcd_dir"]),
            Path(config["tables_dir"]),
            Path(config["annotations_dir"]),
            Path(config["models_dir"]),
            Path(config["results_dir"]),
        ]
    )

    config_path = project_root / "config.json"
    save_config(config_path, config)
    return config_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Starter IMC analysis pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_cmd = subparsers.add_parser("init", help="Create a starter project layout")
    init_cmd.add_argument("--root", required=True, help="Target project directory")

    normalize_cmd = subparsers.add_parser("normalize", help="Filter and normalize labeled cell table")
    normalize_cmd.add_argument("--config", required=True, help="Path to config.json")

    train_cmd = subparsers.add_parser("train-classifier", help="Train a simple centroid classifier")
    train_cmd.add_argument("--config", required=True, help="Path to config.json")

    predict_cmd = subparsers.add_parser("predict", help="Predict cell types for unannotated cells")
    predict_cmd.add_argument("--config", required=True, help="Path to config.json")

    summary_cmd = subparsers.add_parser("summarize-rois", help="Create ROI-level cell fractions")
    summary_cmd.add_argument("--config", required=True, help="Path to config.json")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        config_path = init_project(Path(args.root))
        print(f"Initialized project at {config_path}")
        return

    config = load_config(Path(args.config))

    if args.command == "normalize":
        output = filter_and_normalize_cells(config)
        print(f"Saved normalized cell table to {output}")
    elif args.command == "train-classifier":
        output = train_centroid_classifier(config)
        print(f"Saved classifier to {output}")
    elif args.command == "predict":
        output = predict_from_centroids(config)
        print(f"Saved predictions to {output}")
    elif args.command == "summarize-rois":
        output = summarize_rois(config)
        print(f"Saved ROI summary to {output}")
    else:
        raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
