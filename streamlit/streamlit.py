import streamlit as st
import requests
import os
import json
AI_CHATBOT_URL = os.getenv("AI_CHATBOT_URL", "http://35.240.233.98:7000")
top_k = 11
# App Config
st.set_page_config(page_title="Sacombank ChatBot", page_icon="🦜")

if "chat_history" not in st.session_state:
    st.session_state.full_chat_history = [{"role": "assistant", "content": "Hello! May I help you?"}]
    st.session_state.chat_history = [{"role": "assistant", "content": "Hello! May I help you?"}]
    st.session_state.summary_history = ""
previous_summary_history = st.session_state.summary_history
# Conversation
for message in st.session_state.full_chat_history:
    MESSAGE_TYPE = "AI" if message["role"] == "assistant" else "Human"
    with st.chat_message(MESSAGE_TYPE):
        st.write(message["content"])

user_query = st.chat_input("Type your message ✍")
if user_query is not None and user_query != "":
    with st.chat_message("Human"):
        st.write(user_query)
    response = requests.post(
        url=AI_CHATBOT_URL+"/chat",
        json={
            "content": user_query,
            "histories": st.session_state.chat_history,
            "summary": previous_summary_history
        },
        headers={"Content-Type": "application/json"},
        verify=False
    )
    print(response)
    print(response.json())
    content = response.json()["data"]["content"]
    #print("content: " + content)
    #summary = response.json()["data"]["summary_history"]
    with st.chat_message("AI"):
        st.write(content)
    #print(st.session_state.chat_history)
    st.session_state.full_chat_history.append({"role": "user", "content": user_query})
    st.session_state.full_chat_history.append({"role": "assistant", "content": content})
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    st.session_state.chat_history.append({"role": "assistant", "content": content})
    if (len(st.session_state.chat_history) == top_k and len(st.session_state.chat_history) != 0):
        previous_chat_history = st.session_state.chat_history[:top_k//2]

        previous_chat_history.append({"role":"previous_summary_history", "content": previous_summary_history})
        #del st.session_state.chat_history[:int(top_k/2)]
        st.session_state.summary_history = requests.post(
            url=AI_CHATBOT_URL+"/summary",
            data=json.dumps({
                #"histories": previous_chat_history.append({"role":"previous_summary_history", "content": previous_summary_history})
                #"histories": st.session_state.chat_history[-top_k:]
                "histories": previous_chat_history
            })
        ).text
        print(previous_chat_history)
        del st.session_state.chat_history[:top_k//2]

    print("pre sum: " + previous_summary_history)
    print("Summary: " + st.session_state.summary_history)