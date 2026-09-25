import ollama
from sqlmodel import Session, select
from models import ResearchDocument
from database import engine

def query_biomedical_rag(user_question: str) -> str:
    context_texts = []
    with Session(engine) as session:
        docs = session.exec(select(ResearchDocument).where(ResearchDocument.is_processed == True)).all()
        for doc in docs:
            context_texts.append(f"Title: {doc.title}\nContent: {doc.content}")
    
    combined_context = "\n\n".join(context_texts)
    
    system_prompt = (
        "You are a biomedical research assistant. Answer the user's question "
        "using ONLY the provided context. If the answer is not in the context, "
        "say you do not have enough information."
    )
    
    user_prompt = f"Context:\n{combined_context}\n\nQuestion: {user_question}"
    
    response = ollama.chat(
        model='llama3.1',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
            ]
        )
    return response['message']['content']