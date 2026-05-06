# IMC Data Analysis Pipeline: Workable Implementation Guide

This guide turns the paper's `Data analysis` section into something you can actually build.

## What You Are Really Trying To Build

The paper's workflow has 3 layers:

1. Image processing
2. Single-cell labeling
3. Spatial and clinical analysis

The easiest way to implement it is to treat those as separate deliverables instead of one giant script.

## The Practical Architecture

Use this folder structure:

```text
project/
  raw_mcd/
  annotations/
  tables/
  models/
  results/
  config.json
```

Use the starter script in this folder:

`python imc_pipeline_starter.py init --root ./project`

That creates the folder layout and a `config.json` you can edit.

## Step 1: Preprocess Raw IMC Files

### Goal

Convert raw `.mcd` files into segmented single-cell tables.

### What the paper did

- Steinbock for preprocessing
- hot-pixel filter = 50
- MESMER for segmentation
- nuclear channels: `HistoneH3`, `191Ir`, `193Ir`
- membrane channels: `CD98`, `CD3`, `CD138`, `CD45`
- export single-cell features

### What you need

- raw `.mcd` files
- the panel/channel metadata
- a place to store segmentation masks and cell tables

### How to implement it

Run this stage outside the starter script using Steinbock.

Expected output:

- one segmentation mask per ROI
- one cell table per ROI or one merged cell table

Minimum columns you want in the output table:

- `patient_id`
- `roi_id`
- `cell_id`
- `cell_area`
- marker intensity columns such as `CD3`, `CD8`, `CD45`, `CD138`, `IRF4`
- centroid coordinates if available, like `x` and `y`

### Why this step matters

Everything downstream depends on the cell table being correct. If segmentation is poor, the rest of the pipeline becomes noisy.

## Step 2: Add Tissue Context

### Goal

Tell the pipeline where bone is and which regions should be excluded.

### What the paper did

- manually annotated bone in QuPath using neighboring H&E sections
- computed distance from each cell to nearest bone surface
- annotated artifact regions in Napari
- excluded cells in artifact regions

### What you need

- bone annotations exported from QuPath
- optional artifact annotations
- cell coordinates from the segmentation output

### How to implement it

Create exported annotation files in `project/annotations/`.

At minimum, keep:

- `bone_annotations.*`
- `artifact_annotations.*`

Then write a small converter that:

1. turns polygons into masks or geometry objects
2. maps each cell centroid to distance from bone
3. flags cells that fall inside artifact polygons

### Workable shortcut

If you are just starting, skip full polygon math and begin with a CSV that already contains:

- `cell_id`
- `distance_to_bone`
- `is_artifact`

Then merge that onto your cell table before downstream analysis.

## Step 3: Clean and Normalize the Single-Cell Table

### Goal

Make marker values comparable across cells and ROIs.

### What the paper did

- removed cells with area smaller than 4 pixels
- clipped each marker to the 99th percentile
- applied `arcsinh(x / 1)`
- CLR-normalized each cell

### What you need

- a merged cell table from Step 1

### How to implement it now

Put your labeled table at:

`project/tables/cells_training.csv`

Edit `config.json` so the marker names match your real columns.

Then run:

```bash
python imc_pipeline_starter.py normalize --config ./project/config.json
```

### What the script does

- filters by `cell_area >= 4`
- clips markers at the 99th percentile
- applies arcsinh transform
- applies CLR across the marker columns
- writes `project/tables/cells_normalized.csv`

## Step 4: Build Cell-Type Labels

### Goal

Assign biologically meaningful labels to each cell.

### What the paper did

- batch-corrected cells
- built expert-guided labels with SCIMAP
- trained XGBoost
- refined uncertain populations with FlowSOM and marker rules
- visually checked final labels

### How to implement this in a practical first version

Do it in 2 passes.

#### Pass A: Build a trusted training set

Prepare `project/tables/cells_training.csv` with:

- normalized marker columns
- a `cell_type` column for cells you have manually labeled

Start with a limited set of major classes:

- Plasma_Cell
- T_Cell
- Myeloid
- B_Cell
- Stromal
- Endothelial
- Unknown

#### Pass B: Train a classifier

Run:

```bash
python imc_pipeline_starter.py train-classifier --config ./project/config.json
```

This starter script uses a simple centroid classifier, not XGBoost. That is intentional:

- it is easy to understand
- it gives you a working baseline
- you can later replace it with XGBoost without changing the rest of the pipeline

### Predict on new cells

Place unannotated cells in:

