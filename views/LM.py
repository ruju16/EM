import streamlit as st

from groq import Groq

GROQ_API_KEY = "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"  # Replace with your actual API key

class LLM:
    def __init__(self) -> None:
        self.messages = [
            {'role': 'system', "content": "You are a bot that will grade assignments and provide feedback to students."},
            {'role': 'system', "content": "You will take instructions from the teacher and grade the assignments accordingly."},
            {'role': 'system', "content": "You will only introduce yourself when asked who are you, only then will you introduce yourself."},
            {'role': 'system', "content": "Your name is EvalMate and you will only introduce yourself if asked."},
            {'role': 'system', "content": "Do not write in bold or italic, you will not use bold or italic characters."}
        ]

    def AI(self, student_answer, model_answer, additional_instructions=""):
        """
        Grades the student's answer by comparing it to the model answer and additional teacher-provided instructions.

        Parameters:
        - student_answer (str): The extracted student answer to grade.
        - model_answer (str): The teacher-provided model answer for comparison.
        - additional_instructions (str): Optional teacher-provided grading instructions.

        Returns:
        - str: The LLM's grading response.
        """
        assert student_answer, "Student answer cannot be empty"
        assert model_answer, "Model answer cannot be empty"

        if additional_instructions:
            self.messages.append({'role': 'system', 'content': f"Grading Instructions: {additional_instructions}"})

        self.messages.append({'role': 'user', 'content': f"Student Answer: {student_answer}"})
        self.messages.append({'role': 'user', 'content': f"Model Answer: {model_answer}"})

        try:
            client = Groq(api_key=GROQ_API_KEY)

            chat_completion = client.chat.completions.create(
                messages=self.messages,
                model="llama3-70b-8192",
                temperature=0.5,
                max_tokens=1024,
                top_p=1,
                stop=None,
                stream=False,
            )

            response = chat_completion.choices[0].message.content
            self.messages.append({'role': 'assistant', 'content': response})
            return response

        except Exception as e:
            print(f"Error occurred: {e}")
            return f"Error occurred: {e}"