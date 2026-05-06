# IMC ROI Interface Design

This guide describes the intended interface for an easier, more explainable ROI workflow.

## Primary Users

- researchers who are comfortable with biology but not necessarily with code
- collaborators who need a reproducible ROI workflow
- teams analyzing IMC sarcoma microenvironment data ROI-by-ROI

## User Inputs The Interface Should Ask For

The interface should ask the user for:

1. ROI folder path
2. output folder
3. analysis preset
4. nuclei markers
5. boundary markers
6. markers to quantify
7. segmentation sensitivity controls
8. phenotyping threshold controls

These are the minimum inputs needed to make the analysis flexible across ROI panels.

## Recommended Layout

### Sidebar

- ROI folder path
- output folder
- preset selector

### Main Tabs

- `Configuration`
- `Run`
- `Results`
- `Design Notes`

## Presets

The app should support presets such as:

- `generic_imc`
- `sarcoma_microenvironment`

The sarcoma preset should preload likely useful markers like:

- DNA channels
- immune markers
- structural markers
- sarcoma-relevant markers such as `ERG`, `S100`, `Brachiury`, `aSMA`

## Results The Interface Should Show

At minimum:

- number of channels found
- segmentation object count
- phenotype counts
- path to output folder
- a downloadable presentation summary

## Why This Design Works

- it reduces user burden
- it keeps the workflow explainable
- it supports both beginners and advanced users
- it makes the backend reusable for different ROI folders

## Backend Architecture

The backend should stay separate from the UI.

That backend should expose reusable stages:

1. inspection
2. composite generation
3. segmentation
4. quantification
5. phenotyping
6. spatial analysis
7. summary generation

This makes it possible to drive the same backend from:

- Streamlit
- a notebook
- a CLI
- a future lab-facing dashboard
