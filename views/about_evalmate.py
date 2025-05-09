import streamlit as st
from forms.contact import contact_form

# Custom Styles
st.markdown(
    """
    <style>
        .title-text {
            font-size: 40px;
            font-weight: bold;
            color: #6eacda;
            text-align: left;
        }
        .description-text {
            font-size: 18px;
            color: #ffffff;
            text-align: left;
        }
        .stButton > button {
            background-color: #03346e;
            color: white;
            border-radius: 10px;
            padding: 10px 20px;
            font-size: 16px;
        }
        .stButton > button:hover {
            background-color: #6eacda;
        }
        .main-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .left-content {
            flex: 1;
            display: flex;
            justify-content: center;
        }
        .right-content {
            flex: 1;
            text-align: left;
        }
        .left-content img {
            width: 40%; /* Reduced size for better screen fit */
            max-width: 100px; /* Ensures it does not become too large */
            height: auto;
        }
    </style>
    """,
    unsafe_allow_html=True
)

@st.dialog("📞 Contact Info")
def show_contact_form():
    contact_form()

# Main Page Layout
st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.markdown('<div class="left-content">', unsafe_allow_html=True)
st.image("images/FINAL LOGO.png")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="right-content">', unsafe_allow_html=True)
st.markdown('<p class="title-text">EvalMate</p>', unsafe_allow_html=True)
st.markdown('<p class="description-text">AI-powered grading technology designed for educators.</p>', unsafe_allow_html=True)
if st.button("📩 Contact Info"):
    show_contact_form()
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Features Section
st.subheader("🚀 Key Features")
st.markdown(
    """
    ✅ Instant handwriting recognition for fast and accurate evaluation.\n
    📊 Insightful dashboards to manage assignments.\n
    🧠 Context-aware answer evaluation that understands meaning, not just keywords.\n
    ✏️ Teacher-editable feedback & scores tailored to each student for final review and customization.
    """
)

st.markdown("---")

# Footer
st.markdown("<center><small>© 2025 EvalMate. Elevating education with AI-driven grading.</small></center>", unsafe_allow_html=True)