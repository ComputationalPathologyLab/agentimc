# agent_imc

This folder is a self-contained workspace for interactive IMC ROI analysis.

## Layout

- `inputs/`
  Put one or more ROI folders here.
- `outputs/`
  Pipeline outputs are generated here automatically.
- `configs/`
  Saved run configurations.
- `imc_roi_backend.py`
  Reusable pipeline backend.
- `imc_roi_app.py`
  Streamlit interface with single-ROI, batch-ROI, results, and copilot tabs.
- `imc_copilot.py`
  Lightweight analysis copilot and report generator grounded in ROI outputs.
- `roi_template_notebook.py`
  Reusable notebook template.

## Default Behavior

- Single ROI mode defaults to `inputs/ROI001_D13`
- Batch mode defaults to `inputs/`
- Outputs go to `outputs/<roi_name>/`
- The copilot can answer ROI questions and generate ROI or batch text reports

## Launch

From the parent project folder:

```bash
cd /Users/rashid/1_IMC_Analysis/11_Vincenzo/agent_imc
MPLCONFIGDIR=/Users/rashid/1_IMC_Analysis/11_Vincenzo/.matplotlib ../.venv/bin/streamlit run imc_roi_app.py --server.headless true --server.port 8504
```
