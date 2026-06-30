---
name: document-processing-tools
description: "Extract and edit text from documents: PDF OCR, scan cleanup, and direct text editing with nano-pdf."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pdf, ocr, documents, extraction, editing]
    related_skills: [research-tools]
---

# Document Processing Tools

Two complementary approaches: extraction/cleanup (`ocr-and-documents`) and direct text editing (`nano-pdf`).

## OCR and Document Extraction

Extract text from PDFs and scanned images with Python libraries.

### pymupdf (fitz)
```python
import fitz  # PyMuPDF
doc = fitz.open("document.pdf")
for page in doc:
    text = page.get_text()
    print(text)
```

### marker-pdf (High-Quality Markdown)
```bash
marker_single document.pdf --output_dir ./extracted/
# Produces clean markdown with preserved structure
```

### OCR for Scans
```python
import pytesseract
from PIL import Image
import pdf2image

images = pdf2image.convert_from_path("scan.pdf")
for img in images:
    text = pytesseract.image_to_string(img)
    print(text)
```

### Use Cases
- Ingest arXiv PDFs into `llm-wiki`
- Extract text from scanned contracts or forms
- Batch-convert document archives to searchable markdown

## nano-pdf (Direct Text Editing)

Edit PDF text, typos, and titles via natural-language prompts with the `nano-pdf` CLI.

### Install
```bash
pip install nano-pdf
```

### Edit Text
```bash
nano-pdf edit document.pdf --prompt "Fix the typo 'recieve' to 'receive' on page 3"
```

### Edit Titles
```bash
nano-pdf edit document.pdf --prompt "Change the title on page 1 to 'Q3 Report'"
```

### Batch Processing
```bash
nano-pdf batch ./reports/ --prompt "Standardize all dates to ISO 8601"
```

### Pitfalls
- nano-pdf works best on text-based PDFs; scanned images need OCR first
- Complex layouts (multi-column, tables) may shift during editing
- Always review output before overwriting originals

## Workflow: Scan → Extract → Edit → Archive

1. **Scan:** `ocr-and-documents` extracts raw text from PDF/image
2. **Clean:** LLM fixes formatting, typos, structure
3. **Edit:** `nano-pdf` applies targeted changes to the original PDF
4. **Archive:** Save to `llm-wiki` or document management system
