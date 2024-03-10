from openai import OpenAI
import streamlit as st
from prompts import *
import random
import time
from typing import List, Optional, Union, Dict, Any

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.write("*Please contact David Liebovitz, MD if you need an updated password for access.*")
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if 'pending_question' not in st.session_state:
    st.session_state['pending_question'] = ''

st.title("Neurology Assistant")
st.info("This covers only Parkinson's Disease as an example using NLM Bookshelf references.")

if check_password():

    client = OpenAI(
    organization= st.secrets["ORGANIZATION"],
    api_key = st.secrets["OPENAI_API_KEY"]
    )
    # Retrieve My Assistant
    my_assistant = client.beta.assistants.retrieve(st.secrets["ASSISTANT_ID"])

    # Create a new thread
    thread = client.beta.threads.create()

    # Add a message to the thread
    my_role = st.radio("What is your role?", ["patient", "neurologist", "other"], horizontal=True)
    if my_role == "other":
        my_role = st.text_input("What is your role? ")
    
    suggested_patient_questions = [
        "Ask your own question",
        "I have a tongue tremor; is that common with PD?",
        "What is best early treatment for PD; I just got diagnosed",
        "I had a DAT scan for tremor and its normal, but doctor thought it was PD, what is the cause of my tremor?",
        "I heard about deep brain stimulation and want to know if I should get that treatment for Parkinson’s disease",
    ]
    suggested_neurologist_questions = [
        "Ask your own question",
        "Generate patient instructions for a patient with Parkinson’s disease who is going to be admitted to the hospital for an elective surgery.",
        "Provide guidance on precautions to minimize risk in patients with PD who are hospitalized."
    ]    
    
    if my_role == "patient":
        selected_question = st.radio("", suggested_patient_questions)
        
    if my_role == "neurologist":
        selected_question = st.radio("", suggested_neurologist_questions)
        
    if selected_question != "Ask your own question":
        st.session_state.pending_question = selected_question
    
    if selected_question == "Ask your own question":
        
        my_question = st.text_input("What is your question?")
        st.session_state.pending_question = my_question

    
    # message = client.beta.threads.messages.create(
    #     thread_id=thread.id,
    #     role="user",
    #     content=f'I am a: {my_role} My question is: {my_question}'
    # )

    # Run the assistant
    if st.button("Ask your question!"):
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f'I am a: {my_role} My question is: {st.session_state.pending_question}'
        )
        my_run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=my_assistant.id,
            instructions=neurologist,
            )
        
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        # Periodically retrieve the Run to check on its status to see if it has moved to completed
        with st.spinner("Reviewing references..."):
            while my_run.status != "completed":
                keep_retrieving_run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=my_run.id
                )
                # st.write(f"Run status: {keep_retrieving_run.status}")

                if keep_retrieving_run.status == "completed":
                    # print("\n")
                    break
            all_messages = client.beta.threads.messages.list(
            thread_id=thread.id
            )

        with st.chat_message("user"):
            st.write(st.session_state.pending_question)
            
        with st.chat_message("assistant"):
            st.write(all_messages.data[0].content[0].text.value)
