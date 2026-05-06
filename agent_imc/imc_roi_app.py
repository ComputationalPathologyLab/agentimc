from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
except ImportError:
    st = None

from imc_roi_backend import (
    APP_HOME,
    INPUTS_DIR,
    IMCROIAnalyzer,
    PRESET_CONFIGS,
    collect_output_files,
    config_from_preset,
    run_batch_pipeline,
)
from imc_copilot import answer_roi_query, generate_batch_report, generate_roi_report


def parse_csv_text(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def make_config(
    roi_dir: str,
    output_dir: str,
    preset: str,
    nuclei_markers: str,
    boundary_markers: str,
    measurement_markers: str,
    blur_radius: float,
    threshold_percentile: float,
    min_area: int,
    high_percentile: float,
    support_percentile: float,
):
    config = config_from_preset(roi_dir=roi_dir, preset_name=preset)
    if output_dir.strip():
        config.output_dir = output_dir.strip()
    config.nuclei_markers = parse_csv_text(nuclei_markers)
    config.boundary_markers = parse_csv_text(boundary_markers)
    config.measurement_markers = parse_csv_text(measurement_markers)
    config.segmentation_blur_radius = blur_radius
    config.segmentation_threshold_percentile = threshold_percentile
    config.min_nucleus_area = min_area
    config.phenotype_high_percentile = high_percentile
    config.phenotype_support_percentile = support_percentile
    return config


def render_output_group(output_dir: Path, outputs: dict[str, list[Path]]) -> None:
    st.write("Output directory")
    st.code(str(output_dir))

    st.subheader("Image Previews")
    if outputs["images"]:
        selected_image = st.selectbox(
            "Choose an image output",
            options=[path.name for path in outputs["images"]],
            key=f"image_select_{output_dir.name}",
        )
        image_path = next(path for path in outputs["images"] if path.name == selected_image)
        st.image(str(image_path), caption=image_path.name, use_container_width=True)
        st.download_button(
            label=f"Download {image_path.name}",
            data=image_path.read_bytes(),
            file_name=image_path.name,
            mime="image/png",
            key=f"download_image_{image_path.name}",
        )
    else:
        st.info("No image outputs found.")

    st.subheader("Downloadable Tables")
    if outputs["tables"]:
        for path in outputs["tables"]:
            st.download_button(
                label=f"Download {path.name}",
                data=path.read_bytes(),
                file_name=path.name,
                mime="text/csv",
                key=f"download_table_{output_dir.name}_{path.name}",
            )
    else:
        st.info("No tables found.")

    st.subheader("Text Outputs")
    if outputs["texts"]:
        selected_text = st.selectbox(
            "Choose a text output",
            options=[path.name for path in outputs["texts"]],
            key=f"text_select_{output_dir.name}",
        )
        text_path = next(path for path in outputs["texts"] if path.name == selected_text)
        st.text_area("Preview", value=text_path.read_text(encoding="utf-8"), height=220, key=f"preview_{text_path.name}")
        st.download_button(
            label=f"Download {text_path.name}",
            data=text_path.read_text(encoding="utf-8"),
            file_name=text_path.name,
            mime="text/plain",
            key=f"download_text_{output_dir.name}_{text_path.name}",
        )
    else:
        st.info("No text outputs found.")


def app() -> None:
    st.set_page_config(page_title="IMC ROI Analyzer", layout="wide")
    st.title("IMC ROI Analyzer")
    st.caption("Interactive single-ROI IMC analysis for sarcoma microenvironment and related panels.")
    default_single_roi = str(INPUTS_DIR / "ROI001_D13")
    default_batch_parent = str(INPUTS_DIR)

    with st.sidebar:
        st.header("Inputs")
        mode = st.radio("Run mode", ["Single ROI", "Batch ROI"], index=0)
        roi_dir = st.text_input("ROI folder path", value=default_single_roi)
        batch_parent_dir = st.text_input("Batch parent folder", value=default_batch_parent)
        output_dir = st.text_input("Output folder", value="")
        preset = st.selectbox("Preset", list(PRESET_CONFIGS.keys()), index=list(PRESET_CONFIGS.keys()).index("sarcoma_microenvironment"))

    base_config = config_from_preset(roi_dir=roi_dir, preset_name=preset)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Configuration", "Run", "Results", "Copilot", "Design Notes"])

    with tab1:
        st.subheader("Marker Roles")
        nuclei_markers = st.text_input("Nuclei markers (comma-separated)", value=", ".join(base_config.nuclei_markers))
        boundary_markers = st.text_input("Boundary markers (comma-separated)", value=", ".join(base_config.boundary_markers))
        measurement_markers = st.text_area("Measurement markers (comma-separated)", value=", ".join(base_config.measurement_markers), height=160)

        st.subheader("Segmentation")
        blur_radius = st.slider("Blur radius", 0.5, 3.0, float(base_config.segmentation_blur_radius), 0.1)
        threshold_percentile = st.slider("Segmentation threshold percentile", 85.0, 99.5, float(base_config.segmentation_threshold_percentile), 0.5)
        min_area = st.slider("Minimum nucleus area", 5, 100, int(base_config.min_nucleus_area), 1)

        st.subheader("Phenotyping")
        high_percentile = st.slider("High threshold percentile", 70.0, 95.0, float(base_config.phenotype_high_percentile), 1.0)
        support_percentile = st.slider("Support threshold percentile", 55.0, 90.0, float(base_config.phenotype_support_percentile), 1.0)

    with tab2:
        st.subheader("Pipeline Execution")
        st.write("Run one ROI or a whole folder of ROI subdirectories using the same backend.")

        single_config = make_config(
            roi_dir,
            output_dir,
            preset,
            nuclei_markers,
            boundary_markers,
            measurement_markers,
            blur_radius,
            threshold_percentile,
            min_area,
            high_percentile,
            support_percentile,
        )

        if mode == "Single ROI":
            if st.button("Run Single ROI Pipeline", type="primary"):
                analyzer = IMCROIAnalyzer(single_config)
                with st.spinner("Running single ROI pipeline..."):
                    results = analyzer.run_full_pipeline()
                    outputs = collect_output_files(analyzer.output_dir)
                st.session_state["last_run_mode"] = "single"
                st.session_state["single_run"] = {
                    "roi_name": analyzer.roi_dir.name,
                    "output_dir": str(analyzer.output_dir),
                    "results": results,
                    "outputs": outputs,
                }
                st.success("Single ROI pipeline finished.")
        else:
            subdirs = sorted([path for path in Path(batch_parent_dir).expanduser().resolve().iterdir() if path.is_dir()])
            default_selection = [path.name for path in subdirs if any(path.glob("*.tiff")) or any(path.glob("*.tif"))]
            selected = st.multiselect("ROI folders to run", options=[p.name for p in subdirs], default=default_selection)
            if st.button("Run Batch ROI Pipeline", type="primary"):
                configs = []
                for name in selected:
                    roi_path = str((Path(batch_parent_dir).expanduser().resolve() / name))
                    cfg = make_config(
                        roi_path,
                        "",
                        preset,
                        nuclei_markers,
                        boundary_markers,
                        measurement_markers,
                        blur_radius,
                        threshold_percentile,
                        min_area,
                        high_percentile,
                        support_percentile,
                    )
                    configs.append(cfg)
                with st.spinner("Running batch ROI pipeline..."):
                    batch_results = run_batch_pipeline(configs)
                st.session_state["last_run_mode"] = "batch"
                st.session_state["batch_run"] = batch_results
                st.success(f"Batch pipeline finished for {len(batch_results)} ROI folders.")

    with tab3:
        st.subheader("Results")
        last_mode = st.session_state.get("last_run_mode")
        if last_mode == "single" and "single_run" in st.session_state:
            run = st.session_state["single_run"]
            inspection = run["results"]["inspection"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Channels", inspection["n_channel_files"])
            col2.metric("Objects", run["results"]["segmentation"]["filtered_components"])
            col3.metric("Phenotypes", len(run["results"]["phenotyping"]["label_counts"]))
            st.write("Phenotype counts")
            st.json(run["results"]["phenotyping"]["label_counts"])
            render_output_group(Path(run["output_dir"]), run["outputs"])
        elif last_mode == "batch" and "batch_run" in st.session_state:
            batch_results = st.session_state["batch_run"]
            st.write(f"Completed ROIs: {len(batch_results)}")
            selected_roi = st.selectbox("Choose ROI results", options=[item["roi_name"] for item in batch_results])
            item = next(entry for entry in batch_results if entry["roi_name"] == selected_roi)
            inspection = item["results"]["inspection"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Channels", inspection["n_channel_files"])
            col2.metric("Objects", item["results"]["segmentation"]["filtered_components"])
            col3.metric("Phenotypes", len(item["results"]["phenotyping"]["label_counts"]))
            st.write("Phenotype counts")
            st.json(item["results"]["phenotyping"]["label_counts"])
            render_output_group(Path(item["output_dir"]), item["outputs"])
        else:
            st.info("Run a single ROI or batch job first to populate this tab.")

    with tab4:
        st.subheader("ROI Copilot")
        st.write("Ask grounded questions about a completed ROI analysis, or generate a short report.")

        last_mode = st.session_state.get("last_run_mode")
        if last_mode == "single" and "single_run" in st.session_state:
            run = st.session_state["single_run"]
            output_dir_path = Path(run["output_dir"])
            prompt = st.text_input(
                "Ask a question about this ROI",
                value="What are the dominant phenotypes in this ROI?",
                key="single_copilot_prompt",
            )
            col_a, col_b = st.columns(2)
            if col_a.button("Answer Question", key="single_answer_btn"):
                st.text_area("Copilot answer", value=answer_roi_query(output_dir_path, prompt), height=260)
            if col_b.button("Generate ROI Report", key="single_report_btn"):
                report = generate_roi_report(output_dir_path)
                st.text_area("ROI report", value=report, height=320)
                st.download_button(
                    label="Download ROI report",
                    data=report,
                    file_name=f"{output_dir_path.name}_copilot_report.txt",
                    mime="text/plain",
                    key="single_report_download",
                )
        elif last_mode == "batch" and "batch_run" in st.session_state:
            batch_results = st.session_state["batch_run"]
            options = [item["roi_name"] for item in batch_results]
            selected_roi = st.selectbox("Choose ROI for question answering", options=options, key="batch_copilot_roi")
            item = next(entry for entry in batch_results if entry["roi_name"] == selected_roi)
            output_dir_path = Path(item["output_dir"])
            prompt = st.text_input(
                "Ask a question about the selected ROI",
                value="Summarize the spatial interactions in this ROI.",
                key="batch_copilot_prompt",
            )
            col_a, col_b = st.columns(2)
            if col_a.button("Answer ROI Question", key="batch_answer_btn"):
                st.text_area("Copilot answer", value=answer_roi_query(output_dir_path, prompt), height=260)
            if col_b.button("Generate Batch Report", key="batch_report_btn"):
                report = generate_batch_report([entry["output_dir"] for entry in batch_results])
                st.text_area("Batch report", value=report, height=320)
                st.download_button(
                    label="Download batch report",
                    data=report,
                    file_name="batch_copilot_report.txt",
                    mime="text/plain",
                    key="batch_report_download",
                )
        else:
            st.info("Run a single ROI or batch job first, then use the copilot on the generated outputs.")

    with tab5:
        st.subheader("Interface Design Goals")
        st.code(f"Workspace root: {APP_HOME}")
        st.markdown(
            """
            - Ask only the inputs users actually know: ROI folder, marker roles, and a few thresholds.
            - Keep every stage visible: inspection, segmentation, quantification, phenotyping, spatial analysis.
            - Support presets for domain-specific panels such as sarcoma microenvironment IMC.
            - Make all outputs exportable for presentation and reproducibility.
            - Let advanced users override defaults without forcing new users to understand every parameter first.
            """
        )


if __name__ == "__main__":
    if st is None:
        print("This app uses Streamlit, which is not installed in this environment.")
        print("Install it with: python3 -m pip install streamlit")
        print("Then run: streamlit run imc_roi_app.py")
    else:
        app()
