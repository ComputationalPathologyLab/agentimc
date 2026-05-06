# %% [markdown]
# # ROI Template: Step-by-Step IMC Analysis Notebook
#
# This notebook-style script is written to be:
#
# - understandable for someone new to the analysis
# - explainable to a colleague
# - reproducible, because every step is written down as code
# - built incrementally, one stage at a time
#
# This template can be reused for any ROI with the same folder structure. Start by changing the `ROI_DIR` variable in the first code cell.
# We are not segmenting cells or classifying cell types yet.
#
# The folder `your ROI folder/` contains one ROI extracted from a larger IMC acquisition.
# Each `.ome.tiff` file is one imaging channel for the same 1000 x 1000 field of view.
#
# In this first step, we will:
#
# 1. list all channel files
# 2. parse marker names from filenames
# 3. check that all images have the same dimensions
# 4. display a few key channels to understand what kind of data we have

# %%
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


ROI_DIR = Path("PUT_ROI_FOLDER_HERE")
OUTPUT_DIR = Path(f"{ROI_DIR.name}_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def list_channel_files(roi_dir: Path) -> list[Path]:
    return sorted(list(roi_dir.glob("*.tif")) + list(roi_dir.glob("*.tiff")))


def parse_channel_name(path: Path) -> dict:
    """
    Example filename:
        170Er_CD3.ome.tiff

    We split this into:
    - metal_tag: 170Er
    - marker: CD3
    """
    stem = path.name.replace(".ome.tiff", "").replace(".ome.tif", "")
    if "_" in stem:
        metal_tag, marker = stem.split("_", 1)
    else:
        metal_tag, marker = "UNKNOWN", stem
    return {
        "filename": path.name,
        "metal_tag": metal_tag,
        "marker": marker,
    }


def load_channel_image(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.array(img)


channel_files = list_channel_files(ROI_DIR)
channel_info = [parse_channel_name(path) for path in channel_files]

print(f"ROI folder: {ROI_DIR.resolve()}")
print(f"Number of channel files: {len(channel_files)}")
print()
print("First 10 channels:")
for row in channel_info[:10]:
    print(f"- {row['filename']}")

# %% [markdown]
# ## Why this step matters
#
# Before doing any biology, we need to confirm a simple but critical assumption:
# all files in this ROI should describe the same physical region.
#
# That means:
#
# - same width and height
# - same image type
# - one marker per file
#
# If this is wrong, the downstream pipeline becomes unreliable.

# %%
image_shapes = {}
image_dtypes = {}

for path in channel_files:
    array = load_channel_image(path)
    image_shapes[path.name] = array.shape
    image_dtypes[path.name] = str(array.dtype)

unique_shapes = sorted(set(image_shapes.values()))
unique_dtypes = sorted(set(image_dtypes.values()))

print("Unique image shapes:", unique_shapes)
print("Unique dtypes:", unique_dtypes)

if len(unique_shapes) == 1:
    print("All channels have the same shape. Good.")
else:
    print("Warning: not all channels have the same shape.")

# %% [markdown]
# ## Marker inventory
#
# Here we extract the marker names from the filenames so we can start thinking in
# biological terms rather than file names.
#
# From a quick look, this ROI contains:
#
# - DNA channels: `DNA1`, `DNA2`
# - immune markers: `CD3`, `CD4`, `CD8`, `CD20`, `CD68`, `CD86`, `CD138`
# - checkpoint markers: `PD1`, `PDL1`, `CTLA4`, `LAG3`, `TIM3`
# - functional markers: `Ki67`, `GranzymeB`, `FoxP3`, `Tbet`, `BCL2`
# - structural markers: `aSMA`, `CD31`
#
# We are not assigning cell types yet. We are only organizing the panel.

# %%
markers = [row["marker"] for row in channel_info]
print("Markers in this ROI:")
for marker in markers:
    print(f"- {marker}")

# %% [markdown]
# ## Visual sanity check
#
# A very useful first check is to display a few channels:
#
# - `DNA1` and `DNA2` help us locate nuclei
# - membrane or lineage markers such as `CD3`, `CD4`, `CD8`, `CD138`, `CD68`
#   help us see whether the ROI has interpretable biological structure
#
# We use percentile scaling rather than raw intensity so faint and bright channels
# are easier to compare visually.

# %%
def find_channel(marker_name: str) -> Path | None:
    for path in channel_files:
        if parse_channel_name(path)["marker"] == marker_name:
            return path
    return None


def normalize_for_display(image: np.ndarray, low_q: float = 1.0, high_q: float = 99.5) -> np.ndarray:
    image = image.astype(np.float32)
    low = np.percentile(image, low_q)
    high = np.percentile(image, high_q)
    if high <= low:
        return np.zeros_like(image, dtype=np.float32)
    clipped = np.clip(image, low, high)
    return (clipped - low) / (high - low)


markers_to_show = ["DNA1", "DNA2", "CD3", "CD4", "CD8", "CD68", "CD138", "PDL1"]
available = [(marker, find_channel(marker)) for marker in markers_to_show]
available = [(marker, path) for marker, path in available if path is not None]

fig, axes = plt.subplots(2, 4, figsize=(16, 8))
axes = axes.ravel()

for ax, (marker, path) in zip(axes, available):
    image = load_channel_image(path)
    ax.imshow(normalize_for_display(image), cmap="gray")
    ax.set_title(marker)
    ax.axis("off")

for ax in axes[len(available):]:
    ax.axis("off")

plt.tight_layout()
preview_path = OUTPUT_DIR / "step1_channel_preview.png"
plt.savefig(preview_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved preview figure to: {preview_path.resolve()}")

# %% [markdown]
# ## Step 1 takeaway
#
# At this point, we have confirmed that:
#
# - the ROI is a stack of 43 aligned channel images
# - each channel is 1000 x 1000 pixels
# - we can identify important markers directly from filenames
# - the data is ready for the next stage: selecting the channels needed for segmentation
#
# In the next step, we should decide:
#
# 1. which channels define nuclei
# 2. which channels help define cell boundaries
# 3. which channels we want to carry into downstream quantification
#
# That next step will be the bridge from "looking at images" to "building a cell-level dataset".

# %% [markdown]
# # Step 2: Choose the channels for segmentation
#
# Now we move from simple inspection to a more analytical decision:
# **which channels should define the objects we want to segment?**
#
# In IMC, segmentation usually needs two kinds of information:
#
# 1. **nuclear channels**
#    These tell us where cell nuclei are.
# 2. **boundary-supporting channels**
#    These help separate one cell from another by highlighting membranes or
#    tissue structure.
#
# Based on the panel in this ROI, a sensible first choice is:
#
# - nuclei: `DNA1`, `DNA2`
# - boundary-supporting markers: `CD3`, `CD4`, `CD8`, `CD68`, `CD138`, `CD31`, `aSMA`
#
# This is not yet the final segmentation. This is the step where we explain
# *why* we would choose those channels.

# %%
nuclear_markers = ["DNA1", "DNA2"]
boundary_markers = ["CD3", "CD4", "CD8", "CD68", "CD138", "CD31", "aSMA"]
quantification_markers = [
    "CD20", "CD68", "CD138", "CD47", "CD31", "Tbet", "BCL2", "CD44",
    "CD163", "CD45RO", "PDL1", "MHC_II", "CD66b", "LAG3", "TIM3",
    "FoxP3", "CD4", "CTLA4", "Brachiury", "CD11c", "CD86", "CD8",
    "ERG", "S100", "PD1", "GranzymeB", "CD56", "CD3", "CD21", "CD10",
    "Ki67", "CD72a", "GATA3", "CD80", "aSMA"
]

print("Chosen nuclear markers:")
for marker in nuclear_markers:
    print(f"- {marker}")

print("\nChosen boundary-supporting markers:")
for marker in boundary_markers:
    print(f"- {marker}")

print("\nExample downstream quantification markers:")
for marker in quantification_markers[:12]:
    print(f"- {marker}")
print(f"... and {len(quantification_markers) - 12} more")

# %% [markdown]
# ## Why these channels?
#
# Here is the reasoning in plain language:
#
# - `DNA1` and `DNA2` are the most direct nuclear channels in this dataset.
#   They tell us where cells are centered.
# - `CD3`, `CD4`, `CD8` help outline lymphocytes.
# - `CD68` and `CD138` help recover macrophage-like and plasma-cell-rich areas.
# - `CD31` highlights vascular/endothelial structures.
# - `aSMA` highlights stromal or vessel-adjacent structure and can help define tissue boundaries.
#
# In a real IMC workflow, these channels are often combined into:
#
# - one **nuclear image**
# - one **membrane / boundary image**
#
# We will build those next as composite images so you can inspect what the segmentation
# algorithm would "see".

# %%
def load_marker(marker_name: str) -> np.ndarray:
    path = find_channel(marker_name)
    if path is None:
        raise FileNotFoundError(f"Marker not found in ROI: {marker_name}")
    return load_channel_image(path)


def average_normalized_markers(markers: list[str]) -> np.ndarray:
    images = [normalize_for_display(load_marker(marker)) for marker in markers]
    stacked = np.stack(images, axis=0)
    return stacked.mean(axis=0)


nuclear_composite = average_normalized_markers(nuclear_markers)
boundary_composite = average_normalized_markers(boundary_markers)

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes[0].imshow(nuclear_composite, cmap="gray")
axes[0].set_title("Nuclear Composite")
axes[0].axis("off")

axes[1].imshow(boundary_composite, cmap="gray")
axes[1].set_title("Boundary Composite")
axes[1].axis("off")

plt.tight_layout()
composite_path = OUTPUT_DIR / "step2_segmentation_composites.png"
plt.savefig(composite_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved segmentation composite figure to: {composite_path.resolve()}")

# %% [markdown]
# ## Build a color overlay for intuition
#
# A grayscale composite is useful, but for teaching and presentation a color overlay
# is often easier to understand.
#
# Here we create an RGB-style image where:
#
# - red = boundary-supporting signal
# - blue = nuclear signal
# - green = a mixed channel between nuclei and boundary signal
#
# This is **not** a biological stain. It is a visual teaching aid.

# %%
overlay = np.dstack([
    boundary_composite,
    0.5 * nuclear_composite + 0.5 * boundary_composite,
    nuclear_composite,
])
overlay = np.clip(overlay, 0, 1)

fig, ax = plt.subplots(figsize=(8, 8))
ax.imshow(overlay)
ax.set_title("Segmentation Guidance Overlay")
ax.axis("off")

plt.tight_layout()
overlay_path = OUTPUT_DIR / "step2_segmentation_overlay.png"
plt.savefig(overlay_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved segmentation overlay to: {overlay_path.resolve()}")

# %% [markdown]
# ## Step 2 takeaway
#
# We have now made the first important analytical decision in a reproducible way:
#
# - which channels will guide nuclei detection
# - which channels will help define cell boundaries
# - which markers we want to preserve for later biological interpretation
#
# This matters because segmentation is never magic. It depends directly on the
# channels you choose.
#
# In the next step, we should begin building a **simple segmentation strategy**.
# Since the full IMC stack is not installed here, the most realistic next move is:
#
# 1. detect nuclei from the DNA composite
# 2. create a first-pass cell mask around those nuclei
# 3. export a table of objects for this single ROI
#
# That will be our first transition from image-level analysis to cell-level analysis.

# %% [markdown]
# # Step 3: Build a first-pass nuclei segmentation
#
# This step is intentionally simple.
#
# We are **not** trying to reproduce a production-grade IMC segmentation model here.
# Instead, we want a segmentation procedure that is:
#
# - understandable
# - reproducible
# - good enough to teach the logic of the pipeline
#
# The basic idea is:
#
# 1. combine the DNA channels into one nuclear image
# 2. smooth the image a little to reduce pixel noise
# 3. threshold the image to keep bright nuclear regions
# 4. find connected components
# 5. remove tiny objects
# 6. compute object centroids and areas
#
# This gives us a **first-pass nuclei table** for the ROI.

# %%
from collections import deque
import csv
from PIL import ImageFilter


def smooth_image(image: np.ndarray, radius: float = 1.5) -> np.ndarray:
    pil_img = Image.fromarray(np.uint8(np.clip(image * 255, 0, 255)))
    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.array(blurred).astype(np.float32) / 255.0


def connected_components(binary_mask: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    """
    Very simple 8-connected component labeling.

    This is not optimized like scikit-image, but it is easy to explain and works
    well for a teaching pipeline on a single ROI.
    """
    height, width = binary_mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    components = []
    current_label = 0

    neighbors = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    for y in range(height):
        for x in range(width):
            if not binary_mask[y, x] or labels[y, x] != 0:
                continue

            current_label += 1
            queue = deque([(y, x)])
            labels[y, x] = current_label
            pixels = []

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


smoothed_nuclear = smooth_image(nuclear_composite, radius=1.2)
threshold_value = np.percentile(smoothed_nuclear, 96)
binary_nuclei = smoothed_nuclear > threshold_value

labels, components = connected_components(binary_nuclei)
print(f"Initial connected components: {len(components)}")
print(f"Threshold used (96th percentile): {threshold_value:.4f}")

# %% [markdown]
# ## Why use a percentile threshold?
#
# For this teaching version, we use a simple rule:
#
# - keep the brightest nuclear signal
# - drop the dim background
#
# That is what the percentile threshold is doing.
#
# This is not the only segmentation strategy, and it is not always the best one.
# But it is easy to understand and gives us a clean baseline.

# %%
min_nucleus_area = 20
filtered_components = [comp for comp in components if comp["area_pixels"] >= min_nucleus_area]

filtered_labels = np.zeros_like(labels)
for new_label, comp in enumerate(filtered_components, start=1):
    filtered_labels[labels == comp["label"]] = new_label
    comp["label"] = new_label

print(f"Components after area filtering (>= {min_nucleus_area} pixels): {len(filtered_components)}")

# %% [markdown]
# ## Visualize the segmentation result
#
# To make this easy to explain, we show three panels:
#
# 1. smoothed nuclear composite
# 2. binary threshold mask
# 3. filtered labeled objects
#
# This lets you show your colleague exactly how the first-pass segmentation was created.

# %%
display_labels = filtered_labels.astype(np.float32)
if display_labels.max() > 0:
    display_labels = display_labels / display_labels.max()

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

axes[0].imshow(smoothed_nuclear, cmap="gray")
axes[0].set_title("Smoothed Nuclear Composite")
axes[0].axis("off")

axes[1].imshow(binary_nuclei, cmap="gray")
axes[1].set_title("Binary Nuclear Mask")
axes[1].axis("off")

axes[2].imshow(display_labels, cmap="nipy_spectral")
axes[2].set_title("Filtered Nuclei Objects")
axes[2].axis("off")

plt.tight_layout()
segmentation_path = OUTPUT_DIR / "step3_first_pass_segmentation.png"
plt.savefig(segmentation_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved segmentation summary figure to: {segmentation_path.resolve()}")

# %% [markdown]
# ## Export a first-pass object table
#
# Each detected nucleus becomes one row in a CSV table.
#
# For now, we store:
#
# - object label
# - area
# - centroid coordinates
# - bounding box
#
# This is the beginning of the single-cell style table we will build later.

# %%
objects_csv = OUTPUT_DIR / "step3_nuclei_objects.csv"

with objects_csv.open("w", encoding="utf-8", newline="") as handle:
    fieldnames = [
        "label", "area_pixels", "centroid_y", "centroid_x",
        "min_y", "max_y", "min_x", "max_x"
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(filtered_components)

print(f"Saved nuclei object table to: {objects_csv.resolve()}")
print(f"Final nuclei count: {len(filtered_components)}")

# %% [markdown]
# ## Step 3 takeaway
#
# We now have the first real object-level output of the pipeline:
#
# - a visual segmentation result
# - a CSV table of detected nuclei-like objects
#
# This is the key transition from image analysis to object analysis.
#
# The next step should be:
#
# 1. measure marker intensities inside each detected object
# 2. attach those measurements to the object table
# 3. start building a per-object expression matrix for this ROI
#
# That will move us closer to the paper's cell-level analysis workflow.

# %% [markdown]
# # Step 4: Measure marker intensity per detected object
#
# We now have object locations from Step 3.
# The next question is:
#
# **what does each object express?**
#
# This is the key step that transforms segmentation output into a table that can
# later support phenotyping and spatial analysis.
#
# For each detected object, we will measure:
#
# - mean intensity for each selected marker
# - max intensity for a smaller subset of markers
# - basic metadata such as centroid and area
#
# The result will be a per-object expression table for this ROI.

# %%
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


pixel_map = object_pixels_from_labels(filtered_labels)
print(f"Number of labeled objects available for quantification: {len(pixel_map)}")

# %% [markdown]
# ## Choose a marker panel for quantification
#
# In a full IMC analysis, you would usually quantify nearly all biologically relevant channels.
# For teaching and first-pass analysis, it is often easier to start with a focused set.
#
# Here we measure a compact panel that spans:
#
# - lineage markers: `CD3`, `CD4`, `CD8`, `CD20`, `CD68`, `CD138`
# - immune state markers: `PD1`, `PDL1`, `LAG3`, `CTLA4`, `TIM3`
# - functional markers: `Ki67`, `GranzymeB`, `FoxP3`, `Tbet`
# - structural context markers: `CD31`, `aSMA`
#
# We also keep `DNA1` and `DNA2` so the object table remains anchored to the segmentation signal.

# %%
measurement_markers = [
    "DNA1", "DNA2",
    "CD3", "CD4", "CD8", "CD20", "CD68", "CD138",
    "CD56", "CD86", "MHC_II", "CD163", "CD45RO",
    "PD1", "PDL1", "LAG3", "CTLA4", "TIM3",
    "Ki67", "GranzymeB", "FoxP3", "Tbet",
    "CD31", "aSMA", "CD44", "CD47"
]

available_measurement_markers = [marker for marker in measurement_markers if find_channel(marker) is not None]

print("Markers selected for object-level quantification:")
for marker in available_measurement_markers:
    print(f"- {marker}")

# %% [markdown]
# ## Build the expression matrix
#
# Each row will represent one detected object.
# Each marker becomes a column.
#
# To keep this explainable, we use:
#
# - mean intensity across all pixels in the object
# - max intensity for selected markers as a second descriptive statistic
#
# Later, this table can be normalized or transformed, but for now we first want
# a raw measurement table.

# %%
marker_images = {marker: load_marker(marker) for marker in available_measurement_markers}
max_stat_markers = {"Ki67", "GranzymeB", "PD1", "PDL1", "LAG3", "CTLA4", "TIM3"}

expression_rows = []
component_lookup = {int(comp["label"]): comp for comp in filtered_components}

for label, pixels in sorted(pixel_map.items()):
    comp = component_lookup[label]
    row = {
        "object_label": label,
        "area_pixels": comp["area_pixels"],
        "centroid_y": comp["centroid_y"],
        "centroid_x": comp["centroid_x"],
        "roi_id": ROI_DIR.name,
    }

    for marker, image in marker_images.items():
        row[f"{marker}_mean"] = measure_marker_mean(image, pixels)
        if marker in max_stat_markers:
            row[f"{marker}_max"] = measure_marker_max(image, pixels)

    expression_rows.append(row)

print(f"Expression rows created: {len(expression_rows)}")
print(f"Columns in first row: {len(expression_rows[0]) if expression_rows else 0}")

# %% [markdown]
# ## Save the object expression table
#
# This CSV is the first file in the workflow that starts to resemble a true
# single-cell / single-object analysis table.
#
# It can later be used for:
#
# - normalization
# - thresholding
# - rough phenotyping
# - clustering
# - spatial annotation

# %%
expression_csv = OUTPUT_DIR / "step4_object_expression_table.csv"

fieldnames = list(expression_rows[0].keys()) if expression_rows else []
with expression_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(expression_rows)

print(f"Saved object expression table to: {expression_csv.resolve()}")

# %% [markdown]
# ## Inspect a few example objects
#
# Before moving on, it is important to sanity-check the table.
# We will print a small subset of columns so the values remain readable.

# %%
preview_columns = [
    "object_label", "area_pixels", "centroid_y", "centroid_x",
    "DNA1_mean", "DNA2_mean", "CD3_mean", "CD4_mean", "CD8_mean",
    "CD68_mean", "CD138_mean", "CD56_mean", "MHC_II_mean",
    "Ki67_mean", "PD1_mean", "PDL1_mean"
]

preview_columns = [col for col in preview_columns if col in fieldnames]

print("Preview of first 5 quantified objects:")
for row in expression_rows[:5]:
    print("-" * 40)
    for col in preview_columns:
        print(f"{col}: {row[col]}")

# %% [markdown]
# ## Step 4 takeaway
#
# We now have a first-pass per-object expression matrix for this ROI.
#
# That means we have completed the core transition:
#
# - from image files
# - to segmented objects
# - to object-level marker measurements
#
# This is the minimum structure needed before attempting phenotyping.
#
# The next step should be Step 5:
#
# 1. normalize or scale these marker values for comparability
# 2. define simple marker-based phenotyping rules
# 3. assign rough biological identities to objects
#
# That will be our first version of cell-type labeling for this single ROI.

# %% [markdown]
# # Step 5: First-pass phenotyping with simple marker rules
#
# We now have per-object marker measurements.
# The next question is:
#
# **can we assign an initial biological identity to each object?**
#
# In the paper, phenotyping is much more sophisticated and involves a combination of:
#
# - expert knowledge
# - marker thresholds
# - machine learning
# - refinement steps
#
# For this teaching notebook, we start with a simpler and fully explainable version:
#
# - compute marker positivity thresholds from the ROI itself
# - apply a small set of transparent if/then rules
# - assign rough labels
#
# These labels are not final truth. They are a first-pass annotation.

# %%
def percentile_threshold(rows: list[dict], column: str, percentile: float) -> float:
    values = [float(row[column]) for row in rows]
    return float(np.percentile(values, percentile))


phenotype_threshold_markers = [
    "CD3_mean", "CD4_mean", "CD8_mean", "CD20_mean", "CD68_mean", "CD138_mean",
    "CD31_mean", "aSMA_mean", "FoxP3_mean", "PD1_mean", "PDL1_mean",
    "CD56_mean", "CD86_mean", "MHC_II_mean", "CD163_mean", "CD45RO_mean",
    "GranzymeB_mean", "Tbet_mean"
]

high_thresholds = {
    column: percentile_threshold(expression_rows, column, 85)
    for column in phenotype_threshold_markers
    if column in expression_rows[0]
}

support_thresholds = {
    column: percentile_threshold(expression_rows, column, 75)
    for column in phenotype_threshold_markers
    if column in expression_rows[0]
}

print("Phenotyping high thresholds (85th percentile within this ROI):")
for column, value in high_thresholds.items():
    print(f"- {column}: {value:.3f}")

print("\nPhenotyping support thresholds (75th percentile within this ROI):")
for column, value in support_thresholds.items():
    print(f"- {column}: {value:.3f}")

# %% [markdown]
# ## Why use ROI-specific thresholds?
#
# For a single-ROI teaching workflow, ROI-specific thresholds are a practical way to start.
#
# The idea is:
#
# - values above the upper part of the within-ROI distribution are treated as "high"
# - those "high" signals can then support a label
#
# This is not as robust as cohort-level calibration, but it is easy to explain and
# works well for building intuition.

# %%
def is_high(row: dict, column: str) -> bool:
    return float(row.get(column, 0.0)) >= high_thresholds.get(column, float("inf"))


def is_supportive(row: dict, column: str) -> bool:
    return float(row.get(column, 0.0)) >= support_thresholds.get(column, float("inf"))


def assign_first_pass_label(row: dict) -> str:
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
    cd4_support = is_supportive(row, "CD4_mean")
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
    if cd20:
        return "B_cell_like"
    return "Unassigned"


for row in expression_rows:
    row["first_pass_label"] = assign_first_pass_label(row)

print("Assigned first-pass labels.")

# %% [markdown]
# ## Summarize the phenotype counts
#
# Before trusting any labels, we should inspect how many objects fall into each class.
#
# This is an important habit for reproducible analysis:
# always check label balance before interpreting biology.

# %%
label_counts = {}
for row in expression_rows:
    label = row["first_pass_label"]
    label_counts[label] = label_counts.get(label, 0) + 1

print("First-pass phenotype counts:")
for label, count in sorted(label_counts.items(), key=lambda item: (-item[1], item[0])):
    print(f"- {label}: {count}")

# %% [markdown]
# ## Save the phenotyped object table
#
# We now save an updated version of the object table that includes the new
# `first_pass_label` column.

# %%
phenotyped_csv = OUTPUT_DIR / "step5_object_expression_with_labels.csv"

phenotype_fieldnames = list(expression_rows[0].keys()) if expression_rows else []
with phenotyped_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=phenotype_fieldnames)
    writer.writeheader()
    writer.writerows(expression_rows)

print(f"Saved phenotyped object table to: {phenotyped_csv.resolve()}")

# %% [markdown]
# ## Visualize phenotype centroids on the ROI
#
# A simple centroid plot is a very useful teaching figure.
# It lets you show:
#
# - where the detected objects are
# - how the rough labels are distributed spatially
#
# This is not yet the paper's full spatial-neighborhood analysis, but it is the first
# spatial phenotype map.

# %%
label_colors = {
    "Plasma_like": "#d95f02",
    "Myeloid_like": "#1b9e77",
    "T_cell_CD8_like": "#7570b3",
    "T_cell_CD4_like": "#66a61e",
    "T_cell_other_like": "#4daf4a",
    "Treg_like": "#e7298a",
    "B_cell_like": "#e6ab02",
    "NK_like": "#984ea3",
    "Endothelial_like": "#1f78b4",
    "Stromal_like": "#a6761d",
    "Unassigned": "#666666",
}

fig, ax = plt.subplots(figsize=(8, 8))
ax.imshow(overlay, alpha=0.35)

for label, color in label_colors.items():
    xs = [row["centroid_x"] for row in expression_rows if row["first_pass_label"] == label]
    ys = [row["centroid_y"] for row in expression_rows if row["first_pass_label"] == label]
    if xs:
        ax.scatter(xs, ys, s=18, c=color, label=label, alpha=0.8, edgecolors="none")

ax.set_title("First-Pass Phenotype Map")
ax.set_xlim(0, overlay.shape[1])
ax.set_ylim(overlay.shape[0], 0)
ax.legend(loc="upper right", fontsize=8, frameon=True)
ax.axis("off")

plt.tight_layout()
phenotype_map_path = OUTPUT_DIR / "step5_first_pass_phenotype_map.png"
plt.savefig(phenotype_map_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved phenotype map to: {phenotype_map_path.resolve()}")

# %% [markdown]
# ## Step 5 takeaway
#
# We now have a first-pass biological annotation for this ROI.
#
# That means the pipeline has progressed from:
#
# - images
# - to segmented objects
# - to object-level expression
# - to rough phenotype labels
#
# This is already enough to support useful exploratory discussion.
#
# The next step should be Step 6:
#
# 1. normalize or transform marker intensities more formally
# 2. inspect phenotype-marker consistency
# 3. begin simple spatial interaction analysis between labeled objects
#
# That is where the workflow will start resembling the paper's spatial interpretation stage.

# %% [markdown]
# # Step 6: Simple spatial interaction analysis
#
# We now have rough phenotype labels and centroid coordinates.
# That means we can start asking spatial questions such as:
#
# - which phenotypes are near each other?
# - do some labels tend to cluster with themselves?
# - what is the nearest-neighbor composition of each phenotype?
#
# This is still a simplified version of the paper's spatial analysis.
# We are not yet building CellCharter neighborhoods or permutation-based enrichment.
# Instead, we start with the most explainable spatial unit:
#
# **the nearest labeled neighbor of each object**

# %%
def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return float(np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2))


def nearest_neighbor_indices(rows: list[dict]) -> list[int]:
    neighbors = []
    for i, row_i in enumerate(rows):
        best_j = None
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


nn_idx = nearest_neighbor_indices(expression_rows)
print(f"Computed nearest neighbors for {len(nn_idx)} objects.")

# %% [markdown]
# ## Attach nearest-neighbor information
#
# For each object, we record:
#
# - the nearest object label
# - the nearest object phenotype
# - the nearest-neighbor distance
#
# This gives us a simple object-level interaction table.

# %%
for i, j in enumerate(nn_idx):
    row_i = expression_rows[i]
    row_j = expression_rows[j]
    dist = euclidean_distance(
        float(row_i["centroid_x"]), float(row_i["centroid_y"]),
        float(row_j["centroid_x"]), float(row_j["centroid_y"]),
    )
    row_i["nearest_neighbor_label"] = row_j["object_label"]
    row_i["nearest_neighbor_type"] = row_j["first_pass_label"]
    row_i["nearest_neighbor_distance"] = dist

print("Attached nearest-neighbor information to all objects.")

# %% [markdown]
# ## Summarize phenotype-to-phenotype nearest-neighbor pairs
#
# This table is one of the most useful simple spatial summaries.
# It tells us, for example:
#
# - how often plasma-like objects have plasma-like nearest neighbors
# - how often myeloid-like objects sit nearest to T-cell-like objects
#
# This is not yet a formal enrichment test, but it is already a meaningful spatial description.

# %%
pair_counts = {}
for row in expression_rows:
    source = row["first_pass_label"]
    target = row["nearest_neighbor_type"]
    pair_counts[(source, target)] = pair_counts.get((source, target), 0) + 1

print("Top nearest-neighbor phenotype pairs:")
top_pairs = sorted(pair_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
for (source, target), count in top_pairs[:15]:
    print(f"- {source} -> {target}: {count}")

# %% [markdown]
# ## Mean nearest-neighbor distance by phenotype
#
# Another easy-to-explain spatial statistic is the average nearest-neighbor distance
# for each phenotype.
#
# Lower distances can suggest tighter packing, while larger distances can suggest
# more isolated objects.

# %%
distance_by_label = {}
for row in expression_rows:
    label = row["first_pass_label"]
    distance_by_label.setdefault(label, []).append(float(row["nearest_neighbor_distance"]))

mean_distance_by_label = {
    label: float(np.mean(distances))
    for label, distances in distance_by_label.items()
}

print("Mean nearest-neighbor distance by phenotype:")
for label, value in sorted(mean_distance_by_label.items(), key=lambda item: item[1]):
    print(f"- {label}: {value:.2f} pixels")

# %% [markdown]
# ## Save a spatial interaction table
#
# We now save a compact CSV table that can be used later for more formal analysis.

# %%
spatial_csv = OUTPUT_DIR / "step6_spatial_nearest_neighbor_table.csv"

spatial_fieldnames = list(expression_rows[0].keys()) if expression_rows else []
with spatial_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=spatial_fieldnames)
    writer.writeheader()
    writer.writerows(expression_rows)

print(f"Saved spatial nearest-neighbor table to: {spatial_csv.resolve()}")

# %% [markdown]
# ## Visualize nearest-neighbor links
#
# To make this intuitive, we draw a small sample of nearest-neighbor links on top
# of the phenotype map.
#
# We only show a subset of links so the plot remains readable.

# %%
rng = np.random.default_rng(42)
sample_size = min(80, len(expression_rows))
sample_indices = rng.choice(len(expression_rows), size=sample_size, replace=False)

fig, ax = plt.subplots(figsize=(8, 8))
ax.imshow(overlay, alpha=0.25)

for idx in sample_indices:
    row = expression_rows[idx]
    nn_label = row["nearest_neighbor_label"]
    nn_row = next(r for r in expression_rows if r["object_label"] == nn_label)
    x1, y1 = float(row["centroid_x"]), float(row["centroid_y"])
    x2, y2 = float(nn_row["centroid_x"]), float(nn_row["centroid_y"])
    ax.plot([x1, x2], [y1, y2], color="#444444", alpha=0.25, linewidth=0.8)

for label, color in label_colors.items():
    xs = [row["centroid_x"] for row in expression_rows if row["first_pass_label"] == label]
    ys = [row["centroid_y"] for row in expression_rows if row["first_pass_label"] == label]
    if xs:
        ax.scatter(xs, ys, s=16, c=color, label=label, alpha=0.85, edgecolors="none")

ax.set_title("Nearest-Neighbor Spatial Links")
ax.set_xlim(0, overlay.shape[1])
ax.set_ylim(overlay.shape[0], 0)
ax.axis("off")

plt.tight_layout()
nn_map_path = OUTPUT_DIR / "step6_nearest_neighbor_map.png"
plt.savefig(nn_map_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved nearest-neighbor map to: {nn_map_path.resolve()}")

# %% [markdown]
# ## Step 6 takeaway
#
# We now have the first simple spatial interaction layer for this ROI.
#
# That means we can describe not only what objects are present, but also how they are
# arranged relative to one another.
#
# This is still simpler than the paper's full neighborhood framework, but it gives us:
#
# - phenotype labels
# - nearest-neighbor identities
# - nearest-neighbor distances
# - a first phenotype-to-phenotype spatial summary
#
# The next step should be Step 7:
#
# 1. summarize marker expression by phenotype
# 2. compare phenotypes across markers
# 3. create presentation-ready summary plots and tables
#
# That will help turn the exploratory pipeline into something easier to communicate.

# %% [markdown]
# # Step 7: Summarize marker expression by phenotype
#
# We now want to answer a higher-level biological question:
#
# **how do the phenotypic groups differ in their marker expression?**
#
# This step is useful for two reasons:
#
# - it helps validate whether the rough labels make sense
# - it creates summary tables and figures that are much easier to present than raw object-level data
#
# For this teaching workflow, we will compute:
#
# - mean marker expression per phenotype
# - phenotype counts
# - a heatmap-like summary table
# - a few simple bar plots

# %%
def mean_by_group(rows: list[dict], group_key: str, value_keys: list[str]) -> list[dict]:
    groups = {}
    for row in rows:
        groups.setdefault(row[group_key], []).append(row)

    summary = []
    for group_name, group_rows in groups.items():
        out = {group_key: group_name, "n_objects": len(group_rows)}
        for key in value_keys:
            out[key] = float(np.mean([float(r[key]) for r in group_rows]))
        summary.append(out)
    return summary


summary_markers = [
    "CD3_mean", "CD4_mean", "CD8_mean", "CD20_mean", "CD68_mean", "CD138_mean",
    "CD56_mean", "CD86_mean", "MHC_II_mean", "CD163_mean", "CD45RO_mean",
    "PD1_mean", "PDL1_mean", "LAG3_mean", "CTLA4_mean", "TIM3_mean",
    "Ki67_mean", "GranzymeB_mean", "FoxP3_mean", "Tbet_mean",
    "CD31_mean", "aSMA_mean"
]
summary_markers = [m for m in summary_markers if m in expression_rows[0]]

phenotype_summary = mean_by_group(expression_rows, "first_pass_label", summary_markers)
phenotype_summary = sorted(phenotype_summary, key=lambda row: (-row["n_objects"], row["first_pass_label"]))

print(f"Number of phenotype groups summarized: {len(phenotype_summary)}")
for row in phenotype_summary:
    print(f"- {row['first_pass_label']}: {row['n_objects']} objects")

# %% [markdown]
# ## Save the phenotype summary table
#
# This table is much easier to discuss than the full object-level matrix.
# Each row is now one phenotype rather than one object.

# %%
phenotype_summary_csv = OUTPUT_DIR / "step7_phenotype_marker_summary.csv"

summary_fieldnames = list(phenotype_summary[0].keys()) if phenotype_summary else []
with phenotype_summary_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=summary_fieldnames)
    writer.writeheader()
    writer.writerows(phenotype_summary)

print(f"Saved phenotype summary table to: {phenotype_summary_csv.resolve()}")

# %% [markdown]
# ## Build a heatmap-style matrix
#
# To make differences across phenotypes easier to see, we create a scaled matrix.
#
# Here, each marker column is scaled between 0 and 1 across phenotypes.
# This does **not** change the underlying saved table. It only improves readability in the figure.

# %%
heatmap_labels = [row["first_pass_label"] for row in phenotype_summary]
heatmap_markers = summary_markers

heatmap_matrix = np.array([
    [float(row[marker]) for marker in heatmap_markers]
    for row in phenotype_summary
], dtype=np.float32)

scaled_heatmap = heatmap_matrix.copy()
for col in range(scaled_heatmap.shape[1]):
    column = scaled_heatmap[:, col]
    col_min = float(np.min(column))
    col_max = float(np.max(column))
    if col_max > col_min:
        scaled_heatmap[:, col] = (column - col_min) / (col_max - col_min)
    else:
        scaled_heatmap[:, col] = 0.0

fig, ax = plt.subplots(figsize=(14, 6))
im = ax.imshow(scaled_heatmap, aspect="auto", cmap="YlGnBu")
ax.set_xticks(range(len(heatmap_markers)))
ax.set_xticklabels([m.replace("_mean", "") for m in heatmap_markers], rotation=60, ha="right")
ax.set_yticks(range(len(heatmap_labels)))
ax.set_yticklabels(heatmap_labels)
ax.set_title("Phenotype Marker Summary (Column-scaled)")
plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
plt.tight_layout()

heatmap_path = OUTPUT_DIR / "step7_phenotype_marker_heatmap.png"
plt.savefig(heatmap_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved phenotype heatmap to: {heatmap_path.resolve()}")

# %% [markdown]
# ## Create simple presentation bar plots
#
# We create two straightforward plots:
#
# - phenotype counts
# - mean nearest-neighbor distance by phenotype
#
# These are often the easiest summary visuals to present in a short meeting.

# %%
count_labels = [row["first_pass_label"] for row in phenotype_summary]
count_values = [row["n_objects"] for row in phenotype_summary]

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(count_labels, count_values, color="#4C7A67")
ax.set_title("Object Counts by First-Pass Phenotype")
ax.set_ylabel("Number of objects")
ax.set_xticks(range(len(count_labels)))
ax.set_xticklabels(count_labels, rotation=45, ha="right")
plt.tight_layout()

count_plot_path = OUTPUT_DIR / "step7_phenotype_counts.png"
plt.savefig(count_plot_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved phenotype count plot to: {count_plot_path.resolve()}")

# %%
distance_labels = list(mean_distance_by_label.keys())
distance_values = [mean_distance_by_label[label] for label in distance_labels]

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(distance_labels, distance_values, color="#7A5C61")
ax.set_title("Mean Nearest-Neighbor Distance by Phenotype")
ax.set_ylabel("Distance (pixels)")
ax.set_xticks(range(len(distance_labels)))
ax.set_xticklabels(distance_labels, rotation=45, ha="right")
plt.tight_layout()

distance_plot_path = OUTPUT_DIR / "step7_mean_nn_distance_by_phenotype.png"
plt.savefig(distance_plot_path, dpi=150, bbox_inches="tight")
plt.close(fig)

print(f"Saved nearest-neighbor distance plot to: {distance_plot_path.resolve()}")

# %% [markdown]
# ## Step 7 takeaway
#
# We now have a phenotype-level summary layer for this ROI.
#
# That means the notebook now supports three levels of interpretation:
#
# - object level
# - spatial relationship level
# - phenotype summary level
#
# This is a strong point for presenting the workflow, because you can move from
# raw images to interpretable phenotype summaries in a reproducible sequence.
#
# If we continue, the next step could be one of two directions:
#
# 1. **refinement direction**
#    Improve segmentation and phenotyping so the labels are more biologically reliable.
#
# 2. **paper-like spatial direction**
#    Build more advanced neighborhood-style analyses that move closer to the paper's methodology.
#
# For a single ROI, I would recommend refinement first, then neighborhood analysis.

# %% [markdown]
# # Final Summary For Presentation
#
# This section is meant to help you present the pipeline to a colleague.
#
# It answers four practical questions:
#
# 1. What data did we start with?
# 2. What analysis steps did we perform?
# 3. What did we produce?
# 4. What are the current limitations?

# %%
final_summary_lines = [
    f"ROI analyzed: {ROI_DIR.name}",
    f"Number of channel images: {len(channel_files)}",
    f"Image size: {unique_shapes[0][0]} x {unique_shapes[0][1]} pixels" if unique_shapes else "Image size: unknown",
    f"Detected first-pass nuclei-like objects: {len(filtered_components)}",
    f"Phenotype groups identified: {len(phenotype_summary)}",
    f"Most abundant phenotype: {phenotype_summary[0]['first_pass_label']} ({phenotype_summary[0]['n_objects']} objects)" if phenotype_summary else "Most abundant phenotype: unavailable",
]

print("Presentation summary:")
for line in final_summary_lines:
    print(f"- {line}")

# %% [markdown]
# ## Pipeline recap
#
# The workflow we built for this single ROI is:
#
# 1. read all ROI channel TIFFs
# 2. verify image alignment and inspect marker content
# 3. choose channels for segmentation
# 4. generate a first-pass nuclei segmentation
# 5. quantify marker intensities per object
# 6. assign first-pass phenotypes with transparent rules
# 7. compute simple nearest-neighbor spatial summaries
# 8. summarize marker expression by phenotype
#
# This is already a reproducible, explainable single-ROI pipeline.

# %% [markdown]
# ## Current limitations
#
# To present this responsibly, it is important to state what this notebook does **not** yet do:
#
# - segmentation is a simple baseline, not a production IMC segmentation model
# - phenotyping uses rough ROI-specific thresholds, not cohort-trained classification
# - spatial analysis uses nearest neighbors only, not formal neighborhood enrichment
# - this notebook analyzes one ROI only, so it cannot support cohort-level conclusions
#
# These are not failures. They simply define the current scope.

# %% [markdown]
# ## What To Say In A Meeting
#
# A short presentation version could be:
#
# "We started from one extracted IMC ROI composed of 43 aligned channel TIFFs.
# We built a reproducible notebook that inspects the ROI, creates a first-pass
# nuclei segmentation, quantifies marker intensity per object, assigns rough
# biological labels, and summarizes simple spatial relationships. This gives us
# an explainable single-ROI analysis workflow that can now be refined or scaled
# to additional ROIs."

# %%
presentation_note_path = OUTPUT_DIR / "final_presentation_summary.txt"
with presentation_note_path.open("w", encoding="utf-8") as handle:
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

print(f"Saved presentation summary note to: {presentation_note_path.resolve()}")
