import streamlit as st
import json
import os
import time as TIME
from datetime import datetime
from views.LM import LLM
from gcvutils.textextract_gcv import extract_handwritten_text_from_pdf
from datetime import datetime, time, timedelta
from google.cloud import storage
from google.oauth2 import service_account
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gcvutils.matheqs import process_pdf_to_text_and_latex

# File paths for persistent storage
ASSIGNMENTS_FILE = "assignments/assignments.json"
NOTIFICATIONS_FILE = "notifications/notifications.json"
SUBMISSIONS_FILE = "submissions/submissions.json"
STUDENT_FEEDBACK_FILE = "feedbacks/student_feedbacks.json"
FEEDBACKS_FOLDER = "feedbacks"
SECRETS_FILE = ".streamlit/secrets.toml"

credentials = service_account.Credentials.from_service_account_info(st.secrets["google_credentials"])
bucket_name = st.secrets["gcs"]["bucket_name"]
client = storage.Client(credentials=credentials)
bucket = client.bucket(bucket_name)

def load_data(blob_name, default=None):
    """Loads JSON data from GCS."""
    try:
        blob = bucket.blob(blob_name)
        if blob.exists():
            data = blob.download_as_text()
            return json.loads(data)
    except Exception as e:
        st.error(f"Error loading {blob_name}: {e}")
    return default if default is not None else []

def save_data(blob_name, data):
    """Saves JSON data to GCS."""
    try:
        blob = bucket.blob(blob_name)
        blob.upload_from_string(json.dumps(data, indent=4), content_type='application/json')
    except Exception as e:
        st.error(f"Error saving {blob_name}: {e}")

# Load session data
if "assignments" not in st.session_state:
    st.session_state.assignments = load_data(ASSIGNMENTS_FILE, [])

if "student_feedbacks" not in st.session_state:
    st.session_state.student_feedbacks = load_data(STUDENT_FEEDBACK_FILE, {})

