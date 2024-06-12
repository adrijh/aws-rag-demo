from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_text_splitters import CharacterTextSplitter
from streamlit.runtime.uploaded_file_manager import UploadedFile
from langchain_core.vectorstores import VectorStore

from streamlit_app.utils.prompts import build_chatbot_prompt


def log_document(doc: str):
    print(doc)
    return doc

def build_rag_chain(vector_store: VectorStore):
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")

    if not vector_store:
        prompt = build_chatbot_prompt(rag=False)
        return (
            {"question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )


    prompt = build_chatbot_prompt(rag=True)
    retriever = vector_store.as_retriever()
    return (
        {"context": retriever | format_docs | log_document, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

def build_embeddings_model():
   model_name = "sentence-transformers/all-mpnet-base-v2"
   model_kwargs = {'device': 'cpu'}
   encode_kwargs = {'normalize_embeddings': False}
   return HuggingFaceEmbeddings(
       model_name=model_name,
       model_kwargs=model_kwargs,
       encode_kwargs=encode_kwargs
   )

def chunk_documents(documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 30):
   text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
   return text_splitter.split_documents(documents)

def transform_files_to_documents(
    uploaded_files: list[UploadedFile],
):
    documents = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.read().decode("utf-8")
        doc = Document(page_content=content, metadata={"filename": uploaded_file.name})
        documents.append(doc)

    return documents
