import os

import streamlit as st
from langchain_core.vectorstores import VectorStore

from streamlit_app.utils.embeddings import build_rag_chain


class MainPanel:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

        st.header("Chat with GPT with your own RAG")

        if not os.getenv("OPENAI_API_KEY"):
            st.warning("Please enter an API Key to use the ChatBot")
        else:
            self.__init_message_history()
            self.__build_chatbot()


    def __init_message_history(self):
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

    def __build_chatbot(self):
        rag_chain = build_rag_chain(self.vector_store)

        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if not self.vector_store:
            st.error("There was a problem instantiating Vector Store")

        if prompt := st.chat_input("Enter your question here.."):
            st.session_state["messages"].append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response = rag_chain.invoke(prompt)
                st.session_state["messages"].append({"role": "assistant", "content": response})
                st.write(response)