def teacher_dashboard():
    st.title("Teacher Dashboard")
    st.write("👩‍🏫 Manage Assignments and Notifications")

    if st.button("Logout"):
        logout()

    # Add New Assignment
    st.markdown("## 📝 Add New Assignment")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            assignment_title = st.text_input("📌 Assignment Title", placeholder="e.g., Math Homework 1")
            subject = st.selectbox("📚 Subject", ["DTE", "NIC", "XAI", "AIH", "EDM", "Honours", "Maths"])
        with col2:
            due_date = st.date_input("📅 Due Date")
            time_choice = st.selectbox("⏰ Select Due Time", ["🕛 12:00 PM", "🌙 11:59 PM"])
            due_time = time(12, 0) if time_choice == "🕛 12:00 PM" else time(23, 59)

        model_answer = st.text_area("🧠 Model Answer", placeholder="Write the model answer here...", height=120)
        if st.button("➕ Add Assignment"):
            if not assignment_title or not model_answer:
                st.error("❌ Assignment title and model answer cannot be empty.")
            else:
                new_assignment = {
                    "title": assignment_title,
                    "subject": subject,
                    "submission_deadline": f"{due_date} {due_time}",
                    "model_answer": model_answer,
                    "extracted_texts": {},
                    "graded_students": {}
                }
                st.session_state.assignments.append(new_assignment)
                save_data(ASSIGNMENTS_FILE, st.session_state.assignments)
                st.success(f"✅ Assignment '{assignment_title}' added successfully!")
                TIME.sleep(2)
                st.rerun()

    # Categorization
    pending_grading, finalized_submissions, no_submissions, all_assignments = [], [], [], []

    for assignment in st.session_state.assignments:
        total_subs = len(assignment["extracted_texts"])
        if total_subs == 0:
            no_submissions.append(assignment)
        else:
            all_graded = all(assignment["graded_students"].get(user, {}).get("finalized", False)
                             for user in assignment["extracted_texts"])
            if all_graded:
                finalized_submissions.append(assignment)
            else:
                pending_grading.append(assignment)
        all_assignments.append(assignment)

    # Subject Filter
    st.markdown("## 📂 Filter Assignments by Subject")
    all_subjects = ["All"] + sorted(set(a.get("subject", "Unspecified") for a in st.session_state.assignments))
    selected_subject = st.selectbox("📚 Select Subject", all_subjects)

    def filter_by_subject(assignments):
        return assignments if selected_subject == "All" else [a for a in assignments if a.get("subject") == selected_subject]

    pending_grading = filter_by_subject(pending_grading)
    finalized_submissions = filter_by_subject(finalized_submissions)
    no_submissions = filter_by_subject(no_submissions)
    all_assignments = filter_by_subject(all_assignments)

    tabs = st.tabs(["🟡 Pending Grading", "✅ Finalized Submissions", "📭 No Submissions", "📄 All Assignments"])

    # TAB 1: Pending Grading
    with tabs[0]:
        if not pending_grading:
            st.info("🎉 No assignments pending grading.")
        else:
            for assignment in pending_grading:
                st.subheader(f"🟡 {assignment['title']} ({assignment.get('subject', 'N/A')})")
                for username, extracted_text_path in assignment["extracted_texts"].items():
                    if assignment["graded_students"].get(username, {}).get("finalized", False):
                        continue

                    blob_path = extracted_text_path.replace("\\", "/").replace("./", "")
                    try:
                        content = bucket.blob(blob_path).download_as_text()
                    except:
                        st.warning(f"⚠️ Could not load submission for {username}.")
                        continue

                    with st.expander(f"📄 Submission from {username}"):
                        st.text_area("Extracted Answer", value=content, height=150, disabled=True,
                                     key=f"extracted_{assignment['title']}_{username}")
                        instructions = st.text_area("Optional Grading Instructions",
                                                    key=f"instructions_{assignment['title']}_{username}")

                        if st.button(f"⚙️ Generate Feedback", key=f"generate_{assignment['title']}_{username}"):
                            if not assignment["model_answer"]:
                                st.error("❌ Model answer is required.")
                            else:
                                llm = LLM()
                                feedback = llm.AI(
                                    student_answer=content,
                                    model_answer=assignment["model_answer"],
                                    additional_instructions=instructions
                                )
                                st.session_state[f"feedback_{assignment['title']}_{username}"] = feedback
                                st.rerun()

                        feedback_key = f"feedback_{assignment['title']}_{username}"
                        if feedback_key in st.session_state:
                            st.markdown("### ✍️ Review & Edit Feedback Before Sending")
                            edited = st.text_area("Edit Feedback",
                                                  value=st.session_state[feedback_key],
                                                  height=200,
                                                  key=f"edit_{assignment['title']}_{username}")

                            if st.button("✅ Finalize & Send Feedback", key=f"finalize_{assignment['title']}_{username}"):
                                assignment["graded_students"][username] = {
                                    "feedback": edited,
                                    "finalized": True
                                }

                                feedback_blob_path = f"{FEEDBACKS_FOLDER}/{assignment['title']}/{username}_feedback.txt"
                                bucket.blob(feedback_blob_path).upload_from_string(edited, content_type='text/plain')

                                save_data(ASSIGNMENTS_FILE, st.session_state.assignments)
                                st.success(f"✅ Feedback sent to {username}!")
                                TIME.sleep(2)
                                st.rerun()

