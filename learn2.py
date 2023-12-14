import json
import time
import openai
import os
import streamlit as st
from langchain.utilities import DuckDuckGoSearchAPIWrapper
import requests
import time
# from retrying import retry
from prompts import *
import os 
from io import StringIO, BytesIO
from langchain.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.vectorstores import FAISS
from langchain.callbacks import get_openai_callback
# from langchain.llms import OpenAI
import streamlit as st
from prompts import *
# import fitz
from io import StringIO      
from openai import OpenAI


disclaimer = """**Disclaimer:** This is a tool to teach students"""

st.set_page_config(page_title='My Tutor', layout = 'centered', page_icon = ':stethoscope:', initial_sidebar_state = 'auto')
st.title("Learn!")
st.write("ALPHA version 0.5")


with st.expander('Important Disclaimer'):
    st.write("Author: David Liebovitz")
    st.info(disclaimer)
    st.session_state.temp = st.slider("Select temperature (Higher values more creative but tangential and more error prone)", 0.0, 1.0, 0.3, 0.01)
    st.write("Last updated 10/9/23")
    

    
@st.cache_data
def create_retriever(texts, name, save_vectorstore=False):
    
    embeddings = OpenAIEmbeddings(model = "text-embedding-ada-002",
                                  openai_api_base = "https://api.openai.com/v1/",
                                  openai_api_key = st.secrets['OPENAI_API_KEY']
                                  )
    try:
        vectorstore = FAISS.from_texts(texts, embeddings)
        if save_vectorstore:
            vectorstore.save_local(f"{name}.faiss")
    except (IndexError, ValueError) as e:
        st.error(f"Error creating vectorstore: {e}")
        return
    retriever = vectorstore.as_retriever(k=5)

    return retriever

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

def answer_using_prefix(prefix, sample_question, sample_answer, my_ask, temperature, history_context, model, print = True):
    # st.write('yes the function is being used!')
    messages_blank = []
    messages = update_messages(
        messages = messages_blank, 
        system_content=f'{prefix}; Sample question: {sample_question} Sample response: {sample_answer} Preceding conversation: {history_context}', 
        assistant_content='',
        user_content=my_ask,
        )
    # st.write(messages)
    # st.write('here is the model: ' + model)
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
    
def set_llm_chat(model, temperature):
    if model == "openai/gpt-3.5-turbo":
        model = "gpt-3.5-turbo"
    if model == "openai/gpt-3.5-turbo-16k":
        model = "gpt-3.5-turbo-16k"
    if model == "openai/gpt-4":
        model = "gpt-4"
    if model == "gpt-4" or model == "gpt-3.5-turbo" or model == "gpt-3.5-turbo-16k":
        return ChatOpenAI(model=model, openai_api_base = "https://api.openai.com/v1/", openai_api_key = st.secrets["OPENAI_API_KEY"], temperature=temperature)
    else:
        headers={ "HTTP-Referer": "https://fsm-gpt-med-ed.streamlit.app", # To identify your app
          "X-Title": "GPT and Med Ed"}
        return ChatOpenAI(model = model, openai_api_base = "https://openrouter.ai/api/v1", openai_api_key = st.secrets["OPENROUTER_API_KEY"], temperature=temperature, max_tokens = 500, headers=headers)

@st.cache_data  # Updated decorator name from cache_data to cache
def load_docs(files):
    all_text = ""
    for file in files:
        file_extension = os.path.splitext(file.name)[1]
        if file_extension == ".pdf":
            pdf_data = file.read()  # Read the file into bytes
            pdf_reader = fitz.open("pdf", pdf_data)  # Open the PDF from bytes
            text = ""
            for page in pdf_reader:
                text += page.get_text()
            all_text += text

        elif file_extension == ".txt":
            stringio = StringIO(file.getvalue().decode("utf-8"))
            text = stringio.read()
            all_text += text
        else:
            st.warning('Please provide txt or pdf.', icon="⚠️")
    return all_text 

@st.cache_data
def split_texts(text, chunk_size, overlap, split_method):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=overlap)

    splits = text_splitter.split_text(text)
    if not splits:
        # st.error("Failed to split document")
        st.stop()

    return splits


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
    
if "tutor_user_question" not in st.session_state:
    st.session_state["tutor_user_question"] = []

if "tutor_user_answer" not in st.session_state:
    st.session_state["tutor_user_answer"] = []
    
if "history" not in st.session_state:
    st.session_state["history"] = ""


