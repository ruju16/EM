import streamlit as st
import os
os.system("pip uninstall -y opencv-python opencv-python-headless && pip install opencv-python-headless==4.8.1.78")
import cv2
print("✅ OpenCV version:", cv2.__version__)

about_page = st.Page(
    page = "views/about_evalmate.py",
    title = "About Evalmate",
    icon = ":material/account_circle:",
    default = True,
)

project_1_page = st.Page(
    page = "views/about_signin.py",
    title = "Sign In",
    icon = ":material/login:",
)
pg = st.navigation(pages=[about_page,project_1_page])
pg.run()

# Shared on all pages
st.logo("images/FINAL LOGO.png")