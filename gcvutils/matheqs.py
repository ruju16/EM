import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
from pix2text import Pix2Text
from pix2tex.cli import LatexOCR
from google.cloud import storage
from google.oauth2 import service_account
import streamlit as st

# Setup GCS access
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

def download_pdf_from_gcs(pdf_blob_path):
    """
    Download PDF content from GCS as bytes
    """
    blob = bucket.blob(pdf_blob_path)
    if not blob.exists():
        raise FileNotFoundError(f"GCS blob not found: {pdf_blob_path}")
    return blob.download_as_bytes()

def convert_pdf_bytes_to_images(pdf_bytes):
    """
    Convert PDF bytes to list of PIL images with high DPI
    """
    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    print(f"📄 PDF loaded with {len(doc)} pages")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=300)  # Higher DPI for better clarity
        img_data = pix.tobytes("png")
        image = Image.open(BytesIO(img_data)).convert("RGB")
        images.append(image)
    return images

def process_pdf_from_gcs_to_text(pdf_blob_path):
    """
    Process a PDF stored on GCS, extract math + text, and return the result.
    """
    try:
        pdf_bytes = download_pdf_from_gcs(pdf_blob_path)
        print(f"📦 Downloaded PDF size: {len(pdf_bytes)} bytes")

        images = convert_pdf_bytes_to_images(pdf_bytes)
        print(f"🖼️ Converted to {len(images)} images")

        p2t, latexocr = init_models()

        full_text = ""
        for i, img in enumerate(images):
            result = extract_text_and_latex(img, p2t, latexocr)
            print(f"📄 Page {i + 1} extraction result:\n{result}\n")
            full_text += result + "\n"

        if not full_text.strip():
            print("⚠️ No text extracted from any page.")

        return full_text.strip()
    except Exception as e:
        print(f"❌ Error during PDF processing: {e}")
        return ""

def upload_extracted_text_to_gcs(output_text, title, username):
    """
    Upload extracted result to GCS as a .txt file
    """
    blob_path = f"extracted_texts/{title.replace(' ', '_')}/{username}_extractedtext.txt"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(output_text, content_type="text/plain")
    print(f"✅ Uploaded extracted text to: {blob_path}")
    return blob_path