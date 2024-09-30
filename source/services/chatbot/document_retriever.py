from langfuse.decorators import observe
from utils.log_utils import get_logger
from typing import List, Dict, Any, Set
from schemas.document import Document

# from rerankers.documents import Document as RerankDocument
from external_access.milvus_connect import (
    initialize_milvus_connection,
    load_collection,
    search,
)
from haystack import Document as HaystackDocument
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore
from sentence_transformers import CrossEncoder, SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
from pyvi.ViTokenizer import tokenize
import numpy as np


logger = get_logger(__name__)
class DocumentRetriever:
    def __init__(self) -> None:
        initialize_milvus_connection()
        self.collection = load_collection("Sacombank_Knowledge")

        documents: List[HaystackDocument] = []
        milvusDocuments: List[Any] = self.collection.query(
            expr="",
            limit=16384,
            output_fields=[
                "page_content",
                "text",
                "file_name",
                "file_directory",
            ],
        )
        for item in milvusDocuments:
            documents.append(
                HaystackDocument(
                    id=item["chunk_id"],
                    content=item["text"],
                    meta={"entity": item},
                )
            )
        self.bm25Retriever = InMemoryBM25Retriever(
            document_store=InMemoryDocumentStore()
        )
        self.bm25Retriever.document_store.write_documents(documents)

    @observe(name="DocumentRetriever")
    def run(self, query: str, query_embbedding: List[float]) -> List[Document]:
        results1: List[Document] = self.semantic_search(query_embbedding)
        results2: List[Document] = self.bm25_search(query)
        # ranker = Reranker("rankgpt3", api_key = os.getenv["OENAI_API_KEY"])
        documents: List[Document] = []

        allDocumentIDsSet: Set[str] = set()
        for item in results1:
            documents.append(item)
            allDocumentIDsSet.add(item.id)
        for item in results2:
            if item.id not in allDocumentIDsSet:
                documents.append(item)
                allDocumentIDsSet.add(item.id)
            else:
                logger.info(
                    f"Trùng kết quả semantic search và bm25 search với query = `{query}`, id = {item.id}"
                )

        # Sử dụng cross-encoder để tái xếp hạng danh sách tài liệu
        documents = self.rerank_documents(query, documents)

        return documents

    @observe(name="DocumentRetriever_semantic_search")
    def semantic_search(self, query_embbedding: List[float]) -> List[Document]:
        results = search(
            input_embeddings=[query_embbedding],
            loaded_collection=self.collection,
            embed_field="embedding",
            text_field="page_content",
            source_fields=[
                "text",
                "file_name",
                "file_directory"
            ],
            limit=20,
            search_limit=20,
            search_param={"metric_type": "L2"},
        )
        # print(results)
        documents: List[Document] = []

        for item in results[0]:
            documents.append(
                Document(
                    id=item.id,
                    page_content=item.page_content,
                    file_path=f"{item.file_directory}/{item.file_name}",
                    text = item.text,
                )
            )
        return documents

    @observe(name="DocumentRetriever_bm25_search")
    def bm25_search(self, query: str) -> List[Document]:
        results: List[HaystackDocument] = self.bm25Retriever.run(query=query, top_k=20)["documents"]
        documents: List[Document] = []

        for item in results:
            page_content = item.meta["entity"]["page_content"]
            file_directory = item.meta["entity"]["file_directory"]
            file_name = item.meta["entity"]["file_name"]
            text = item.meta["entity"]["text"]
            
            documents.append(
                Document(
                    id=item.id,
                    page_content=page_content,
                    file_path=f"{file_directory}/{file_name}",
                    text=text,
                )
            )
        return documents

    @observe(name="Rerank_Document")
    def rerank_documents(self, query: str, documents: List[Document]) -> List[Document]:
        cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        # Tạo các cặp câu truy vấn và nội dung tài liệu
        sentence_pairs = [[query, item.text] for item in documents]
        for item in documents:
            print("text",item.text)
            print("page_content",item.page_content)
            
        similarity_scores = cross_encoder_model.predict(sentences = sentence_pairs)
        # Assign the scores to the documents
        for idx, document in enumerate(documents):
            document.cross_score = similarity_scores[idx].item()
        filter_documents = [doc for doc in documents if doc.cross_score>=3.5]
        # Sắp xếp tài liệu theo điểm số cross-encoder
        reranked_documents = sorted(
            documents,
            key=lambda item: item.cross_score,
            reverse=True
        )
        top_reranked_documents = reranked_documents[:5]
        print(f"Number of reranked documents: {len(reranked_documents)}")

        print("Top 10 hits with CrossEncoder:")
        for item in top_reranked_documents:
            print("\t{:.3f}\t{}".format(item.cross_score, item.id))

        return top_reranked_documents

