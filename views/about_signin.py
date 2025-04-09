import streamlit as st
import json
import os
import time as TIME
from datetime import datetime
from views.LM import LLM
from gcvutils.textextract_gcv import extract_handwritten_text_from_pdf
from datetime import datetime, time, timedelta
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gcvutils.matheqs import process_pdf_to_text_and_latex

if 'submissions' not in st.session_state:
    st.session_state.submissions = {}

if 'username' not in st.session_state:
    st.session_state.username = None 

username = st.session_state.username 

if username is not None:
    submissions = st.session_state.submissions.get(username, [])
else:
    submissions = []

# File paths for persistent storage
ASSIGNMENTS_FILE = "assignments.json"
NOTIFICATIONS_FILE = "notifications.json"
SUBMISSIONS_FILE = "submissions.json"
STUDENT_FEEDBACK_FILE = "student_feedbacks.json"
FEEDBACKS_FOLDER = "feedbacks"
SECRETS_FILE = ".streamlit/secrets.toml"

def load_data(file_path, default=None):
    """Load data from a JSON file with a default return value."""
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return default if default is not None else []

def save_data(file_path, data):
    """Save data to a JSON file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

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
        folder = os.path.join("extracted_texts", assignment["title"].replace(" ", "_"))
        os.makedirs(folder, exist_ok=True)

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
                for username, extracted_text in assignment["extracted_texts"].items():
                    if assignment["graded_students"].get(username, {}).get("finalized", False):
                        continue

                    student_file = os.path.join("extracted_texts", assignment["title"].replace(" ", "_"), f"{username}_extractedtext.txt")
                    if not os.path.exists(student_file):
                        continue

                    with open(student_file, "r") as f:
                        content = f.read()

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

                                feedback_folder = os.path.join(FEEDBACKS_FOLDER, assignment["title"])
                                os.makedirs(feedback_folder, exist_ok=True)
                                with open(os.path.join(feedback_folder, f"{username}_feedback.txt"), "w") as f:
                                    f.write(edited)

                                save_data(ASSIGNMENTS_FILE, st.session_state.assignments)
                                st.success(f"✅ Feedback sent to {username}!")
                                TIME.sleep(2)
                                st.rerun()

    # TAB 2: Finalized Submissions
    with tabs[1]:
        if not finalized_submissions:
            st.info("📭 No finalized submissions.")
        else:
            for assignment in finalized_submissions:
                st.subheader(f"✅ {assignment['title']} ({assignment.get('subject', 'N/A')})")
                for username, data in assignment["graded_students"].items():
                    if data.get("finalized"):
                        st.markdown(f"**{username}** - Feedback Sent")
                        st.text_area("Feedback", value=data["feedback"], height=100, disabled=True,
                                     key=f"final_{assignment['title']}_{username}")

    # TAB 3: No Submissions
    with tabs[2]:
        if not no_submissions:
            st.success("🎉 All assignments have submissions.")
        else:
            for assignment in no_submissions:
                st.subheader(f"📭 {assignment['title']} ({assignment.get('subject', 'N/A')})")
                st.write(f"📅 Deadline: {assignment['submission_deadline']}")
                st.text_area("Model Answer", value=assignment["model_answer"], height=100, disabled=True,
                             key=f"no_model_{assignment['title']}")

    # TAB 4: All Assignments
    with tabs[3]:
        if not all_assignments:
            st.info("No assignments created yet.")
        else:
            for assignment in all_assignments:
                st.subheader(f"📄 {assignment['title']} ({assignment.get('subject', 'N/A')})")
                col1, col2, col3 = st.columns([3, 3, 1])
                with col1:
                    st.write(f"📅 Deadline: {assignment['submission_deadline']}")
                    st.write(f"📥 Submissions: {len(assignment['extracted_texts'])}")
                with col2:
                    st.text_area("Model Answer", value=assignment["model_answer"], height=100, disabled=True,
                                 key=f"view_model_{assignment['title']}")
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{assignment['title']}"):
                        st.session_state.assignments.remove(assignment)
                        save_data(ASSIGNMENTS_FILE, st.session_state.assignments)
                        st.rerun()

def save_submission_data():
    with open("submissions.json", "w") as f:
        json.dump(st.session_state.submissions, f)

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

    # Load data
    st.session_state.assignments = load_data(ASSIGNMENTS_FILE)
    st.session_state.submissions = load_data(SUBMISSIONS_FILE)

    if "submissions" not in st.session_state:
        st.session_state.submissions = {}

    st.subheader("🔔 Notifications")
    current_user = st.session_state["username"]
    current_date = datetime.now().date()

    today_notifications = []

    for assignment in st.session_state.assignments:
        # Check if deadline is today
        try:
            deadline = datetime.strptime(assignment['submission_deadline'], "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            continue

        submission_exists = current_user in assignment.get("extracted_texts", {})

        if deadline == current_date and not submission_exists:
            msg = f"❗ You missed the deadline for '{assignment['title']}' today!"
            today_notifications.append(msg)

        # Check if feedback was added today
        feedback_file_path = os.path.join(FEEDBACKS_FOLDER, assignment["title"], f"{current_user}_feedback.txt")
        if os.path.exists(feedback_file_path):
            feedback_mod_time = datetime.fromtimestamp(os.path.getmtime(feedback_file_path)).date()
            if feedback_mod_time == current_date:
                msg = f"✅ Your assignment '{assignment['title']}' was graded today!"
                today_notifications.append(msg)

    # Display only today's notifications
    if today_notifications:
        st.write("📅 **Today's Notifications:**")
        for msg in today_notifications:
            st.write(f"- {msg}")
    else:
        st.write("📭 No new notifications for today.")
    # 📂 Filter by Subject
    st.subheader("🧠 Filter Assignments by Subject")
    all_subjects = list({a.get("subject", "Unknown Subject") for a in st.session_state.assignments})
    selected_subject = st.selectbox("Select Subject", ["All"] + sorted(all_subjects))

    # 📝 Assignments Section
    st.subheader("📝 Assignments")
    tabs = st.tabs(["📅 Upcoming", "❌ Past Due", "✅ Graded", "📨 Submitted (Pending Grading)"])

    upcoming_shown = past_due_shown = graded_shown = pending_grading_shown = False

    for idx, assignment in enumerate(st.session_state.assignments):
        subject = assignment.get("subject", "Unknown Subject")
        if selected_subject != "All" and subject != selected_subject:
            continue  # Skip if not matching selected subject

        try:
            deadline = datetime.strptime(assignment['submission_deadline'], "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            continue

        title = assignment["title"]

        submissions = st.session_state.submissions.get(username, [])

        is_submitted = title in submissions
        feedback_file_path = os.path.join(FEEDBACKS_FOLDER, title, f"{username}_feedback.txt")
        is_graded = os.path.exists(feedback_file_path)

        # 📅 Upcoming
        if current_date <= deadline and not is_submitted:
            with tabs[0]:
                upcoming_shown = True
                st.write(f"**{title}** *(Subject: {subject})* — Deadline: {assignment['submission_deadline']}")

                uploaded_file = st.file_uploader(
                    f"📄 Upload PDF for {title}",
                    type=["pdf"],
                    key=f"upload_{idx}"
                )

                if uploaded_file:
                    upload_folder = f"uploads/{title.replace(' ', '_')}"
                    os.makedirs(upload_folder, exist_ok=True)

                    pdf_path = os.path.join(upload_folder, f"{username}.pdf")
                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_file.read())

                    st.success(f"✅ File uploaded successfully for {title}!")

                    if st.button(f"Extract Text for {title}", key=f"extract_{idx}"):
                        try:
                            assignment_folder = os.path.join("extracted_texts", title.replace(" ", "_"))
                            os.makedirs(assignment_folder, exist_ok=True)
                            extracted_text_path = os.path.join(assignment_folder, f"{username}_extractedtext.txt")

                            # 📘 Use different extraction based on subject
                            if subject.lower() == "maths":
                                process_pdf_to_text_and_latex(pdf_path, extracted_text_path)
                            else:
                                extract_handwritten_text_from_pdf(pdf_path, extracted_text_path)

                            for assign in st.session_state.assignments:
                                if assign['title'] == title:
                                    assign.setdefault("submitted_files", []).append(pdf_path)
                                    assign.setdefault("extracted_texts", {})[username] = extracted_text_path
                                    break

                            save_data(ASSIGNMENTS_FILE, st.session_state.assignments)
                            st.session_state.submissions.setdefault(username, []).append(title)
                            save_data(SUBMISSIONS_FILE, st.session_state.submissions)

                            st.success("📌 Your submission has been recorded and text extracted successfully!")

                        except Exception as e:
                            st.error(f"❌ Error during text extraction: {e}")

        # ❌ Past Due
        elif current_date > deadline and not is_submitted:
            with tabs[1]:
                past_due_shown = True
                st.write(f"**{title}** *(Subject: {subject})* — Deadline: {assignment['submission_deadline']}")
                st.warning("⏳ Submission deadline has passed. You cannot upload files for this assignment.")

        # ✅ Graded
        elif is_submitted and is_graded:
            with tabs[2]:
                graded_shown = True
                with open(feedback_file_path, "r") as f:
                    feedback = f.read()
                st.success(f"📘 **{title}** *(Subject: {subject})* - Feedback: {feedback}")

        # 📨 Submitted, not graded
        elif is_submitted and not is_graded:
            with tabs[3]:
                pending_grading_shown = True
                st.info(f"📄 **{title}** *(Subject: {subject})* - Submitted, waiting for grading.")

    # Empty tabs fallback messages
    with tabs[0]:
        if not upcoming_shown:
            st.success("🎉 Yay! No pending assignments!")

    with tabs[1]:
        if not past_due_shown:
            st.success("🎉 Yay! No past due assignments!")

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