import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
from pix2text import Pix2Text
from pix2tex.cli import LatexOCR
from google.cloud import storage
from google.oauth2 import service_account
import streamlit as st
import os

# Setup GCS access
credentials = service_account.Credentials.from_service_account_info(st.secrets["google_credentials"])
bucket_name = st.secrets["gcs"]["bucket_name"]
client = storage.Client(credentials=credentials)
bucket = client.bucket(bucket_name)

# Persistent directory for models
PIX2TEXT_MODEL_DIR = os.path.expanduser("model/pix2text/breezedeus-Pix2Text")
LATEXOCR_MODEL_PATH = os.path.expanduser("~/.streamlit/latexocr/weights.pth")

def ensure_pix2text_model():
    expected_files = ["config.json", "model.safetensors"]  # Adjust as per model contents
    missing_files = [f for f in expected_files if not os.path.exists(os.path.join(PIX2TEXT_MODEL_DIR, f))]
    if missing_files:
        st.info("📦 Downloading Pix2Text model files from GCS...")
        for blob in bucket.list_blobs(prefix="models/pix2text/breezedeus-Pix2Text/"):
            rel_path = blob.name.replace("models/pix2text/breezedeus-Pix2Text/", "")
            if rel_path:
                local_path = os.path.join(PIX2TEXT_MODEL_DIR, rel_path)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                blob.download_to_filename(local_path)
        st.success("✅ Pix2Text model files downloaded.")

def ensure_latexocr_model():
    if not os.path.exists(LATEXOCR_MODEL_PATH):
        st.info("📦 Downloading LatexOCR weights from GCS...")
        latexocr_blob = bucket.blob("models/latexocr/weights.pth")
        os.makedirs(os.path.dirname(LATEXOCR_MODEL_PATH), exist_ok=True)
        latexocr_blob.download_to_filename(LATEXOCR_MODEL_PATH)
        st.success("✅ LatexOCR weights downloaded.")

def init_models():
    try:
        ensure_pix2text_model()
        p2t = Pix2Text(model_dir=PIX2TEXT_MODEL_DIR, use_fast=True)
        st.success("✅ Pix2Text model loaded successfully.")
    except Exception as e:
        st.error(f"❌ Pix2Text failed to load: {e}")
        p2t = None

    try:
        ensure_latexocr_model()
        latexocr = LatexOCR(weights_path=LATEXOCR_MODEL_PATH)
        st.success("✅ LatexOCR model loaded successfully.")
    except Exception as e:
        st.error(f"❌ LatexOCR failed to load: {e}")
        latexocr = None

    return p2t, latexocr

def clean_latex_string(latex):
    return latex.replace(r'\left', '').replace(r'\right', '')

def extract_text_and_latex(image, p2t_model, latexocr_model):
    full_text = ""
    try:
        extracted = p2t_model.recognize(image)
        st.write("🔍 Raw Pix2Text Output:", extracted)
    except Exception as e:
        st.error(f"❌ Pix2Text recognition failed: {e}")
        return "[Pix2Text recognition error]"

    if isinstance(extracted, list):
        for item in extracted:
            if item['type'] == 'text':
                full_text += item['text'].strip() + "\n"
            elif item['type'] == 'formula' and latexocr_model:
                try:
                    latex = latexocr_model(image)
                    cleaned_latex = clean_latex_string(latex)
                    full_text += cleaned_latex.strip() + "\n"
                except Exception as e:
                    st.error(f"❌ LatexOCR failed on formula: {e}")
    elif isinstance(extracted, dict):
        if extracted.get('type') == 'text':
            full_text += extracted['text'].strip() + "\n"
        elif extracted.get('type') == 'formula' and latexocr_model:
            try:
                latex = latexocr_model(image)
                cleaned_latex = clean_latex_string(latex)
                full_text += cleaned_latex.strip() + "\n"
            except Exception as e:
                st.error(f"❌ LatexOCR failed on formula: {e}")
    elif isinstance(extracted, str):
        full_text += extracted.strip() + "\n"
    else:
        full_text += "[Unsupported format]\n"

    return full_text.strip()

def download_pdf_from_gcs(pdf_blob_path):
    blob = bucket.blob(pdf_blob_path)
    if not blob.exists():
        raise FileNotFoundError(f"📁 GCS blob not found: {pdf_blob_path}")
    return blob.download_as_bytes()

def convert_pdf_bytes_to_images(pdf_bytes, dpi=500):
    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    st.info(f"📄 PDF loaded with {len(doc)} pages")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        img_data = pix.tobytes("png")
        image = Image.open(BytesIO(img_data)).convert("RGB")
        images.append(image)
    return images

def process_pdf_from_gcs_to_text(pdf_blob_path):
    try:
        pdf_bytes = download_pdf_from_gcs(pdf_blob_path)
        st.info(f"📥 PDF downloaded from GCS: {len(pdf_bytes)} bytes")
        images = convert_pdf_bytes_to_images(pdf_bytes)
        st.success(f"🖼️ {len(images)} page(s) converted to images.")

        p2t, latexocr = init_models()
        if not p2t:
            return "[Pix2Text failed to initialize]"

        full_text = ""
        for i, img in enumerate(images):
            st.image(img, caption=f"Page {i+1} Preview", use_column_width=True)
            result = extract_text_and_latex(img, p2t, latexocr)
            st.text_area(f"📄 Extracted Text - Page {i+1}", result, height=200)
            full_text += result + "\n\n"

        if not full_text.strip():
            st.warning("⚠️ No text extracted from any page.")

        return full_text.strip()
    except Exception as e:
        st.error(f"❌ Error during PDF processing: {e}")
        return "[Error processing PDF]"

def upload_extracted_text_to_gcs(output_text, title, username):
    blob_path = f"extracted_texts/{title.replace(' ', '_')}/{username}_extractedtext.txt"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(output_text, content_type="text/plain")
    st.success(f"✅ Uploaded extracted text to: `{blob_path}`")
    return blob_path