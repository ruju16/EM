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
    try:
        p2t = Pix2Text(use_fast=True)
        st.success("✅ Pix2Text model loaded successfully.")
    except Exception as e:
        st.error(f"❌ Pix2Text failed to load: {e}")
        p2t = None

    try:
        latexocr = LatexOCR()
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
