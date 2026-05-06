from __future__ import annotations

import csv
import json
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageFilter

APP_HOME = Path(__file__).resolve().parent
INPUTS_DIR = APP_HOME / "inputs"
OUTPUTS_DIR = APP_HOME / "outputs"
CONFIGS_DIR = APP_HOME / "configs"


@dataclass
class IMCROIConfig:
    roi_dir: str
    output_dir: str | None = None
    preset_name: str = "sarcoma_microenvironment"
    nuclei_markers: list[str] = field(default_factory=lambda: ["DNA1", "DNA2"])
    boundary_markers: list[str] = field(
        default_factory=lambda: ["CD3", "CD4", "CD8", "CD68", "CD138", "CD31", "aSMA"]
    )
    measurement_markers: list[str] = field(
        default_factory=lambda: [
            "DNA1",
            "DNA2",
            "CD3",
            "CD4",
            "CD8",
            "CD20",
            "CD68",
            "CD138",
            "CD56",
            "CD86",
            "MHC_II",
            "CD163",
            "CD45RO",
            "PD1",
            "PDL1",
            "LAG3",
            "CTLA4",
            "TIM3",
            "Ki67",
            "GranzymeB",
            "FoxP3",
            "Tbet",
            "CD31",
            "aSMA",
            "CD44",
            "CD47",
            "ERG",
            "S100",
            "Brachiury",
        ]
    )
    segmentation_blur_radius: float = 1.2
    segmentation_threshold_percentile: float = 96.0
    min_nucleus_area: int = 20
    phenotype_high_percentile: float = 85.0
    phenotype_support_percentile: float = 75.0

    def resolved_roi_dir(self) -> Path:
        return Path(self.roi_dir).expanduser().resolve()

    def resolved_output_dir(self) -> Path:
        if self.output_dir:
            return Path(self.output_dir).expanduser().resolve()
        return OUTPUTS_DIR / self.resolved_roi_dir().name


PRESET_CONFIGS: dict[str, dict[str, Any]] = {
    "generic_imc": {
        "nuclei_markers": ["DNA1", "DNA2"],
        "boundary_markers": ["CD3", "CD4", "CD8", "CD68", "CD138", "CD31", "aSMA"],
    },
    "sarcoma_microenvironment": {
        "nuclei_markers": ["DNA1", "DNA2"],
        "boundary_markers": ["CD3", "CD4", "CD8", "CD68", "CD138", "CD31", "aSMA"],
        "measurement_markers": [
            "DNA1",
            "DNA2",
            "CD3",
            "CD4",
            "CD8",
            "CD20",
            "CD68",
            "CD138",
            "CD56",
            "CD86",
            "MHC_II",
            "CD163",
            "CD45RO",
            "PD1",
            "PDL1",
            "LAG3",
            "CTLA4",
            "TIM3",
            "Ki67",
            "GranzymeB",
            "FoxP3",
            "Tbet",
            "CD31",
            "aSMA",
            "CD44",
            "CD47",
            "ERG",
            "S100",
            "Brachiury",
            "CD11c",
            "CD80",
            "CD21",
            "CD10",
        ],
    },
}


def config_from_preset(roi_dir: str, preset_name: str = "sarcoma_microenvironment") -> IMCROIConfig:
    base = IMCROIConfig(roi_dir=roi_dir, preset_name=preset_name)
    preset = PRESET_CONFIGS.get(preset_name, {})
    for key, value in preset.items():
        setattr(base, key, value)
    return base


def list_channel_files(roi_dir: Path) -> list[Path]:
    return sorted(list(roi_dir.glob("*.tif")) + list(roi_dir.glob("*.tiff")))


def parse_channel_name(path: Path) -> dict[str, str]:
    stem = path.name.replace(".ome.tiff", "").replace(".ome.tif", "")
    if "_" in stem:
        metal_tag, marker = stem.split("_", 1)
    else:
        metal_tag, marker = "UNKNOWN", stem
    return {"filename": path.name, "metal_tag": metal_tag, "marker": marker}


