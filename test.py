import streamlit as st
import pkg_resources

try:
    version = pkg_resources.get_distribution("opencv-python-headless").version
    st.write(f"✅ opencv-python-headless version: {version}")
except Exception as e:
    st.error(f"❌ OpenCV not found: {e}")