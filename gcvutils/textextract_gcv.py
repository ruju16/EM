from google.cloud import vision
from google.oauth2 import service_account
import fitz  # PyMuPDF
import streamlit as st
from google.cloud import storage
from io import BytesIO

# Setup credentials and bucket from Streamlit secrets
creds = service_account.Credentials.from_service_account_info(st.secrets["google_credentials"])
bucket_name = st.secrets["gcs"]["bucket_name"]
client = storage.Client(credentials=creds)
bucket = client.bucket(bucket_name)
vision_client = vision.ImageAnnotatorClient(credentials=creds)

def extract_handwritten_text_from_pdf(gcs_pdf_blob_path, assignment_title, username):
    """
    Extract handwritten text from a PDF stored in GCS using Google Cloud Vision,
    and save the extracted result back to GCS.
    """

    # Step 1: Download PDF from GCS as bytes stream
    pdf_blob = bucket.blob(gcs_pdf_blob_path)
    pdf_stream = BytesIO()
    pdf_blob.download_to_file(pdf_stream)
    pdf_stream.seek(0)

    # Step 2: Load PDF into PyMuPDF
    doc = fitz.open(stream=pdf_stream.read(), filetype="pdf")
    total_pages = len(doc)
    full_text = ""

    progress_bar = st.progress(0)

    # Step 3: Iterate over each page and extract text
    for i, page in enumerate(doc):
        progress_bar.progress(int((i / total_pages) * 100))

        # Render image at DPI 150 to stay well below GCV's 40MB limit
        pix = page.get_pixmap(dpi=150)  # Reduced from 300 to 150
        img_bytes = pix.tobytes("png")

        # Create vision.Image object
        gcv_image = vision.Image(content=img_bytes)
        response = vision_client.document_text_detection(image=gcv_image)
        annotations = response.full_text_annotation

        if annotations and annotations.text.strip():
            full_text += annotations.text.strip() + "\n\n"
            print(f"✅ Extracted text from page {i+1}")
        else:
            print(f"⚠️ No text found on page {i+1}")

        if response.error.message:
            raise Exception(f"❌ API Error on page {i+1}: {response.error.message}")

    progress_bar.progress(100)

    # Step 4: Upload extracted text back to GCS
    blob_path = f"extracted_texts/{assignment_title.replace(' ', '_')}/{username}_extractedtext.txt"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(full_text.strip(), content_type='text/plain')

    print(f"✅ Uploaded extracted text to: {blob_path}")
    return blob_path