def load_channel_image(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.array(img)


def normalize_for_display(image: np.ndarray, low_q: float = 1.0, high_q: float = 99.5) -> np.ndarray:
    image = image.astype(np.float32)
    low = np.percentile(image, low_q)
    high = np.percentile(image, high_q)
    if high <= low:
        return np.zeros_like(image, dtype=np.float32)
    clipped = np.clip(image, low, high)
    return (clipped - low) / (high - low)


def smooth_image(image: np.ndarray, radius: float) -> np.ndarray:
    pil_img = Image.fromarray(np.uint8(np.clip(image * 255, 0, 255)))
    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.array(blurred).astype(np.float32) / 255.0


def connected_components(binary_mask: np.ndarray) -> tuple[np.ndarray, list[dict[str, float | int]]]:
    height, width = binary_mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    components: list[dict[str, float | int]] = []
    current_label = 0
    neighbors = [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ]

    for y in range(height):
        for x in range(width):
            if not binary_mask[y, x] or labels[y, x] != 0:
                continue
            current_label += 1
            queue = deque([(y, x)])
            labels[y, x] = current_label
            pixels: list[tuple[int, int]] = []

            while queue:
                cy, cx = queue.popleft()
                pixels.append((cy, cx))
                for dy, dx in neighbors:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        if binary_mask[ny, nx] and labels[ny, nx] == 0:
                            labels[ny, nx] = current_label
                            queue.append((ny, nx))

            ys = [p[0] for p in pixels]
            xs = [p[1] for p in pixels]
            components.append(
                {
                    "label": current_label,
                    "area_pixels": len(pixels),
                    "centroid_y": float(np.mean(ys)),
                    "centroid_x": float(np.mean(xs)),
                    "min_y": int(min(ys)),
                    "max_y": int(max(ys)),
                    "min_x": int(min(xs)),
                    "max_x": int(max(xs)),
                }
            )
    return labels, components


def percentile_threshold(rows: list[dict], column: str, percentile: float) -> float:
    return float(np.percentile([float(row[column]) for row in rows], percentile))


def object_pixels_from_labels(label_image: np.ndarray) -> dict[int, list[tuple[int, int]]]:
    pixel_map: dict[int, list[tuple[int, int]]] = {}
    ys, xs = np.nonzero(label_image > 0)
    for y, x in zip(ys, xs):
        label = int(label_image[y, x])
        pixel_map.setdefault(label, []).append((int(y), int(x)))
    return pixel_map


def measure_marker_mean(image: np.ndarray, pixels: list[tuple[int, int]]) -> float:
    values = [float(image[y, x]) for y, x in pixels]
    return float(np.mean(values)) if values else 0.0


def measure_marker_max(image: np.ndarray, pixels: list[tuple[int, int]]) -> float:
    values = [float(image[y, x]) for y, x in pixels]
    return float(np.max(values)) if values else 0.0


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return float(np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2))


def nearest_neighbor_indices(rows: list[dict]) -> list[int]:
    neighbors: list[int] = []
    for i, row_i in enumerate(rows):
        best_j = 0
        best_distance = float("inf")
        xi, yi = float(row_i["centroid_x"]), float(row_i["centroid_y"])
        for j, row_j in enumerate(rows):
            if i == j:
                continue
            xj, yj = float(row_j["centroid_x"]), float(row_j["centroid_y"])
            dist = euclidean_distance(xi, yi, xj, yj)
            if dist < best_distance:
                best_distance = dist
                best_j = j
        neighbors.append(best_j)
    return neighbors


