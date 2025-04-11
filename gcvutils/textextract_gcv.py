from google.cloud import vision
from google.oauth2 import service_account
import io
import fitz  # PyMuPDF
import streamlit as st
from google.cloud import storage
import tempfile
import os
import json

# Setup GCS and Vision API credentials from secrets
creds = service_account.Credentials.from_service_account_info(st.secrets["google_credentials"])
bucket_name = st.secrets["gcs"]["bucket_name"]
client = storage.Client(credentials=creds)
bucket = client.bucket(bucket_name)

vision_client = vision.ImageAnnotatorClient(credentials=creds)

def extract_handwritten_text_from_pdf(pdf_path, assignment_title, username):
    """
    Extract handwritten text from PDF using GCV and upload result to GCS.
    Returns the GCS blob path of the extracted text.
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    full_text = ""

    progress_bar = st.progress(0)

    for i, page in enumerate(doc):
        progress = int((i / total_pages) * 100)
        progress_bar.progress(progress)

        pix = page.get_pixmap(dpi=300)
        image_byte_arr = pix.tobytes("png")

        gcv_image = vision.Image(content=image_byte_arr)
        response = vision_client.document_text_detection(image=gcv_image)
        annotations = response.full_text_annotation

        if annotations and annotations.text.strip():
            text = annotations.text.strip()
            full_text += text + "\n\n"
            print(f"✅ Extracted page {i+1}")
        else:
            print(f"⚠️ No text on page {i+1}")

        if response.error.message:
            raise Exception(f"API Error: {response.error.message}")

    progress_bar.progress(100)

    # Upload full text to GCS
    blob_path = f"extracted_texts/{assignment_title.replace(' ', '_')}/{username}_extractedtext.txt"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(full_text, content_type='text/plain')

    print(f"✅ Uploaded extracted text to: {blob_path}")
    return blob_path