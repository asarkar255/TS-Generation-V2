import os
import re
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()
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


# ✅ Step 1: Extract line-by-line explanation
def extract_abap_explanation(abap_code: str) -> str:
    """
    Generates a detailed line-by-line technical and functional explanation of the ABAP code.
    """
    explanation_prompt = [
        SystemMessage(content="You are an experienced SAP Techno-Functional Solution Architect. "
                              "Explain the given ABAP code line-by-line in detail from both a technical and functional perspective.\n"
                              "Output should be like below:\n"
                              "Selection Screen Parameters:\n"
                              "Technical: Technical Explanation of selection screen PARAMETERS and SELECT-OPTIONS\n"
                              "Technical: Technical Explanation of line n\n"
                              "Functional: Functional Explanation of line n\n"
                              "Ensure to cover all lines in the ABAP code."),
        HumanMessage(content=abap_code)
    ]

    llm = ChatOpenAI(model="gpt-4.1", temperature=0.3)
    explanation_response = llm.invoke(explanation_prompt)
    return explanation_response.content if hasattr(explanation_response, "content") else str(explanation_response)


# ✅ Step 2: Extract version history from ABAP comments
def extract_version_history(abap_code: str) -> str:
    """
    Extracts version history entries from ABAP comments and formats them as a Markdown-compatible table.
    """
    pattern = re.compile(r"\*\s*(Changed by|Modified by|Correction(?: by)?)(.*)", re.IGNORECASE)
    version_table = []
    version_no = 1

    for line in abap_code.splitlines():
        match = pattern.search(line)
        if match:
            entry_type = match.group(1).strip().capitalize()
            details = match.group(2).strip().replace(":", " -", 1)
            changed_by = "Unknown"
            change_date = "Unknown"
            description = details

            # Attempt to extract name and date
            by_match = re.search(r"by\s+([\w\s]+)\s+on\s+(\d{4}-\d{2}-\d{2})", line, re.IGNORECASE)
            if by_match:
                changed_by = by_match.group(1).strip()
                change_date = by_match.group(2).strip()
            else:
                name_match = re.search(r"by\s+([\w\s]+)", line, re.IGNORECASE)
                if name_match:
                    changed_by = name_match.group(1).strip()

            version_table.append(f"| {version_no}.0 | {changed_by} | {change_date} | {description} |")
            version_no += 1

    if not version_table:
        version_table.append("| 1.0 | Initial Developer | N/A | Initial Version |")

    markdown_table = (
        "\n| Version No. | Changed By | Change Date | Description of Change |\n"
        "|-------------|------------|-------------|------------------------|\n" +
        "\n".join(version_table)
    )

    return markdown_table


# ✅ Step 3: Generate formatted Technical + Functional Description
def generate_description_from_explanation(explanation: str) -> str:
    prompt = [
        SystemMessage(content="You are a senior SAP documentation specialist. From the explanation below, create:\n"
                              "- A clear Technical Description (100–150 words)\n"
                              "- A clear Functional Description (100–150 words)\n"
                              "Ensure MS Word-compatible formatting."),
        HumanMessage(content=explanation)
    ]
    llm = ChatOpenAI(model="gpt-4.1", temperature=0.3)
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


# ✅ Step 4: Final TSD generator
def generate_ts_from_abap(abap_code: str) -> str:
    explanation = extract_abap_explanation(abap_code)
    formatted_description = generate_description_from_explanation(explanation)
    version_table = extract_version_history(abap_code)

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
        "Version History Table:\n{version_table}\n\n"
        "Formatted Technical + Functional Description:\n{description}"
    )

    messages = prompt_template.format_messages(
        context=retrieved_context,
        abap_code=abap_code,
        explanation=explanation,
        description=formatted_description,
        version_table=version_table
    )

    llm = ChatOpenAI(model="gpt-4.1", temperature=0.4)
    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)
