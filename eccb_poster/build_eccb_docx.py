from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


OUT_PATH = Path("/Users/rashid/1_IMC_Analysis/11_Vincenzo/ECCB_2026_submission_template.docx")


def para(text: str = "", style: str | None = None, bold_prefix: str | None = None) -> str:
    parts = ['<w:p>']
    if style:
        parts.append(f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>')
    if bold_prefix:
        parts.append(
            '<w:r><w:rPr><w:b/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(bold_prefix)}</w:t></w:r>'
        )
        if text:
            parts.append(f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>')
    else:
        safe = escape(text) if text else ""
        parts.append(f'<w:r><w:t xml:space="preserve">{safe}</w:t></w:r>')
    parts.append("</w:p>")
    return "".join(parts)


def spacer() -> str:
    return '<w:p><w:r><w:t xml:space="preserve"> </w:t></w:r></w:p>'


def build_document_xml() -> str:
    body = []
    body.append(para("ECCB 2026 Submission Template", style="Title"))
    body.append(para("Editable draft based on the EasyChair submission form for posters or highlight talks.", style="Subtitle"))
    body.append(spacer())

    body.append(para("Submission reminder", style="Heading1"))
    body.append(para("Abstracts must be plain text and no longer than 250 words. No tables, images, or references should appear in the abstract field."))
    body.append(para("Deadline: April 20, 2026 at 1:00 p.m. CET."))
    body.append(spacer())

    body.append(para("Submission Type", style="Heading1"))
    body.append(para("[Choose one: Poster / Highlight Talk]"))
    body.append(spacer())

    body.append(para("Author Information", style="Heading1"))
    body.append(para("[First Name]", bold_prefix="Presenting Author First Name: "))
    body.append(para("[Last Name]", bold_prefix="Presenting Author Last Name: "))
    body.append(para("[Email Address]", bold_prefix="Email: "))
    body.append(para("[Country or Region]", bold_prefix="Country/Region: "))
    body.append(para("[Institution, Department, City, Country]", bold_prefix="Affiliation: "))
    body.append(para("[Mark corresponding author: Yes/No]   [Mark presenter: Yes/No]", bold_prefix="Author Role Flags: "))
    body.append(para("[Add each co-author with full name, affiliation, and email address]", bold_prefix="Co-Authors: "))
    body.append(spacer())

    body.append(para("Title and Abstract", style="Heading1"))
    body.append(para("[Insert conference title here]", bold_prefix="Title: "))
    body.append(para("[Insert abstract here, maximum 250 words, plain text only]", bold_prefix="Abstract: "))
    body.append(para("Tip: structure the abstract around motivation, method, results, and impact.", style="Emphasis"))
    body.append(spacer())

    body.append(para("Keywords", style="Heading1"))
    body.append(para("imaging mass cytometry; spatial analysis; tumor microenvironment; single-cell imaging; sarcoma; computational pathology", bold_prefix="Suggested keywords: "))
    body.append(para("Use at least three keywords. Replace or expand these based on the final framing of the submission.", style="Emphasis"))
    body.append(spacer())

    body.append(para("Scientific Areas", style="Heading1"))
    body.append(para("Systems biology, multi-omics integration and modelling", bold_prefix="Primary Scientific Area: "))
    body.append(para("Proteins and structural biology", bold_prefix="Secondary Scientific Area: "))
    body.append(para("Suggested based on your IMC ROI analysis platform and spatial tumor microenvironment framing.", style="Emphasis"))
    body.append(spacer())

    body.append(para("Other Information and Files", style="Heading1"))
    body.append(para("[For highlight talk: year, journal, volume, pages, DOI or preprint URL. If not applicable, enter N/A.]", bold_prefix="Information about the original publication: "))
    body.append(para("N/A", bold_prefix="Conflicts of Interest: "))
    body.append(para("I understand and agree.", bold_prefix="In-Person Participation Understanding: "))
    body.append(para("[Attach PDF if required for highlight talk, optional for poster]", bold_prefix="Paper Upload: "))
    body.append(spacer())

    body.append(para("Submission Checklist", style="Heading1"))
    checklist = [
        "At least one author is marked as corresponding author.",
        "One author is marked as presenter.",
        "The abstract is 250 words or fewer.",
        "The title and abstract are plain text only.",
        "At least three keywords are included.",
        "Primary and secondary scientific areas are selected.",
        "Original publication details are filled in, or N/A is entered.",
        "Any required PDF file is ready for upload.",
    ]
    for item in checklist:
        body.append(para(f"- {item}"))
    body.append(spacer())
    body.append(para("Prepared as an editable drafting document for ECCB 2026 submission planning.", style="FooterText"))

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
    <w:rPr>
      <w:b/>
      <w:sz w:val="34"/>
      <w:color w:val="0F172A"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="180"/></w:pPr>
    <w:rPr>
      <w:i/>
      <w:color w:val="475569"/>
      <w:sz w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="240" w:after="80"/></w:pPr>
    <w:rPr>
      <w:b/>
      <w:color w:val="0B3C5D"/>
      <w:sz w:val="28"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Emphasis">
    <w:name w:val="Emphasis"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:i/>
      <w:color w:val="64748B"/>
      <w:sz w:val="20"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="FooterText">
    <w:name w:val="FooterText"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="180"/></w:pPr>
    <w:rPr>
      <w:color w:val="475569"/>
      <w:sz w:val="18"/>
    </w:rPr>
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
  <dc:title>ECCB 2026 Submission Template</dc:title>
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
