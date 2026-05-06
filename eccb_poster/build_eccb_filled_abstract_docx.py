from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


OUT_PATH = Path("/Users/rashid/1_IMC_Analysis/11_Vincenzo/eccb_poster/ECCB_2026_filled_abstract.docx")

TITLE = "AgentIMC: An Interactive Workflow for Imaging Mass Cytometry Analysis of the Sarcoma Microenvironment"
ABSTRACT = (
    "Imaging mass cytometry enables high-dimensional, spatially resolved characterization of the tumor microenvironment, "
    "but its broader adoption remains constrained by fragmented computational workflows and limited accessibility for end "
    "users. We present AgentIMC, a reproducible framework for imaging mass cytometry analysis developed for sarcoma "
    "microenvironment studies and adaptable to other antibody panels. Starting from ROI-level TIFF channels, the workflow "
    "performs channel inspection, segmentation-oriented marker selection, nuclei segmentation, object-level marker "
    "quantification, phenotype assignment, spatial nearest-neighbor analysis, and phenotype-level summarization. To support "
    "practical use, we coupled the analysis backend to an interactive interface for both single-ROI and batch-ROI "
    "processing, with configurable marker roles, visual quality-control outputs, downloadable result tables, and automated "
    "report generation from the derived analyses. In a sarcoma imaging mass cytometry dataset, the workflow identified "
    "biologically meaningful cellular populations, including myeloid-like, B-cell-like, plasma-like, stromal-like, "
    "endothelial-like, and T-cell-like compartments, while preserving a consistent and auditable analysis structure across "
    "processing stages. AgentIMC is designed to reduce technical barriers in exploratory and translational imaging mass "
    "cytometry studies by combining standardized processing, interpretable spatial summaries, and presentation-ready outputs "
    "within a unified environment. This framework supports reproducible characterization of imaging-derived tumor "
    "microenvironment organization and can facilitate collaborative analysis across computational and experimental teams."
)


def para(text: str = "", style: str | None = None, bold_prefix: str | None = None) -> str:
    parts = ['<w:p>']
    if style:
        parts.append(f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>')
    if bold_prefix:
        parts.append(
            '<w:r><w:rPr><w:b/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(bold_prefix)}</w:t></w:r>'
        )
        parts.append(f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>')
    else:
        parts.append(f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>')
    parts.append("</w:p>")
    return "".join(parts)


def spacer() -> str:
    return '<w:p><w:r><w:t xml:space="preserve"> </w:t></w:r></w:p>'


def build_document_xml() -> str:
    body = [
        para("ECCB 2026 Filled Abstract Draft", style="Title"),
        para("Prepared for poster/highlight submission drafting", style="Subtitle"),
        spacer(),
        para("Presenting Author", style="Heading1"),
        para("Rashid Hussain", bold_prefix="Name: "),
        para("Presenter", bold_prefix="Role: "),
        para("Humanitas Research Hospital, Milan, Italy", bold_prefix="Affiliation: "),
        spacer(),
        para("Title", style="Heading1"),
        para(TITLE),
        spacer(),
        para("Abstract", style="Heading1"),
        para(ABSTRACT),
        para("Word count: 196", style="Emphasis"),
        spacer(),
        para("Suggested Keywords", style="Heading1"),
        para("imaging mass cytometry; spatial analysis; tumor microenvironment; sarcoma; single-cell imaging; computational pathology"),
        spacer(),
        para("Suggested Scientific Areas", style="Heading1"),
        para("Systems biology, multi-omics integration and modelling", bold_prefix="Primary: "),
        para("Proteins and structural biology", bold_prefix="Secondary: "),
    ]
    sect = (
        "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>'
        "</w:sectPr>"
    )
    body_xml = "".join(body) + sect
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
        'mc:Ignorable="w14 w15 wp14">'
        f"<w:body>{body_xml}</w:body></w:document>"
    )


def build_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Aptos" w:hAnsi="Aptos" w:eastAsia="Aptos" w:cs="Aptos"/>
        <w:sz w:val="22"/>
        <w:szCs w:val="22"/>
        <w:color w:val="1F2937"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="34"/><w:color w:val="0F172A"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="180"/></w:pPr>
    <w:rPr><w:i/><w:color w:val="475569"/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="240" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:color w:val="0B3C5D"/><w:sz w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Emphasis">
    <w:name w:val="Emphasis"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr><w:i/><w:color w:val="64748B"/><w:sz w:val="20"/></w:rPr>
  </w:style>
</w:styles>
"""


def build_content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def build_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def build_doc_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""


def build_core_xml() -> str:
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>ECCB 2026 Filled Abstract Draft</dc:title>
  <dc:creator>OpenAI Codex</dc:creator>
  <cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>
"""


def build_app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>OpenAI Codex</Application>
</Properties>
"""


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUT_PATH, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", build_content_types_xml())
        zf.writestr("_rels/.rels", build_rels_xml())
        zf.writestr("docProps/core.xml", build_core_xml())
        zf.writestr("docProps/app.xml", build_app_xml())
        zf.writestr("word/document.xml", build_document_xml())
        zf.writestr("word/styles.xml", build_styles_xml())
        zf.writestr("word/_rels/document.xml.rels", build_doc_rels_xml())
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
