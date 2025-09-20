# EvalMate: Automated Handwritten Assignment Grading Tool

**EvalMate** is an AI-powered tool that automates grading of handwritten assignments, combining OCR, deep learning for math recognition, and Large Language Models (LLMs) for personalized evaluation and feedback. It reduces teacher workload while providing consistent, actionable insights for students.

---

## Key Features

- **Handwritten Text Recognition**: Extracts text from PDFs/images using OCR.  
- **Math Processing**: Converts handwritten equations to LaTeX via LaTeXOCR/Pix2Text.  
- **Automated Grading**: LLM evaluates answers against teacher-defined rubrics.  
- **Personalized Feedback**: Highlights strengths, weaknesses, and suggestions.  
- **Streamlit Interface**: Separate dashboards for teachers and students.  
- **Scalable & Modular**: Supports small classes to large institutions.  

---

## How It Works

1. Teachers create assignments with metadata and rubrics.  
2. Students upload handwritten PDFs.  
3. PDFs are preprocessed (resized, deskewed, enhanced).  
4. OCR extracts text; LaTeXOCR/Pix2Text handle math.  
5. LLM evaluates answers and generates feedback.  
6. Teachers can review/adjust feedback before publishing.  
7. Students view grades and detailed feedback.  

---

## Data Model

- **Teacher** → Creates Assignments (1:N)  
- **Student** → Submits Assignments (1:N)  
- **Submission** → Linked to Assignment & Student (N:1)  
- **Feedback** → Linked to Submission (1:1)  

---

## Technologies

Python | Streamlit | Google Cloud Vision API | LaTeXOCR | Pix2Text | LLaMA 3.1 (Groq API) | CNNs & BiLSTM  

---

## Benefits

- Fast, fair, and consistent grading.  
- Detailed feedback improves student learning.  
- Handles text and mathematical content.  
- Teacher oversight ensures pedagogical accuracy.  

---

## Future Improvements

- **Multi-language Support**: Extend OCR and LLM evaluation for regional languages.  
- **Plagiarism Detection**: Optional similarity checking between submissions.  
- **Web & Cloud Integration**: Full SaaS version for schools and colleges.  
- **Analytics Dashboard**: Class performance trends and insights.  
- **Enhanced Feedback**: More interactive, step-by-step learning suggestions.  



