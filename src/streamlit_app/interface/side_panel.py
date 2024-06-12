import os

import streamlit as st
from langchain_core.vectorstores import VectorStore
from streamlit.runtime.uploaded_file_manager import UploadedFile

from streamlit_app.utils.embeddings import chunk_documents, transform_files_to_documents


class SidePanel:
    def __init__(
        self,
        vector_store: VectorStore,
    ):
        self.vector_store = vector_store
        self.chunk_size = 200
        self.chunk_overlap = 50

        self.build()

    def build(self):
        toggle = st.sidebar.checkbox("Use RAG")

        if toggle:
            self.build_toggle_panel()

        self.create_openai_key_field()

    def build_toggle_panel(self):
        st.sidebar.header("RAG Parameters")
        uploaded_files = st.sidebar.file_uploader("Upload an file", type=("txt", "md"), accept_multiple_files=True)
        self.chunk_size = st.sidebar.slider("Chunk Size", min_value=500, max_value=2000, value=1000)
        self.chunk_overlap = st.sidebar.slider("Chunk Overlap", min_value=0, max_value=100, value=25)

        if st.sidebar.button("Load"):
            self.upload_button_impl(uploaded_files)

    def upload_button_impl(self, uploaded_files: list[UploadedFile]| None):
        if uploaded_files:
            try:
                documents = transform_files_to_documents(uploaded_files)
                chunked_documents = chunk_documents(documents, self.chunk_size, self.chunk_overlap)
                self.vector_store.add_documents(chunked_documents)
                st.success(f"Uploaded {len(uploaded_files)} files successfully!")
            except Exception as e:
                st.error(f"There was a problem uploading files: {e}")
        else:
            st.sidebar.write("Please upload a file.")

    def create_openai_key_field(self):
        openai_api_key = st.sidebar.text_input(
            "OpenAI API Key",
            key="openai_api_key",
            type="password"
        )

        os.environ["OPENAI_API_KEY"] = openai_api_key
