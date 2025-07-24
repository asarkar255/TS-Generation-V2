from langchain_core.messages import SystemMessage, HumanMessage

def extract_abap_explanation(abap_code: str) -> str:
    """
    Step 1: Use GPT to generate technical and functional explanation of ABAP code
    """
    explanation_prompt = [
        SystemMessage(content="You are an experienced SAP Techno-Functional Architect. "
                              "Explain the given ABAP code line-by-line in detail from both a technical and functional perspective."),
        HumanMessage(content=abap_code)
    ]

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    explanation_response = llm.invoke(explanation_prompt)
    return explanation_response.content if hasattr(explanation_response, "content") else str(explanation_response)


def generate_ts_from_abap(abap_code: str) -> str:
    """
    Step 2: Generate final Technical Specification from RAG + Explanation + Code
    """

    # Step 1: Generate explanation
    explanation = extract_abap_explanation(abap_code)

    # Step 2: Retrieve additional domain-specific context from RAG
    retrieved_docs = retriever.get_relevant_documents(abap_code)
    retrieved_context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    if not retrieved_context.strip():
        return "No relevant context found in the RAG base. Please verify the ABAP code or knowledge file."

    # Combine explanation and RAG content as context
    combined_context = f"### Technical & Functional Explanation:\n{explanation}\n\n### RAG Knowledge Base Context:\n{retrieved_context}"

    # Create prompt template for TSD generation
    prompt_template = ChatPromptTemplate.from_template(
        "You are an SAP ABAP Technical Architect. Based on the following explanation, RAG context, and ABAP code, "
        "generate a detailed and professionally formatted Technical Specification Document (minimum 2000 words) "
        "with DOCX-compatible formatting, section titles, and numbering.\n\n"
        "Context:\n{context}\n\n"
        "ABAP Code:\n{abap_code}"
    )
    messages = prompt_template.format_messages(context=combined_context, abap_code=abap_code)

    # Step 3: Generate the TSD
    llm = ChatOpenAI(model="gpt-4o", temperature=0.4)
    response = llm.invoke(messages)

    return response.content if hasattr(response, "content") else str(response)
