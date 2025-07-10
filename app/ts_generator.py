import openai
import os
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
# from dotenv import load_dotenv

# load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")
os.environ["OPENAI_API_KEY"]=os.getenv("OPENAI_API_KEY")
# Load your RAG knowledge base from a text file
rag_file_path = os.path.join(os.path.dirname(__file__), "rag_knowledge_base.txt")
loader = TextLoader(file_path=rag_file_path,encoding="utf-8")
documents = loader.load()

# Split documents for embedding
text_splitter = RecursiveCharacterTextSplitter(chunk_size=20000, chunk_overlap=200)
docs = text_splitter.split_documents(documents)

# Create vector store with OpenAI embeddings and Chroma
embedding = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(docs, embedding)

# Create retriever
retriever = vectorstore.as_retriever()
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o", temperature=0.4),
    chain_type="stuff",
    retriever=retriever,
)
def generate_ts_from_abap(abap_code: str) -> str:
    # Retrieve relevant documents (just content)
    retrieved_docs = retriever.get_relevant_documents(abap_code)
    retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    if not retrieved_context.strip():
        return "No relevant context found in the RAG base. Please verify the ABAP code or knowledge file."

    # Compose a structured prompt
    prompt_template = ChatPromptTemplate.from_template(
        "Given the following context and ABAP code, generate a detailed, minimum 1000-word technical specification in professional DOCX-compatible formatting using System message provided.\n\n"
        "Context:\n{context}\n\n"
        # "Context:\n{documents}\n\n"
        "ABAP Code:\n{abap_code}"
    )
    messages = prompt_template.format_messages(context=retrieved_context, abap_code=abap_code)

    # Query GPT
    llm = ChatOpenAI(model="gpt-4o", temperature=0.4)
    response = llm.invoke(messages)

    return response.content if hasattr(response, "content") else str(response)


# import os
# from dotenv import load_dotenv

# from langchain.prompts.chat import ChatPromptValue
# from langchain.schema import SystemMessage, HumanMessage
# from langchain.chains import RetrievalQA
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.document_loaders import TextLoader
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from langchain_chroma import Chroma

# # Load environment variables
# load_dotenv()
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# # File paths
# BASE_DIR = os.path.dirname(__file__)
# TEMPLATE_PATH = os.path.join(BASE_DIR, "ts_template.txt")  # The strict format/instruction file
# RAG_CONTEXT_PATH = os.path.join(BASE_DIR, "rag_knowledge_base.txt")  # The knowledge file

# # Load template and knowledge base
# with open(TEMPLATE_PATH, "r", encoding="utf-8") as file:
#     ts_template_instruction = file.read().strip()

# loader = TextLoader(file_path=RAG_CONTEXT_PATH, encoding="utf-8")
# raw_documents = loader.load()

# # Split and embed documents
# splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
# documents = splitter.split_documents(raw_documents)

# embedding_model = OpenAIEmbeddings()
# vector_store = Chroma.from_documents(documents, embedding_model)
# retriever = vector_store.as_retriever()

# # Initialize LLM
# llm = ChatOpenAI(model="gpt-4o", temperature=0.4)

# def generate_ts_from_abap(abap_code: str) -> str:
#     """
#     Generates a technical specification document using ABAP code and a strict TS template.
#     """
#     relevant_docs = retriever.get_relevant_documents(abap_code)
#     context = "\n\n".join(doc.page_content for doc in relevant_docs).strip()

#     if not context:
#         return "No relevant context found in the RAG base. Please verify the ABAP code or knowledge file."

#     # Compose system and user messages
#     system_message = SystemMessage(content=ts_template_instruction)

#     user_message = HumanMessage(content=(
#         "Using the following context and ABAP code, generate a detailed, minimum 1000-word technical specification "
#         "in Word-compatible formatting, strictly following the structure and rules described in the system message.\n\n"
#         f"Context:\n{context}\n\n"
#         f"ABAP Code:\n{abap_code}"
#     ))

#     # Format the chat prompt and invoke the model
#     chat_prompt = ChatPromptValue(messages=[system_message, user_message])
#     response = llm.invoke(chat_prompt)

#     return getattr(response, "content", str(response))
