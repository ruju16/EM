from google.cloud import vision
from google.oauth2 import service_account
import io
import fitz  
import streamlit as st

# Set up credentials using secrets
creds = service_account.Credentials.from_service_account_info(
    st.secrets["google_credentials"]
)

def extract_handwritten_text_from_pdf(pdf_path, output_file):
    """
    Extract handwritten text from a PDF using Google Cloud Vision.
    """
    # Load PDF using PyMuPDF
    doc = fitz.open(pdf_path)
    client = vision.ImageAnnotatorClient(credentials=creds)

    total_pages = len(doc)
    progress_bar = st.progress(0)

    for i, page in enumerate(doc):
        progress = int((i / total_pages) * 100)
        progress_bar.progress(progress)

        print(f"Processing page {i + 1}...")

        # Render page to PNG bytes
        pix = page.get_pixmap(dpi=300)
        image_byte_arr = pix.tobytes("png")

        # Send to Vision API
        gcv_image = vision.Image(content=image_byte_arr)
        response = client.document_text_detection(image=gcv_image)
        annotations = response.full_text_annotation

        if annotations:
            progress_bar.progress(100)
            text = annotations.text
            print(f"Extracted text from page {i + 1}:")
            print(text)
            save_extracted_text_to_file(text, output_file)
        else:
            print(f"No text detected on page {i + 1}.")

        if response.error.message:
            raise Exception(f"API Error: {response.error.message}")

def save_extracted_text_to_file(text, output_file):
    """
    Save extracted text to a file.
    """
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(text + "\n\n")