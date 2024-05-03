import os
from dotenv import load_dotenv
import boto3
from datetime import datetime
import streamlit as st

# Load environment variables from .env file
load_dotenv()

# Configuration and constants
AGENT_ALIAS_ID = os.getenv("AGENT_ALIAS_ID")
AGENT_ID = os.getenv("AGENT_ID")

# Sample questions
sample_questions = [
    "What assets are available?",
    "What is the current RPM value for turbine 2?",
    "What is the average RPM value for turbine 2, aggregated by hour?",
    "Which turbine has the highest RPM value and what is it?"
]

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(datetime.now().strftime("%Y%m%d%H%M%S"))
if "messages" not in st.session_state:
    st.session_state.messages = []

# Configure the Bedrock Agent Runtime client
def create_bedrock_agent_runtime_client():
    if os.getenv("AWS_PROFILE") and os.getenv("AWS_REGION"):
        # Use AWS profile and region from .env file
        session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"))
        client = session.client(
            service_name="bedrock-agent-runtime",
            region_name=os.getenv("AWS_REGION"),
        )
    else:
        # Use default credentials and region from IAM role
        client = boto3.client(service_name="bedrock-agent-runtime")
    
    return client

bedrock_agent_runtime_client = create_bedrock_agent_runtime_client()

# Function to display chat history
def display_chat_history():
    chat_history_container = st.container()
    with chat_history_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and message.get("trace"):
                    with st.expander("Trace"):
                        st.json(message["trace"], expanded=False)
        chat_history_container.empty()

# Function to handle user input
def handle_user_input():
    prompt = st.session_state.user_input
    st.session_state.messages.append({"role": "user", "content": prompt})

    response_text, trace = invoke_agent(prompt, st.session_state.get("enable_trace", False))
    st.session_state.messages.append({"role": "assistant", "content": response_text, "trace": trace})

    st.session_state.user_input = ""  # Clear the user input

# Function to invoke the agent
def invoke_agent(prompt, enable_trace):
    response = bedrock_agent_runtime_client.invoke_agent(
        agentAliasId=AGENT_ALIAS_ID,
        agentId=AGENT_ID,
        enableTrace=enable_trace,
        inputText=prompt,
        sessionId=st.session_state.session_id
    )

    trace = []
    response_text = ""
    for event in response["completion"]:
        if "trace" in event:
            trace.append(event["trace"])
        elif "chunk" in event:
            response_text += event["chunk"]["bytes"].decode("utf-8")

    return response_text, trace if enable_trace else None

# Function to reset chat history and session
def reset_chat():
    st.session_state.messages = []
    st.session_state.session_id = str(datetime.now().strftime("%Y%m%d%H%M%S"))

# Streamlit app
def main():
    st.title("Industrial Conversational Agent :robot_face:")

    # Sidebar
    with st.sidebar:
        st.subheader("Sample questions:")
        for sample_question in sample_questions:
            if st.button(sample_question):
                st.session_state.user_input = sample_question
                handle_user_input()

        st.checkbox("Enable Trace", key="enable_trace")
        if st.button("Reset Chat"):
            reset_chat()
            st.rerun()

    # Chat history
    st.subheader("Conversation")
    display_chat_history()

    # User input
    st.text_input("Ask a question", key="user_input", on_change=handle_user_input)

if __name__ == "__main__":
    main()