def mean_by_group(rows: list[dict], group_key: str, value_keys: list[str]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(str(row[group_key]), []).append(row)
    summary = []
    for group_name, group_rows in groups.items():
        out = {group_key: group_name, "n_objects": len(group_rows)}
        for key in value_keys:
            out[key] = float(np.mean([float(r[key]) for r in group_rows]))
        summary.append(out)
    return summary


class IMCROIAnalyzer:
    def __init__(self, config: IMCROIConfig):
        self.config = config
        self.roi_dir = config.resolved_roi_dir()
        self.output_dir = config.resolved_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.channel_files = list_channel_files(self.roi_dir)
        self.channel_info = [parse_channel_name(path) for path in self.channel_files]
        self.channel_map = {row["marker"]: self.roi_dir / row["filename"] for row in self.channel_info}
        self.cache: dict[str, Any] = {}

    def save_config(self) -> Path:
        CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / "pipeline_config.json"
        path.write_text(json.dumps(asdict(self.config), indent=2), encoding="utf-8")
        return path

    def find_channel(self, marker_name: str) -> Path | None:
        return self.channel_map.get(marker_name)

    def load_marker(self, marker_name: str) -> np.ndarray:
        path = self.find_channel(marker_name)
        if path is None:
            raise FileNotFoundError(f"Marker not found in ROI: {marker_name}")
        return load_channel_image(path)

    def available_markers(self, markers: list[str]) -> list[str]:
        return [marker for marker in markers if self.find_channel(marker) is not None]

    def run_inspection(self) -> dict[str, Any]:
        image_shapes = {}
        image_dtypes = {}
        for path in self.channel_files:
            arr = load_channel_image(path)
            image_shapes[path.name] = arr.shape
            image_dtypes[path.name] = str(arr.dtype)
        result = {
            "n_channel_files": len(self.channel_files),
            "markers": [row["marker"] for row in self.channel_info],
            "unique_shapes": sorted(set(image_shapes.values())),
            "unique_dtypes": sorted(set(image_dtypes.values())),
        }
        self.cache["inspection"] = result
        return result

    def average_normalized_markers(self, markers: list[str]) -> np.ndarray:
        images = [normalize_for_display(self.load_marker(marker)) for marker in markers]
        return np.stack(images, axis=0).mean(axis=0)

    def run_composites(self) -> dict[str, Path]:
        nuclei = self.available_markers(self.config.nuclei_markers)
        boundary = self.available_markers(self.config.boundary_markers)
        nuclear_composite = self.average_normalized_markers(nuclei)
        boundary_composite = self.average_normalized_markers(boundary)
        overlay = np.dstack(
            [
                boundary_composite,
                0.5 * nuclear_composite + 0.5 * boundary_composite,
                nuclear_composite,
            ]
        )
        overlay = np.clip(overlay, 0, 1)

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        axes[0].imshow(nuclear_composite, cmap="gray")
        axes[0].set_title("Nuclear Composite")
        axes[0].axis("off")
        axes[1].imshow(boundary_composite, cmap="gray")
        axes[1].set_title("Boundary Composite")
        axes[1].axis("off")
        plt.tight_layout()
        composites_path = self.output_dir / "step2_segmentation_composites.png"
        plt.savefig(composites_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(overlay)
        ax.set_title("Segmentation Guidance Overlay")
        ax.axis("off")
        plt.tight_layout()
        overlay_path = self.output_dir / "step2_segmentation_overlay.png"
        plt.savefig(overlay_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        self.cache["nuclear_composite"] = nuclear_composite
        self.cache["boundary_composite"] = boundary_composite
        self.cache["overlay"] = overlay
        return {"composites_path": composites_path, "overlay_path": overlay_path}

    def run_segmentation(self) -> dict[str, Any]:
        nuclear_composite = self.cache["nuclear_composite"]
        smoothed = smooth_image(nuclear_composite, self.config.segmentation_blur_radius)
        threshold = np.percentile(smoothed, self.config.segmentation_threshold_percentile)
        binary = smoothed > threshold
        labels, components = connected_components(binary)
        filtered = [comp for comp in components if int(comp["area_pixels"]) >= self.config.min_nucleus_area]

        filtered_labels = np.zeros_like(labels)
        for new_label, comp in enumerate(filtered, start=1):
            filtered_labels[labels == comp["label"]] = new_label
            comp["label"] = new_label

        display_labels = filtered_labels.astype(np.float32)
        if display_labels.max() > 0:
            display_labels = display_labels / display_labels.max()

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        axes[0].imshow(smoothed, cmap="gray")
        axes[0].set_title("Smoothed Nuclear Composite")
        axes[0].axis("off")
        axes[1].imshow(binary, cmap="gray")
        axes[1].set_title("Binary Nuclear Mask")
        axes[1].axis("off")
        axes[2].imshow(display_labels, cmap="nipy_spectral")
        axes[2].set_title("Filtered Nuclei Objects")
        axes[2].axis("off")
        plt.tight_layout()
        seg_path = self.output_dir / "step3_first_pass_segmentation.png"
        plt.savefig(seg_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        objects_csv = self.output_dir / "step3_nuclei_objects.csv"
        with objects_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(filtered[0].keys()) if filtered else [])
            writer.writeheader()
            writer.writerows(filtered)

        self.cache["filtered_components"] = filtered
        self.cache["filtered_labels"] = filtered_labels
        return {
            "initial_components": len(components),
            "filtered_components": len(filtered),
            "threshold": float(threshold),
            "segmentation_path": seg_path,
            "objects_csv": objects_csv,
        }

    def run_quantification(self) -> dict[str, Any]:
        labels = self.cache["filtered_labels"]
        components = self.cache["filtered_components"]
        pixel_map = object_pixels_from_labels(labels)
        markers = self.available_markers(self.config.measurement_markers)
        marker_images = {marker: self.load_marker(marker) for marker in markers}
        max_stat_markers = {"Ki67", "GranzymeB", "PD1", "PDL1", "LAG3", "CTLA4", "TIM3"}
        component_lookup = {int(comp["label"]): comp for comp in components}

        rows = []
        for label, pixels in sorted(pixel_map.items()):
            comp = component_lookup[label]
            row = {
                "object_label": label,
                "area_pixels": comp["area_pixels"],
                "centroid_y": comp["centroid_y"],
                "centroid_x": comp["centroid_x"],
                "roi_id": self.roi_dir.name,
            }
            for marker, image in marker_images.items():
                row[f"{marker}_mean"] = measure_marker_mean(image, pixels)
                if marker in max_stat_markers:
                    row[f"{marker}_max"] = measure_marker_max(image, pixels)
            rows.append(row)

        out_csv = self.output_dir / "step4_object_expression_table.csv"
        with out_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)

        self.cache["expression_rows"] = rows
        return {"n_objects_quantified": len(rows), "expression_csv": out_csv}

    def run_phenotyping(self) -> dict[str, Any]:
        rows = self.cache["expression_rows"]
        phenotype_threshold_markers = [
            "CD3_mean",
            "CD4_mean",
            "CD8_mean",
            "CD20_mean",
            "CD68_mean",
            "CD138_mean",
            "CD31_mean",
            "aSMA_mean",
            "FoxP3_mean",
            "PD1_mean",
            "PDL1_mean",
            "CD56_mean",
            "CD86_mean",
            "MHC_II_mean",
            "CD163_mean",
            "CD45RO_mean",
            "GranzymeB_mean",
            "Tbet_mean",
        ]
        phenotype_threshold_markers = [m for m in phenotype_threshold_markers if m in rows[0]]
        high_thresholds = {
            column: percentile_threshold(rows, column, self.config.phenotype_high_percentile)
            for column in phenotype_threshold_markers
        }
        support_thresholds = {
            column: percentile_threshold(rows, column, self.config.phenotype_support_percentile)
            for column in phenotype_threshold_markers
        }

        def is_high(row: dict, column: str) -> bool:
            return float(row.get(column, 0.0)) >= high_thresholds.get(column, float("inf"))

        def is_supportive(row: dict, column: str) -> bool:
            return float(row.get(column, 0.0)) >= support_thresholds.get(column, float("inf"))

        def assign_label(row: dict) -> str:
            cd3 = is_high(row, "CD3_mean")
            cd4 = is_high(row, "CD4_mean")
            cd8 = is_high(row, "CD8_mean")
            cd20 = is_high(row, "CD20_mean")
            cd68 = is_high(row, "CD68_mean")
            cd138 = is_high(row, "CD138_mean")
            cd31 = is_high(row, "CD31_mean")
            asma = is_high(row, "aSMA_mean")
            foxp3 = is_high(row, "FoxP3_mean")
            cd56 = is_high(row, "CD56_mean")
            cd86 = is_high(row, "CD86_mean")
            mhc2 = is_high(row, "MHC_II_mean")
            cd163 = is_high(row, "CD163_mean")
            cd45ro = is_high(row, "CD45RO_mean")
            granzymeb = is_high(row, "GranzymeB_mean")
            tbet = is_high(row, "Tbet_mean")

            cd3_support = is_supportive(row, "CD3_mean")
            cd8_support = is_supportive(row, "CD8_mean")
            cd68_support = is_supportive(row, "CD68_mean")
            cd138_support = is_supportive(row, "CD138_mean")
            cd56_support = is_supportive(row, "CD56_mean")
            cd86_support = is_supportive(row, "CD86_mean")
            mhc2_support = is_supportive(row, "MHC_II_mean")
            cd163_support = is_supportive(row, "CD163_mean")
            cd45ro_support = is_supportive(row, "CD45RO_mean")

            if cd138 and not (cd68 or cd163 or cd86):
                return "Plasma_like"
            if (cd68 and not cd138) or (cd68 and cd163) or (cd68 and mhc2) or (cd86 and mhc2):
                return "Myeloid_like"
            if cd3 and cd8 and (granzymeb or tbet):
                return "T_cell_CD8_like"
            if cd3 and cd4 and foxp3:
                return "Treg_like"
            if cd3 and cd4:
                return "T_cell_CD4_like"
            if (cd3 and cd8) or (cd3_support and cd8_support):
                return "T_cell_CD8_like"
            if cd20:
                return "B_cell_like"
            if cd56 and not cd3:
                return "NK_like"
            if cd31:
                return "Endothelial_like"
            if asma:
                return "Stromal_like"
            if cd3_support or cd45ro or cd45ro_support:
                return "T_cell_other_like"
            if cd20 or is_supportive(row, "CD20_mean"):
                return "B_cell_like"
            if cd68_support or cd163_support or mhc2_support or cd86_support:
                return "Myeloid_like"
            if cd138_support:
                return "Plasma_like"
            if cd56_support:
                return "NK_like"
            return "Unassigned"

        for row in rows:
            row["first_pass_label"] = assign_label(row)

        counts: dict[str, int] = {}
        for row in rows:
            counts[row["first_pass_label"]] = counts.get(row["first_pass_label"], 0) + 1

        out_csv = self.output_dir / "step5_object_expression_with_labels.csv"
        with out_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        self.cache["expression_rows"] = rows
        self.cache["label_counts"] = counts
        self.cache["high_thresholds"] = high_thresholds
        self.cache["support_thresholds"] = support_thresholds
        return {"label_counts": counts, "phenotyped_csv": out_csv}

    def run_spatial(self) -> dict[str, Any]:
        rows = self.cache["expression_rows"]
        nn_idx = nearest_neighbor_indices(rows)
        for i, j in enumerate(nn_idx):
            row_i = rows[i]
            row_j = rows[j]
            dist = euclidean_distance(
                float(row_i["centroid_x"]),
                float(row_i["centroid_y"]),
                float(row_j["centroid_x"]),
                float(row_j["centroid_y"]),
            )
            row_i["nearest_neighbor_label"] = row_j["object_label"]
            row_i["nearest_neighbor_type"] = row_j["first_pass_label"]
            row_i["nearest_neighbor_distance"] = dist

        pair_counts: dict[tuple[str, str], int] = {}
        distance_by_label: dict[str, list[float]] = {}
        for row in rows:
            source = row["first_pass_label"]
            target = row["nearest_neighbor_type"]
            pair_counts[(source, target)] = pair_counts.get((source, target), 0) + 1
            distance_by_label.setdefault(source, []).append(float(row["nearest_neighbor_distance"]))

        mean_distance_by_label = {
            label: float(np.mean(distances)) for label, distances in distance_by_label.items()
        }

        out_csv = self.output_dir / "step6_spatial_nearest_neighbor_table.csv"
        with out_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        self.cache["expression_rows"] = rows
        self.cache["pair_counts"] = pair_counts
        self.cache["mean_distance_by_label"] = mean_distance_by_label
        return {"pair_counts": pair_counts, "mean_distance_by_label": mean_distance_by_label, "spatial_csv": out_csv}

    def run_summary(self) -> dict[str, Any]:
        rows = self.cache["expression_rows"]
        mean_distance_by_label = self.cache["mean_distance_by_label"]
        summary_markers = [
            "CD3_mean",
            "CD4_mean",
            "CD8_mean",
            "CD20_mean",
            "CD68_mean",
            "CD138_mean",
            "CD56_mean",
            "CD86_mean",
            "MHC_II_mean",
            "CD163_mean",
            "CD45RO_mean",
            "PD1_mean",
            "PDL1_mean",
            "LAG3_mean",
            "CTLA4_mean",
            "TIM3_mean",
            "Ki67_mean",
            "GranzymeB_mean",
            "FoxP3_mean",
            "Tbet_mean",
            "CD31_mean",
            "aSMA_mean",
        ]
        summary_markers = [m for m in summary_markers if m in rows[0]]
        phenotype_summary = mean_by_group(rows, "first_pass_label", summary_markers)
        phenotype_summary = sorted(phenotype_summary, key=lambda row: (-row["n_objects"], row["first_pass_label"]))

        out_csv = self.output_dir / "step7_phenotype_marker_summary.csv"
        with out_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(phenotype_summary[0].keys()) if phenotype_summary else [])
            writer.writeheader()
            writer.writerows(phenotype_summary)

        final_summary_lines = [
            f"ROI analyzed: {self.roi_dir.name}",
            f"Number of channel images: {len(self.channel_files)}",
            f"Image size: {self.cache['inspection']['unique_shapes'][0][0]} x {self.cache['inspection']['unique_shapes'][0][1]} pixels",
            f"Detected first-pass nuclei-like objects: {len(self.cache['filtered_components'])}",
            f"Phenotype groups identified: {len(phenotype_summary)}",
            f"Most abundant phenotype: {phenotype_summary[0]['first_pass_label']} ({phenotype_summary[0]['n_objects']} objects)",
        ]
        note_path = self.output_dir / "final_presentation_summary.txt"
        with note_path.open("w", encoding="utf-8") as handle:
            handle.write("Single-ROI IMC analysis summary\n")
            handle.write("=" * 32 + "\n\n")
            for line in final_summary_lines:
                handle.write(f"- {line}\n")
            handle.write("\nPipeline steps:\n")
            handle.write("- ROI inspection and marker inventory\n")
            handle.write("- Segmentation channel selection\n")
            handle.write("- First-pass nuclei segmentation\n")
            handle.write("- Object-level marker quantification\n")
            handle.write("- First-pass phenotyping\n")
            handle.write("- Nearest-neighbor spatial analysis\n")
            handle.write("- Phenotype-level summary plots\n")
            handle.write("\nLimitations:\n")
            handle.write("- Baseline segmentation only\n")
            handle.write("- Rule-based phenotyping only\n")
            handle.write("- Simple nearest-neighbor spatial analysis only\n")
            handle.write("- Single ROI only\n")

        return {"phenotype_summary_csv": out_csv, "presentation_summary_txt": note_path}

    def run_full_pipeline(self) -> dict[str, Any]:
        self.save_config()
        results = {
            "inspection": self.run_inspection(),
            "composites": self.run_composites(),
            "segmentation": self.run_segmentation(),
            "quantification": self.run_quantification(),
            "phenotyping": self.run_phenotyping(),
            "spatial": self.run_spatial(),
            "summary": self.run_summary(),
        }
        return results


def collect_output_files(output_dir: Path) -> dict[str, list[Path]]:
    files = sorted([path for path in output_dir.iterdir() if path.is_file()]) if output_dir.exists() else []
    grouped = {"images": [], "tables": [], "texts": [], "other": []}
    for path in files:
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            grouped["images"].append(path)
        elif suffix in {".csv", ".tsv"}:
            grouped["tables"].append(path)
        elif suffix in {".txt", ".json", ".md"}:
            grouped["texts"].append(path)
        else:
            grouped["other"].append(path)
    return grouped


def run_batch_pipeline(configs: list[IMCROIConfig]) -> list[dict[str, Any]]:
    batch_results = []
    for config in configs:
        analyzer = IMCROIAnalyzer(config)
        result = analyzer.run_full_pipeline()
        batch_results.append(
            {
                "roi_name": analyzer.roi_dir.name,
                "roi_dir": str(analyzer.roi_dir),
                "output_dir": str(analyzer.output_dir),
                "results": result,
                "outputs": collect_output_files(analyzer.output_dir),
            }
        )
    return batch_results