`project/tables/cells_unlabeled.csv`

Run:

```bash
python imc_pipeline_starter.py predict --config ./project/config.json
```

Output:

`project/results/cells_predicted.csv`

### Recommended upgrade after baseline works

Replace the centroid model with:

- XGBoost
- LightGBM
- RandomForest

Only do that after you trust the labels and features.

## Step 5: Summarize Per ROI and Per Patient

### Goal

Reduce cell-level predictions into ROI-level and patient-level quantities.

### Why this matters

The paper avoids naive single-cell statistical testing when the unit of interest is actually the patient or ROI.

### Implement it now

Run:

```bash
python imc_pipeline_starter.py summarize-rois --config ./project/config.json
```

This computes per-ROI cell-type counts and fractions.

Output:

`project/results/roi_summary.csv`

Use this as the starting point for:

- comparing patients
- building survival models
- checking class balance

## Step 6: Spatial Neighborhood Analysis

### Goal

Capture local microenvironments, not just isolated cell types.

### What the paper did

- dimensionality reduction with trVAE
- Delaunay neighbor graph with Squidpy
- aggregate neighbor features across 3 layers
- CellCharter clustering
- selected `n_clusters = 9`
- measured enrichments and connected components

### How to implement this for real

This part should be a dedicated notebook or script, separate from the normalization/classifier pipeline.

Required inputs:

- predicted cell types
- marker features
- cell coordinates
- ROI identifiers

Recommended implementation order:

1. build a spatial neighbor graph from cell centroids
2. verify the graph visually on a few ROIs
3. compute neighborhood composition features
4. cluster those features into neighborhoods
5. inspect marker and cell-type enrichment per neighborhood

### Important advice

Do not start with 9 neighborhoods just because the paper used 9.
First verify whether your dataset supports that number.

## Step 7: Colocalization and Neighbor Preference

### Goal

Measure who prefers to sit next to whom.

### What the paper did

- COZI
- permutation-based z-scores
- directional preference scores

### Workable first version

Before reproducing COZI exactly, compute a simpler baseline:

1. identify neighbors from the graph
2. count cell-type pair frequencies
3. compare observed counts to shuffled label counts
4. convert to z-scores

If that works and matches intuition, then move to the full COZI implementation.

## Step 8: Survival and Cohort Analysis

### Goal

Link spatial features to progression-free survival.

### What the paper did

- split patients into short vs. long PFS
- Kaplan-Meier
- log-rank optimization
- elastic-net Cox regression

### Workable implementation

Build one patient-level table where each row is a patient and columns are:

- clinical covariates
- cell-type fractions
- neighborhood scores
- colocalization scores
- PFS time
- event indicator

Then run:

1. univariate screening
2. Kaplan-Meier for top candidates
3. multivariable Cox model

### Best practice

Keep the patient as the statistical unit whenever you are asking a clinical question.

## What To Build First

Do not try to reproduce the whole paper at once.

Build in this order:

1. a clean merged single-cell table
2. normalization
3. a small trusted training set
4. cell-type prediction
5. ROI-level summaries
6. neighbor graph
7. neighborhood clustering
8. patient-level outcome models

## The Minimal Workable Version

If you want the shortest path to something useful, do this:

1. run external segmentation and export one merged cell table
2. add `patient_id`, `roi_id`, `cell_area`, and marker columns
3. create 500 to 2,000 manually labeled cells
4. normalize with the starter script
5. train the classifier
6. predict labels for all cells
7. summarize fractions per ROI
8. inspect results before attempting spatial modeling

That gives you a usable first-generation pipeline.

## What The Starter Script Handles Today

The script in this folder already handles:

- project initialization
- config generation
- single-cell filtering
- marker clipping
- arcsinh transform
- CLR normalization
- a baseline cell-type classifier
- prediction on unannotated cells
- ROI-level cell-type summaries

## What You Still Need To Add

You still need tool-specific implementations for:

- Steinbock preprocessing
- MESMER segmentation
- QuPath bone annotations
- artifact polygon filtering
- Scanorama batch correction
- SCIMAP rule-based labeling
- FlowSOM refinement
- Squidpy neighbor graphs
- CellCharter neighborhood clustering
- COZI interaction scoring
- Kaplan-Meier and Cox modeling

## Honest Recommendation

The best implementation strategy is:

- use the starter script as the data backbone
- keep image and spatial tooling in separate scripts or notebooks
- validate each stage with tiny subsets before scaling up

That will save you a lot of time.
