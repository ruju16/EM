from google.cloud import vision
from google.oauth2 import service_account
from pdf2image import convert_from_bytes
import io
import streamlit as st

# Set up credentials using secrets
creds = service_account.Credentials.from_service_account_info(
    st.secrets["google_credentials"]
)

def extract_handwritten_text_from_pdf(pdf_path, output_file):
    """
    Extract handwritten text from a PDF using Google Cloud Vision.
    """
    # Read the PDF as bytes
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Convert PDF to images (no Poppler path needed)
    images = convert_from_bytes(pdf_bytes)

    client = vision.ImageAnnotatorClient(credentials=creds)
    
    # Show progress bar
    total_pages = len(images)
    progress_bar = st.progress(0)

    for i, image in enumerate(images):
        progress = int((i / total_pages) * 100)
        progress_bar.progress(progress)
        
        print(f"Processing page {i + 1}...")

        # Convert image to byte array
        image_byte_arr = io.BytesIO()
        image.save(image_byte_arr, format='PNG')
        image_byte_arr = image_byte_arr.getvalue()

        # Use Google Vision API
        gcv_image = vision.Image(content=image_byte_arr)
        response = client.document_text_detection(image=gcv_image)
        annotations = response.full_text_annotation

        if annotations:
            progress_bar.progress(100)
            print(f"Extracted text from page {i + 1}:")
            text = annotations.text
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