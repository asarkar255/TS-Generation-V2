import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Step 1: Load RAG knowledge base
rag_file_path = os.path.join(os.path.dirname(__file__), "rag_knowledge_base.txt")
loader = TextLoader(file_path=rag_file_path, encoding="utf-8")
documents = loader.load()

# Step 2: Create document chunks for vector embedding
text_splitter = RecursiveCharacterTextSplitter(chunk_size=20000, chunk_overlap=200)
docs = text_splitter.split_documents(documents)

# Step 3: Create vectorstore retriever
embedding = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(docs, embedding)
retriever = vectorstore.as_retriever()

# Step 4: Explanation generator
def extract_abap_explanation(abap_code: str) -> str:
    """
    Generates a detailed line-by-line technical and functional explanation of the ABAP code.
    """
    explanation_prompt = [
        SystemMessage(content="You are an experienced SAP Techno-Functional Solution Architect. "
                              "Explain the given ABAP code line-by-line in detail from both a technical and functional perspective."
                              "Output should be like below:\n"
                              "Selection Screen Parameters:\n"
                              "Technical: Technical Explanation of selection screen parameters\n"
                              "SAP Code Line 1:\n"
                              "Technical: Technical Explanation of line 1\n"
                              "Functional: Functional Explanation of line 1\n"
                              "SAP Code Line 2:\n"
                              "Technical: Technical Explanation of line 2\n"  
                              "Functional: Functional Explanation of line 2\n"
                                ),
        HumanMessage(content=abap_code)
    ]

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    explanation_response = llm.invoke(explanation_prompt)
    return explanation_response.content if hasattr(explanation_response, "content") else str(explanation_response)

# Step 5: Final TSD Generator
def generate_ts_from_abap(abap_code: str) -> str:
    """
    Generates a detailed Technical Specification from ABAP code using both explanation and RAG.
    """

    # Part 1: Get technical and functional explanation
    explanation = extract_abap_explanation(abap_code)

    # Part 2: Retrieve relevant context from RAG
    retrieved_docs = retriever.get_relevant_documents(abap_code)
    retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    if not retrieved_context.strip():
        return "No relevant context found in the RAG base. Please verify the ABAP code or knowledge file."

    # Combine context


    # Prompt to generate TSD
    prompt_template = ChatPromptTemplate.from_template(
        "You are an SAP ABAP Technical Architect. Based on the following explanation, RAG contextand ABAP code, "
        "generate a detailed and professionally formatted Technical Specification Document (minimum 2000 words) "
        "Use all lines from explanation to create Pseudo Code section of TSD."
        "with DOCX-compatible formatting, section titles, and numbering.\n\n"
        "Context:\n{context}\n\n"
        "ABAP Code:\n{abap_code}"
        "Explanation:\n{explanation}"
    )

    messages = prompt_template.format_messages(context=retrieved_context , abap_code=abap_code, explanation=explanation)

    # Call LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0.4)
    response = llm.invoke(messages)

    final_tsd = response.content if hasattr(response, "content") else str(response)

    return final_tsd
