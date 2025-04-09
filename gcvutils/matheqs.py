import os
import tempfile
from PIL import Image
from PyPDF2 import PdfReader
import fitz
from pix2text import Pix2Text
from pix2tex.cli import LatexOCR

def init_models():
    return Pix2Text(use_fast=True), LatexOCR()

def clean_latex_string(latex):
    return latex.replace(r'\left', '').replace(r'\right', '')

def extract_text_and_latex(image, p2t_model, latexocr_model):
    full_text = ""
    extracted = p2t_model.recognize(image)

    if isinstance(extracted, list):
        for item in extracted:
            if item['type'] == 'text':
                full_text += item['text'].strip() + "\n"
            elif item['type'] == 'formula':
                latex = latexocr_model(image)
                cleaned_latex = clean_latex_string(latex)
                full_text += cleaned_latex.strip() + "\n"
    elif isinstance(extracted, dict):
        if extracted.get('type') == 'text':
            full_text += extracted['text'].strip() + "\n"
        elif extracted.get('type') == 'formula':
            latex = latexocr_model(image)
            cleaned_latex = clean_latex_string(latex)
            full_text += cleaned_latex.strip() + "\n"
    elif isinstance(extracted, str):
        full_text += extracted.strip() + "\n"
    else:
        full_text += "[Unsupported format]\n"

    return full_text.strip()

def save_extracted_text_to_file(text, output_file):
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(text + "\n")

def convert_pdf_to_images(pdf_path):
    """Use PyMuPDF to convert PDF pages to images (no Poppler needed)."""
    images = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=200)  # Reasonable DPI for handwriting
        img_data = pix.tobytes("png")
        image = Image.open(tempfile.NamedTemporaryFile(delete=False, suffix=".png"))
        image.fp.write(img_data)
        image.fp.close()
        image = Image.open(image.fp.name).convert("RGB")
        images.append(image)
    return images

def process_pdf_to_text_and_latex(pdf_path, output_txt_path):
    try:
        images = convert_pdf_to_images(pdf_path)
        p2t, latexocr = init_models()

        for img in images:
            result = extract_text_and_latex(img, p2t, latexocr)
            save_extracted_text_to_file(result, output_txt_path)

        print(f"✅ Extracted content saved to: {output_txt_path}")
    except Exception as e:
        print(f"❌ Error during processing: {e}")