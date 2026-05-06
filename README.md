# IMC Sarcoma Analysis Workspace

This repository contains an interactive and notebook-driven workflow for Imaging Mass Cytometry analysis, developed around sarcoma microenvironment use cases.

## Main components

- `agent_imc/`
  Packaged Streamlit application for single-ROI and batch-ROI analysis, including a lightweight copilot and report generator.
- `paper_based_workflow/`
  Stepwise notebooks for reproducing a paper-based Steinbock + MESMER workflow with explicit documentation of any channel adaptations.
- `eccb_poster/`
  ECCB 2026 abstract and submission-preparation materials.
- `roi001_d13_notebook.py` and `roi001_d13_notebook.ipynb`
  Guided notebook versions of the exploratory single-ROI workflow.

## What is intentionally excluded

The repository is configured to exclude:

- raw ROI TIFF folders
- generated outputs and masks
- local virtual environments
- local plotting caches
- large local reference PDFs

This keeps the GitHub repository lightweight and focused on reproducible code, notebooks, and documentation.

## Running the app

```bash
cd agent_imc
MPLCONFIGDIR=/absolute/path/to/.matplotlib ../.venv/bin/streamlit run imc_roi_app.py --server.headless true --server.port 8506
```

## Notes

The paper-based workflow is structured as explicit stop points between major stages so segmentation, measurement, and downstream biological interpretation can each be reviewed before proceeding.
