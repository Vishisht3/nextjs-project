import time
from concurrent.futures import ThreadPoolExecutor
from sqlmodel import Session
from database import engine
from models import ResearchDocument


executor = ThreadPoolExecutor(max_workers=4)

def process_document_background(doc_id: int):
    print(f"[Worker] Starting processing for Document ID: {doc_id}")
    with Session(engine) as session:
        doc = session.get(ResearchDocument, doc_id)
        if not doc:
            print(f"[Worker] Document {doc_id} not found.")
            return

        time.sleep(3)

        doc.is_processed = True
        session.add(doc)
        session.commit()
        print(f"[Worker Thread] Successfully processed and indexed Document ID: {doc_id}")

def enqueue_document_processing(doc_id: int):
    executor.submit(process_document_background, doc_id)