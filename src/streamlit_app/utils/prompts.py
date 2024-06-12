from langchain_core.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.prompts.prompt import PromptTemplate


def build_chatbot_prompt(rag: bool = False):
    rag_prompt=PromptTemplate(
        input_variables=["context", "question"],
        template="""
            Answer the following question making use of the given context.
            If you don't know the answer, just say you don't know.

            -----------------
            Question:
            {question}

            -----------------
            Context:
            {context}
        """
    )

    no_rag_prompt=PromptTemplate(
        input_variables=["question"],
        template="""
            Answer the following question.
            If you don't know the answer, just say you don't know.

            -----------------
            Question:
            {question}
        """
    )

    if rag:
        prompt = rag_prompt
        input_variables=["context", "question"]
    else:
        prompt = no_rag_prompt
        input_variables=["question"]

    return ChatPromptTemplate(
        input_variables=input_variables,
        messages=[HumanMessagePromptTemplate(prompt=prompt)]
    )