def student_dashboard():
    st.title("Student Dashboard")
    st.write("📚 View Assignments, Feedback, and Notifications")

    if st.button("Logout"):
        logout()
        return

    current_date = datetime.today().date()
    username = st.session_state.get("username")

    if not username:
        st.error("You are not logged in. Please log in first.")
        return

    # Load GCS data
    st.session_state.assignments = load_data(ASSIGNMENTS_FILE, default=[])
    st.session_state.submissions = load_data(SUBMISSIONS_FILE, default={})

    if not isinstance(st.session_state.assignments, list):
        st.error("🚨 Assignments file is not in the correct format.")
        st.stop()

    if not isinstance(st.session_state.submissions, dict):
        st.session_state.submissions = {}

    st.subheader("🔔 Notifications")
    today_notifications = []

    for assignment in st.session_state.assignments:
        title = assignment.get("title")
        subject = assignment.get("subject", "Unknown Subject")

        if not title:
            continue

        try:
            deadline = datetime.strptime(assignment['submission_deadline'], "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            continue

        submission_exists = username in assignment.get("extracted_texts", {})

        if deadline == current_date and not submission_exists:
            today_notifications.append(f"❗ You missed the deadline for '{title}' today!")

        feedback_blob = f"{FEEDBACKS_FOLDER}/{title}/{username}_feedback.txt"
        feedback_file = bucket.blob(feedback_blob)
        if feedback_file.exists():
            mod_time = feedback_file.updated.date()
            if mod_time == current_date:
                today_notifications.append(f"✅ Your assignment '{title}' was graded today!")

    if today_notifications:
        st.write("📅 **Today's Notifications:**")
        for msg in today_notifications:
            st.write(f"- {msg}")
    else:
        st.write("📭 No new notifications for today.")

    st.subheader("🧠 Filter Assignments by Subject")
    all_subjects = list({a.get("subject", "Unknown Subject") for a in st.session_state.assignments})
    selected_subject = st.selectbox("Select Subject", ["All"] + sorted(all_subjects))

    st.subheader("📝 Assignments")
    tabs = st.tabs(["📅 Upcoming", "❌ Past Due", "✅ Graded", "📨 Submitted (Pending Grading)"])

    upcoming_shown = past_due_shown = graded_shown = pending_grading_shown = False

    for idx, assignment in enumerate(st.session_state.assignments):
        title = assignment.get("title")
        subject = assignment.get("subject", "Unknown Subject")

        if not title or (selected_subject != "All" and subject != selected_subject):
            continue

        try:
            deadline = datetime.strptime(assignment['submission_deadline'], "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            continue

        submissions = st.session_state.submissions.get(username, [])
        is_submitted = title in submissions

        feedback_blob = f"{FEEDBACKS_FOLDER}/{title}/{username}_feedback.txt"
        feedback_file = bucket.blob(feedback_blob)
        is_graded = feedback_file.exists()

        # 📅 Upcoming
        if current_date <= deadline and not is_submitted:
            with tabs[0]:
                upcoming_shown = True
                st.write(f"**{title}** *(Subject: {subject})* — Deadline: {assignment['submission_deadline']}")
                uploaded_file = st.file_uploader(f"📄 Upload PDF for {title}", type=["pdf"], key=f"upload_{idx}")

                if uploaded_file:
                    pdf_blob_path = f"uploads/{title.replace(' ', '_')}/{username}.pdf"
                    pdf_blob = bucket.blob(pdf_blob_path)
                    pdf_blob.upload_from_file(uploaded_file, content_type="application/pdf")
                    st.success(f"✅ File uploaded successfully for {title}!")

                    if st.button(f"Extract Text for {title}", key=f"extract_{idx}"):
                        try:
                            extracted_text_blob = f"extracted_texts/{title.replace(' ', '_')}/{username}_extractedtext.txt"
                            extracted_path = f"/tmp/{username}_extract.txt"

                            pdf_blob.download_to_filename("/tmp/input.pdf")
                            if subject.lower() == "maths":
                                process_pdf_to_text_and_latex("/tmp/input.pdf", extracted_path)
                            else:
                                extract_handwritten_text_from_pdf("/tmp/input.pdf", extracted_path)

                            with open(extracted_path, "r") as f:
                                content = f.read()

                            bucket.blob(extracted_text_blob).upload_from_string(content)

                            for assign in st.session_state.assignments:
                                if assign.get("title") == title:
                                    assign.setdefault("submitted_files", []).append(pdf_blob_path)
                                    assign.setdefault("extracted_texts", {})[username] = extracted_text_blob
                                    break

                            save_data(ASSIGNMENTS_FILE, st.session_state.assignments)
                            st.session_state.submissions.setdefault(username, []).append(title)
                            save_data(SUBMISSIONS_FILE, st.session_state.submissions)

                            st.success("📌 Your submission has been recorded and text extracted successfully!")
                        except Exception as e:
                            st.error(f"❌ Error during text extraction: {e}")

        elif current_date > deadline and not is_submitted:
            with tabs[1]:
                past_due_shown = True
                st.write(f"**{title}** *(Subject: {subject})* — Deadline: {assignment['submission_deadline']}")
                st.warning("⏳ Submission deadline has passed.")

        elif is_submitted and is_graded:
            with tabs[2]:
                graded_shown = True
                feedback = feedback_file.download_as_text()
                st.success(f"📘 **{title}** *(Subject: {subject})* - Feedback: {feedback}")

        elif is_submitted and not is_graded:
            with tabs[3]:
                pending_grading_shown = True
                st.info(f"📄 **{title}** *(Subject: {subject})* - Submitted, waiting for grading.")

    with tabs[0]:
        if not upcoming_shown:
            st.success("🎉 Yay! No pending assignments!")
    with tabs[1]:
        if not past_due_shown:
            st.success("🎉 No past due assignments!")
    with tabs[2]:
        if not graded_shown:
            st.info("👏 All submitted assignments have been graded!")
    with tabs[3]:
        if not pending_grading_shown:
            st.info("📘 All your assignments have been graded!")

# Login and Logout Functions
teachers_db = st.secrets["teachers"]
students_db = st.secrets["students"]

def check_login(username, password):
    """Check user credentials against stored values."""
    if username in teachers_db and password == teachers_db[username]:
        st.session_state.user_type = "Teacher"
        return True
    elif username in students_db and password == students_db[username]:
        st.session_state.user_type = "Student"
        return True
    return False

def login():
    """Fancy User login interface with improved aesthetics and professionalism."""
    st.markdown(
        """
        <style>
        .main {
            background-color: #f0f2f6;
        }
        div.stButton > button:first-child {
            background-color: #03346e;
            color: white;
            border-radius: 8px;
            height: 3em;
            width: 100%;
            font-size: 16px;
            font-weight: 600;
            transition: 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #1d4ed8;
            transform: scale(1.02);
        }
        .stTextInput > div > input {
            padding: 0.75em;
            border-radius: 8px;
            border: 1px solid #ccc;
            font-size: 1rem;
        }
        .stRadio > div {
            gap: 20px;
        }
        .custom-link {
            font-size: 0.9rem;
            color: #2563eb;
            text-align: right;
            display: block;
            margin-top: -0.5rem;
            margin-bottom: 1rem;
        }
        .custom-link:hover {
            text-decoration: underline;
            color: #1d4ed8;
        }
        .alt-option {
            margin-top: 1.5rem;
            font-size: 0.9rem;
            text-align: center;
        }
        .alt-option a {
            color: #2563eb;
            font-weight: 500;
            text-decoration: none;
        }
        .alt-option a:hover {
            text-decoration: underline;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("## Welcome to **EvalMate**")
    st.markdown("### A Smarter Way to Manage Assignments")
    st.write("Please log in to continue:")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # User Type Selection
        user_type = st.radio("I am a", ("Student", "Teacher"))
        st.session_state.user_type = user_type  # Save for dashboard routing

        # Input Fields
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        # Sign In Button
        if st.button("Sign In"):
            if check_login(username, password):
                st.success("Login Successful!")
                st.session_state.logged_in = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Login failed. Please check your credentials.")

def logout():
    """Logs out the user and clears session state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "navigation" not in st.session_state:
        st.session_state.navigation = "login"

    if not st.session_state.logged_in:
        if st.session_state.navigation == "login":
            login()
    else:
        if st.session_state.user_type == "Teacher":
            teacher_dashboard()
        elif st.session_state.user_type == "Student":
            student_dashboard()

main()