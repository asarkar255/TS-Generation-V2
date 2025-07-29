import os
import re
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.messages import SystemMessage, HumanMessage
from app.abap_explanation import extract_abap_explanation

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
 load_dotenv(dotenv_path=env_path)
else:
    print(f"Warning: .env file not found at {env_path}. Environment variables may not be set correctly.")
    
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Load RAG knowledge base
rag_file_path = os.path.join(os.path.dirname(__file__), "rag_knowledge_base.txt")
loader = TextLoader(file_path=rag_file_path, encoding="utf-8")
documents = loader.load()

# Create chunks for vector search
text_splitter = RecursiveCharacterTextSplitter(chunk_size=20000, chunk_overlap=200)
docs = text_splitter.split_documents(documents)

embedding = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(docs, embedding)
retriever = vectorstore.as_retriever()


# # ✅ Step 1: Extract line-by-line explanation
# def extract_abap_explanation(abap_code: str) -> str:
#     """
#     Generates a detailed line-by-line technical and functional explanation of the ABAP code.
#     """
#     explanation_prompt = [
#         SystemMessage(content="You are an experienced SAP Techno-Functional Solution Architect. "
#                               "Explain the given ABAP code line-by-line in detail from both a technical and functional perspective.\n"
#                               "Output should be like below:\n"
#                               "Selection Screen Parameters:\n(Go through all the selection scrren parameters and select-options in the ABAP code and explain them in detail THIS IS MANDATORY)\n"
#                               "DATA SELECTION:Technically explain each and every data select query in the ABAP code.\n"
#                               "Technical: Technical Explanation of selection screen PARAMETERS and SELECT-OPTIONS\n"
#                               "Technical: Technical Explanation of line n\n"
#                               "Functional: Functional Explanation of line n\n"
#                               "Ensure to cover all lines in the ABAP code."),
#         HumanMessage(content=abap_code)
#     ]

#     llm = ChatOpenAI(model="gpt-4.1", temperature=0)
#     explanation_response = llm.invoke(explanation_prompt)
#     return explanation_response.content if hasattr(explanation_response, "content") else str(explanation_response)



# ✅ Step 3: Generate formatted Technical + Functional Description
def generate_description_from_explanation(explanation: str) -> str:
    prompt = [
        SystemMessage(content="You are a senior SAP documentation specialist. From the explanation below, create:\n"
                              "- A clear Technical Description (100–150 words)\n"
                              "- A clear Functional Description (100–150 words)\n"
                              "Ensure MS Word-compatible formatting."),
        HumanMessage(content=explanation)
    ]
    llm = ChatOpenAI(model="gpt-4.1", temperature=0)
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


# ✅ Step 4: Final TSD generator
def generate_ts_from_abap(abap_code: str) -> str:
    explanation = extract_abap_explanation(abap_code)
    formatted_description = generate_description_from_explanation(explanation)

    retrieved_docs = retriever.get_relevant_documents(abap_code)
    retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    if not retrieved_context.strip():
        return "No relevant context found in RAG knowledge base."

    # Final prompt for TSD generation
    prompt_template = ChatPromptTemplate.from_template(
        "You are an SAP ABAP Technical Architect. Based on the explanation, formatted description, version table, RAG context, and ABAP code, "
        "generate a complete and professionally formatted Technical Specification Document (min 2000 words). "
        "Use all explanation lines in the Pseudo Code section.\n\n"
        "RAG Context:\n{context}\n\n"
        "ABAP Code:\n{abap_code}\n\n"
        "Explanation:\n{explanation}\n\n"
        "Formatted Technical + Functional Description:\n{description}"
    )

    messages = prompt_template.format_messages(
        context=retrieved_context,
        abap_code=abap_code,
        explanation=explanation,
        description=formatted_description,

    )

    llm = ChatOpenAI(model="gpt-4.1", temperature=0)
    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)
