import streamlit as st

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