if check_password():
    
    
    # st.header("Chat about Colon Cancer Screening!")
    # st.info("""Embeddings, i.e., reading your file(s) and converting words to numbers, are created using an OpenAI [embedding model](https://platform.openai.com/docs/guides/embeddings/what-are-embeddings) and indexed for searching. Then,
    #         your selected model (e.g., gpt-3.5-turbo-16k) is used to answer your questions.""")
    # with st.sidebar.expander("LLM Selection - default GPT-3.5-turbo-16k"):
    #     st.session_state.model = st.selectbox("Model Options", ("openai/gpt-3.5-turbo", "openai/gpt-3.5-turbo-16k", "openai/gpt-4", "openai/gpt-4-1106-preview"), index=3)
    
    # st.sidebar.markdown('[Article 1](https://www.ncbi.nlm.nih.gov/books/NBK570913/)')
    # st.sidebar.markdown('[Article 2](https://jamanetwork.com/journals/jama/fullarticle/2779985)')
    # st.sidebar.write("And, patient education materals from Northwestern Medicine.")
    # Reenable in order to create another vectorstore!    
        
    # uploaded_files = []
    # uploaded_files = st.file_uploader("Choose your file(s)", accept_multiple_files=True)
    # vectorstore_name = st.text_input("Please enter a name for your vectorstore (e.g., colon_ca):")

    # if uploaded_files is not None:
    #     documents = load_docs(uploaded_files)
    #     texts = split_texts(documents, chunk_size=1250,
    #                                 overlap=200, split_method="splitter_type")

    #     retriever = create_retriever(texts, vectorstore_name, save_vectorstore=True)

    #     # openai.api_base = "https://openrouter.ai/api/v1"
    #     # openai.api_key = st.secrets["OPENROUTER_API_KEY"]

    #     llm = set_llm_chat(model=st.session_state.model, temperature=st.session_state.temp)
    #     # llm = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_base = "https://api.openai.com/v1/")

    #     qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)

    # else:
    #     st.warning("No files uploaded.")       
    #     st.write("Ready to answer your questions!")
    
    # Disable section below if you'd like to make new vectorstores!
    
    embeddings = OpenAIEmbeddings()
    if "vectorstore" not in st.session_state:
        st.session_state["vectorstore"] = FAISS.load_local("bio.faiss", embeddings)
        


    # llm = set_llm_chat(model=st.session_state.model, temperature=st.session_state.temp)

    # qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=st.session_state.retriever)



    # tutor_chat_option = st.radio("Select an Option", ("For Patients", "For Clinicians"))
    # if tutor_chat_option == "For Patients":
    #     reading_level = "5th grade"
    #     bio_tutor = bio_tutor_patient
    #     user = "patient"
    # if tutor_chat_option == "For Clinicians":
    #     reading_level = "medical professional"
    #     bio_tutor = bio_tutor_clinician
    #     user = "clinician"
             


    name = st.text_input("Please enter your first name only:")
    if st.button("Let's Learn"):
        st.session_state.history = ""   
        initial_question = "Teach me about the cell"
        docs = st.session_state.vectorstore.similarity_search("Teach me about the cell")
        full_question = f'Username: {name} My question: {initial_question} /n/n **Respond `Hi {name},` and use the reference {docs} for topics and appropriate level of detail for a high school freshman. **Accuracy is essential** teaching!'
        with st.spinner("Thinking..."):
            answer_for_learner = answer_using_prefix(prefix = bio_tutor, sample_question = "", sample_answer = "", my_ask = full_question, temperature = st.session_state.temp, history_context = st.session_state.history, model = st.session_state.model, print = True)
        st.session_state.history += (f'Question: {initial_question} AI answer: {answer_for_learner}')   
        st.session_state.tutor_user_question.append(initial_question)
        st.session_state.tutor_user_answer.append(answer_for_learner)
        
            
    user_question = st.text_input("Please ask a followup or new question:")
    
        

    if st.button("Ask more questions biology!"):
        # index_context = f'Use only the reference document for knowledge. Question: {user_question}'
        docs = st.session_state.vectorstore.similarity_search(user_question)
        user_question_context = f"User: {name},  with a follow-up question: {user_question} /n/n Answer focusing on {docs} for topics to explain at a high school level. Address the user using the right name, {name}, in your response, e.g., {name}, .... **Accuracy is essential** for education."
        # chain = load_qa_chain(llm=llm, chain_type="stuff")
        # with get_openai_callback() as cb:
        #     answer_for_learner = chain.run(input_documents = docs, question = chain)
        # name
        with st.spinner("Thinking..."): 
            answer_for_learner = answer_using_prefix(prefix = bio_tutor, sample_question = "", sample_answer = "", my_ask = user_question_context, temperature = st.session_state.temp, history_context = st.session_state.history, model = st.session_state.model, print = True)
        # Append the user question and tutor answer to the session state lists
        st.session_state.tutor_user_question.append(f'{name}: {user_question}')
        st.session_state.tutor_user_answer.append(answer_for_learner)
        st.session_state.history += (f'{name}: {user_question} AI answer: {answer_for_learner}')

        # Display the tutor answer
        # st.write(answer_for_learner)

        # Prepare the download string for the tutor questions
        tutor_download_str = f"{disclaimer}\n\ntutor Questions and Answers:\n\n"
        for i in range(len(st.session_state.tutor_user_question)):
            tutor_download_str += f"{st.session_state.tutor_user_question[i]}\n"
            tutor_download_str += f"Answer: {st.session_state.tutor_user_answer[i]}\n\n"
            st.session_state.current_thread = tutor_download_str

        # Display the expander section with the full thread of questions and answers
        
    if st.session_state.history != "":    
        with st.sidebar.expander("Your Conversation", expanded=False):
            for i in range(len(st.session_state.tutor_user_question)):
                st.info(f"{st.session_state.tutor_user_question[i]}", icon="🧐")
                st.success(f"Answer: {st.session_state.tutor_user_answer[i]}", icon="🤖")

            if st.session_state.current_thread != '':
                st.download_button('Download', st.session_state.current_thread, key='tutor_questions')
    
    if st.sidebar.button("Start a new conversation"):
        st.session_state.history = ""