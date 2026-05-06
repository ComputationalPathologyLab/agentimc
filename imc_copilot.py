from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ROIKnowledgeBase:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.step5 = read_csv_rows(self.output_dir / "step5_object_expression_with_labels.csv")
        self.step6 = read_csv_rows(self.output_dir / "step6_spatial_nearest_neighbor_table.csv")
        self.step7 = read_csv_rows(self.output_dir / "step7_phenotype_marker_summary.csv")
        self.summary_text = (self.output_dir / "final_presentation_summary.txt").read_text(encoding="utf-8") if (self.output_dir / "final_presentation_summary.txt").exists() else ""

    def phenotype_counts(self) -> dict[str, int]:
        return Counter(row["first_pass_label"] for row in self.step5)

    def dominant_phenotypes(self, top_n: int = 5) -> list[tuple[str, int]]:
        return self.phenotype_counts().most_common(top_n)

    def nearest_neighbor_pairs(self, top_n: int = 10) -> list[tuple[tuple[str, str], int]]:
        pairs = Counter((row["first_pass_label"], row["nearest_neighbor_type"]) for row in self.step6)
        return pairs.most_common(top_n)

    def mean_nn_distance_by_label(self) -> dict[str, float]:
        grouped = defaultdict(list)
        for row in self.step6:
            grouped[row["first_pass_label"]].append(float(row["nearest_neighbor_distance"]))
        return {label: sum(vals) / len(vals) for label, vals in grouped.items() if vals}

    def phenotype_summary_row(self, label: str) -> dict | None:
        for row in self.step7:
            if row["first_pass_label"].lower() == label.lower():
                return row
        return None

    def strongest_markers_for_label(self, label: str, top_n: int = 5) -> list[tuple[str, float]]:
        row = self.phenotype_summary_row(label)
        if row is None:
            return []
        marker_values = []
        for key, value in row.items():
            if key.endswith("_mean"):
                marker_values.append((key.replace("_mean", ""), float(value)))
        marker_values.sort(key=lambda item: item[1], reverse=True)
        return marker_values[:top_n]


def answer_roi_query(output_dir: str | Path, query: str) -> str:
    kb = ROIKnowledgeBase(output_dir)
    q = query.lower().strip()

    if not q:
        return "Ask about dominant phenotypes, marker programs, spatial interactions, or request a report."

    if "dominant" in q or "most abundant" in q or "top phenotype" in q:
        tops = kb.dominant_phenotypes()
        lines = ["Top phenotypes:"]
        lines += [f"- {label}: {count} objects" for label, count in tops]
        return "\n".join(lines)

    if "spatial" in q or "neighbor" in q or "interaction" in q:
        pairs = kb.nearest_neighbor_pairs()
        lines = ["Top nearest-neighbor phenotype pairs:"]
        lines += [f"- {src} -> {dst}: {count}" for (src, dst), count in pairs]
        return "\n".join(lines)

    if "distance" in q:
        distances = kb.mean_nn_distance_by_label()
        items = sorted(distances.items(), key=lambda item: item[1])
        lines = ["Mean nearest-neighbor distance by phenotype:"]
        lines += [f"- {label}: {value:.2f} pixels" for label, value in items]
        return "\n".join(lines)

    if "report" in q or "summary" in q:
        return generate_roi_report(output_dir)

    if "marker" in q or "express" in q:
        labels = list(kb.phenotype_counts().keys())
        matched = None
        for label in labels:
            if label.lower().replace("_", " ") in q or label.lower() in q:
                matched = label
                break
        if matched is None and labels:
            matched = kb.dominant_phenotypes(1)[0][0]
        markers = kb.strongest_markers_for_label(matched)
        if not markers:
            return f"I could not find a phenotype summary row for '{matched}'."
        lines = [f"Strongest mean markers for {matched}:"]
        lines += [f"- {marker}: {value:.3f}" for marker, value in markers]
        return "\n".join(lines)

    return (
        "I can help with: dominant phenotypes, marker summaries by phenotype, "
        "nearest-neighbor interactions, nearest-neighbor distances, or a full ROI report."
    )


def generate_roi_report(output_dir: str | Path) -> str:
    kb = ROIKnowledgeBase(output_dir)
    dominant = kb.dominant_phenotypes(top_n=5)
    pairs = kb.nearest_neighbor_pairs(top_n=5)
    distances = sorted(kb.mean_nn_distance_by_label().items(), key=lambda item: item[1])[:5]

    lines = [
        f"ROI report for {Path(output_dir).name}",
        "",
        "Dominant phenotypes:",
    ]
    lines += [f"- {label}: {count} objects" for label, count in dominant]
    lines += [
        "",
        "Top nearest-neighbor interactions:",
    ]
    lines += [f"- {src} -> {dst}: {count}" for (src, dst), count in pairs]
    lines += [
        "",
        "Shortest mean nearest-neighbor distances:",
    ]
    lines += [f"- {label}: {value:.2f} pixels" for label, value in distances]
    lines += [
        "",
        "Limitations:",
        "- baseline segmentation",
        "- rule-based phenotyping",
        "- nearest-neighbor spatial analysis only",
        "- single-ROI interpretation unless compared across multiple ROI outputs",
    ]
    return "\n".join(lines)


def generate_batch_report(output_dirs: list[str | Path]) -> str:
    roi_summaries = []
    aggregate_counts = Counter()
    for out in output_dirs:
        kb = ROIKnowledgeBase(out)
        counts = kb.phenotype_counts()
        aggregate_counts.update(counts)
        dominant = kb.dominant_phenotypes(top_n=3)
        roi_summaries.append((Path(out).name, dominant))

    lines = ["Batch ROI report", "", "Per-ROI dominant phenotypes:"]
    for roi_name, dominant in roi_summaries:
        formatted = ", ".join([f"{label} ({count})" for label, count in dominant])
        lines.append(f"- {roi_name}: {formatted}")

    lines += ["", "Aggregate phenotype counts across ROI outputs:"]
    lines += [f"- {label}: {count}" for label, count in aggregate_counts.most_common()]
    return "\n".join(lines)
