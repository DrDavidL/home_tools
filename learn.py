
import streamlit as st
import os 
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import streamlit as st
from prompts import * 
from openai import OpenAI



st.set_page_config(page_title='My Tutor', layout = 'centered', page_icon = ':stethoscope:', initial_sidebar_state = 'auto')
st.title("Learn!")
st.write("ALPHA version 0.5")


with st.expander('Important Disclaimer'):
    st.write("Author: David Liebovitz")
    st.info(disclaimer)
    st.session_state.temp = st.slider("Select temperature (Higher values more creative but tangential and more error prone)", 0.0, 1.0, 0.3, 0.01)
    st.write("Last updated 12/9/23")
    

def update_messages(messages, system_content=None, assistant_content=None, user_content=None):
    """
    Updates a list of message dictionaries with new system, user, and assistant content.

    :param messages: List of message dictionaries with keys 'role' and 'content'.
    :param system_content: Optional new content for the system message.
    :param user_content: Optional new content for the user message.
    :param assistant_content: Optional new content for the assistant message.
    :return: Updated list of message dictionaries.
    """

    # Update system message or add it if it does not exist
    system_message = next((message for message in messages if message['role'] == 'system'), None)
    if system_message is not None:
        if system_content is not None:
            system_message['content'] = system_content
    else:
        if system_content is not None:
            messages.append({"role": "system", "content": system_content})

    # Add assistant message if provided
    if assistant_content is not None:
        messages.append({"role": "assistant", "content": assistant_content})

    # Add user message if provided
    if user_content is not None:
        messages.append({"role": "user", "content": user_content})

    return messages

def gen_response(messages, temperature, model, print = True):
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(
        api_key=api_key,
    )
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": print,
    }
    try:    
        completion = client.chat.completions.create(**params)
    except Exception as e:
        st.write(e)
        st.write(f'Here were the params: {params}')
        return None

    placeholder = st.empty()
    full_response = ''
    for chunk in completion:
        if chunk.choices[0].delta.content is not None:
            full_response += chunk.choices[0].delta.content
            # full_response.append(chunk.choices[0].delta.content)
            placeholder.markdown(full_response)
    placeholder.markdown(full_response)
    return full_response

def answer_using_prefix(prefix, sample_question, sample_answer, my_ask, temperature, message_thread_context, model, print = True):
    messages_blank = []
    messages = update_messages(
        messages = messages_blank, 
        system_content=f'{prefix}; Sample question: {sample_question} Sample response: {sample_answer} Preceding conversation: {message_thread_context}', 
        assistant_content='',
        user_content=my_ask,
        )

    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(
        api_key=api_key,
    )
    params = {
        "model": "gpt-3.5-turbo-1106",
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    # st.write(f'here are the params: {params}')
    try:    
        completion = client.chat.completions.create(**params)
    except Exception as e:
        st.write(e)
        st.write(f'Here were the params: {params}')
        return None

    placeholder = st.empty()
    full_response = ''
    for chunk in completion:
        if chunk.choices[0].delta.content is not None:
            full_response += chunk.choices[0].delta.content
            # full_response.append(chunk.choices[0].delta.content)
            placeholder.markdown(full_response)
    placeholder.markdown(full_response)
    return full_response

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            # del st.session_state["password"]  # don't store password
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
    



if "current_thread" not in st.session_state:
    st.session_state["current_thread"] = ""


if "last_answer" not in st.session_state:
    st.session_state["last_answer"] = []


if "temp" not in st.session_state:
    st.session_state["temp"] = 0.3
    
if "your_question" not in st.session_state:
    st.session_state["your_question"] = ""
    
if "texts" not in st.session_state:
    st.session_state["texts"] = ""
    
if "retriever" not in st.session_state:
    st.session_state["retriever"] = ""
    
if "model" not in st.session_state:
    st.session_state["model"] = "openai/gpt-3.5-turbo-16k"
    
if "tutor_user_topic" not in st.session_state:
    st.session_state["tutor_user_topic"] = []

if "tutor_user_answer" not in st.session_state:
    st.session_state["tutor_user_answer"] = []
    
if "message_thread" not in st.session_state:
    st.session_state["message_thread"] = []


if check_password():
    

    
    embeddings = OpenAIEmbeddings()
    if "vectorstore" not in st.session_state:
        st.session_state["vectorstore"] = FAISS.load_local("bio.faiss", embeddings)
        



    
    # if st.button("Let's Learn"):
    #     st.session_state.message_thread = ""   
    #     initial_question = "Teach me about the cell"
    #     docs = st.session_state.vectorstore.similarity_search("Teach me about the cell")
    #     full_question = f'Username: {name} My input: {initial_question} /n/n **Respond `Hi {name},` and use the reference {docs} for topics and appropriate level of detail for a high school freshman. **Accuracy is essential** teaching!'
    #     with st.spinner("Thinking..."):
    #         answer_for_learner = answer_using_prefix(prefix = bio_tutor, sample_question = "", sample_answer = "", my_ask = full_question, temperature = st.session_state.temp, message_thread_context = st.session_state.message_thread, model = st.session_state.model, print = True)
    #     st.session_state.message_thread += (f'Question: {initial_question} AI answer: {answer_for_learner}')   
    #     st.session_state.tutor_user_topic.append(initial_question)
    #     st.session_state.tutor_user_answer.append(answer_for_learner)
        
    model = st.sidebar.selectbox("Select a model", ["gpt-4-1106-preview", "gpt-3.5-turbo-1106", ])
    
    name = st.text_input("Please enter your first name:")
    user_input = st.text_input("Your input here, ask to be tough, ask for test questions, submit your responses, etc.:")    
    system_context = bio_tutor.format(name = name, outline = biology_outline)
    if st.session_state.message_thread == []:
        st.session_state.message_thread = [{"role": "system", "content": system_context}]
        

    if st.button("Learn about biology!"):
        st.session_state.message_thread.append({"role": "user", "content": user_input})
        with st.spinner("Thinking..."): 
            answer_for_learner = gen_response(messages = st.session_state.message_thread, temperature = st.session_state.temp, model = model, print = True)
        st.session_state.tutor_user_topic.append(f'{name}: {user_input}')
        st.session_state.tutor_user_answer.append(answer_for_learner)        
        st.session_state.message_thread.append({"role": "assistant", "content": answer_for_learner})
        

        # Display the tutor answer
        # st.write(answer_for_learner)

        # Prepare the download string for the tutor questions
        tutor_download_str = f"{disclaimer}\n\ntutor Questions and Answers:\n\n"
        for i in range(len(st.session_state.tutor_user_topic)):
            tutor_download_str += f"{st.session_state.tutor_user_topic[i]}\n"
            tutor_download_str += f"Answer: {st.session_state.tutor_user_answer[i]}\n\n"
            st.session_state.current_thread = tutor_download_str

        # Display the expander section with the full thread of questions and answers
        
    if st.session_state.message_thread != "":    
        with st.sidebar.expander("Your Conversation", expanded=False):
            for i in range(len(st.session_state.tutor_user_topic)):
                st.info(f"{st.session_state.tutor_user_topic[i]}", icon="🧐")
                st.success(f"Answer: {st.session_state.tutor_user_answer[i]}", icon="🤖")

            if st.session_state.current_thread != '':
                st.download_button('Download', st.session_state.current_thread, key='tutor_questions')
    
    if st.sidebar.button("Start a new conversation"):
        st.session_state.message_thread = []