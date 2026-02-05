# Redaction Widths Tools

This repository contains tools for analyzing redaction widths in PDF files and measuring word widths for guessing redactions.

## Scripts

### 1. PixelcountBlack.py

This script detects and measures black redaction bars in a PDF file.

**How to use:**

1.  Open `PixelcountBlack.py` in your text editor.
2.  Locate the line `PDF_FILE = "efta00018586.pdf"` (around line 9).
3.  Change `"efta00018586.pdf"` to the filename of your PDF file.
4.  Run the script:
    ```bash
    python PixelcountBlack.py
    ```

### 2. measure_word_widths.py

This script calculates the pixel width of words listed in an input file using the Times New Roman font.

**How to use:**

1.  Open or create a file named `MyGuesslist.txt` in the same directory.
2.  Add the words you want to measure to `MyGuesslist.txt`, one word per line.
3.  Run the script:
    ```bash
    python measure_word_widths.py
    ```
4.  The results will be saved to `MyGuesslist_width.txt`, sorted by width.

## Requirements

*   Python 3.x
*   Dependencies:
    *   `pymupdf` (fitz)
    *   `opencv-python`
    *   `numpy`
    *   `Pillow`

You can install the dependencies using pip:
```bash
pip install pymupdf opencv-python numpy Pillow
```
