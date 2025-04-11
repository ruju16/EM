import os
import tempfile
from PIL import Image
import fitz  # PyMuPDF
from pix2text import Pix2Text
from pix2tex.cli import LatexOCR
from google.cloud import storage
from google.oauth2 import service_account
import streamlit as st

# Load credentials and bucket
credentials = service_account.Credentials.from_service_account_info(st.secrets["google_credentials"])
bucket_name = st.secrets["gcs"]["bucket_name"]
client = storage.Client(credentials=credentials)
bucket = client.bucket(bucket_name)

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

def convert_pdf_to_images(pdf_path):
    """Convert PDF pages to PIL images using PyMuPDF."""
    images = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=200)
        img_data = pix.tobytes("png")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name

        image = Image.open(tmp_path).convert("RGB")
        images.append(image)

    return images

def process_pdf_to_text_and_latex(pdf_path):
    """Extract math + text from a PDF and return it as a single string."""
    try:
        images = convert_pdf_to_images(pdf_path)
        p2t, latexocr = init_models()

        full_text = ""
        for img in images:
            result = extract_text_and_latex(img, p2t, latexocr)
            full_text += result + "\n"

        return full_text.strip()
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return ""

def upload_extracted_text_to_gcs(output_text, title, username):
    """Uploads extracted text to GCS under extracted_texts/assignment_title/username.txt"""
    blob_path = f"extracted_texts/{title.replace(' ', '_')}/{username}_extractedtext.txt"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(output_text, content_type='text/plain')
    return blob_path  # You can store this path in your JSON metadata if needed