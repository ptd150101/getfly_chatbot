import sys
import os

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from model_database.outline_database import Embedding


from langfuse.decorators import observe
from utils.log_utils import get_logger
from typing import List, Set
from schemas.document import Document
import numpy as np
import json
import requests
from .embedder import Embedder
from sqlalchemy import text, select, and_
import re

LIMIT_SEARCH = 15

logger = get_logger(__name__)

class DocumentRetriever:
    def __init__(self, session) -> None:
        self.session = session
        self.embedder = Embedder(
            url="http://35.197.153.145:8231/embed",
            batch_size=1,
            max_length=4096,
            max_retries=10,
            retry_delay=2.0
        )

    # @observe(name="FullDocumentRetriever")
    # def run(self, query: str, threshold: float) -> List[Document]:
    #     result = self.retriever_and_reranker(query, threshold)
    #     return result
    

    @observe(name="RetrieverAndReranker")
    def run(self, query: str, threshold: float) -> List[Document]:
        hybrid_search_documents = self.hybrid_search(query)
        rerank_hybrid_search = self.rerank_documents(
                                                            query,
                                                            hybrid_search_documents,
                                                            use_enriched_content = False,
                                                            threshold = threshold
                                                            )
        rerank_hybrid_search_documents = rerank_hybrid_search["top_reranked_documents"]
        backup_hybrid_search_documents = rerank_hybrid_search["reranked_documents"]


        # Chỉ tìm kiếm enrichment nếu không có tài liệu nào từ hybrid search
        if not rerank_hybrid_search_documents:
            enrichment_search_documents = self.search_enrichment(query)
            rerank_enrichment_search = self.rerank_documents(
                                                                    query,
                                                                    enrichment_search_documents,
                                                                    use_enriched_content = True,
                                                                    threshold = threshold
                                                                    )
            rerank_enrichment_search_documents = rerank_enrichment_search["top_reranked_documents"]
            backup_enrichment_search_documents = rerank_enrichment_search["reranked_documents"]
        else:
            rerank_enrichment_search_documents = []
            backup_enrichment_search_documents = []
        # Hợp nhất 2 kết quả và loại bỏ trùng lặp
        all_documents = rerank_hybrid_search_documents + rerank_enrichment_search_documents
        unique_documents = {doc['id']: doc for doc in all_documents}.values()

        back_up_documents = backup_hybrid_search_documents + backup_enrichment_search_documents
        unique_backup_documents = {doc['id']: doc for doc in back_up_documents}.values()
        return {
            "final_rerank": list(unique_documents),
            "backup_rerank": list(unique_backup_documents)
        }

    
    @observe(name="DocumentRetriever_hybrid_search")
    def hybrid_search(self, query_text: str) -> List[Document]:
        query_embedding = self.embedder.run(query_text)
        documents: List[Document] = []
        seen_ids: Set[str] = set()
        cleaned_query = re.sub(r'[^\w\s]', '', query_text)
        
        
        
        try:
            # Thử tìm kiếm full text với query_text
            try:
                full_text_query = self.session.execute(
                    select(Embedding.chunk_id,
                            Embedding.url,
                            Embedding.page_content,
                            Embedding.text,
                            Embedding.enriched_content,
                            Embedding.images,
                            Embedding.videos,
                            text("paradedb.score(embeddings.chunk_id)")
                            )
                    .where(and_(
                        Embedding.text.op('@@@')(cleaned_query),
                        Embedding.customer_id == "New Getfly"
                    ))
                    .order_by(text("score DESC"))
                    .limit(LIMIT_SEARCH)
                ).fetchall()

                # Xử lý kết quả full text search
                for row in full_text_query:
                    if row.chunk_id not in seen_ids:
                        documents.append(
                            Document(
                                id=row.chunk_id,
                                page_content=row.page_content,
                                enriched_content=row.enriched_content,
                                text=row.text,
                                url=row.url,
                                images=row.images,
                                videos=row.videos,
                            )
                        )
                        seen_ids.add(row.chunk_id)

                # Query semantic search
                semantic_query = self.session.execute(
                    select(Embedding.chunk_id,
                        Embedding.url,
                        Embedding.page_content,
                        Embedding.enriched_content,
                        Embedding.text,
                        Embedding.images,
                        Embedding.videos,
                        )
                    .where(and_(Embedding.customer_id == "New Getfly"))
                    .order_by(Embedding.embedding.l2_distance(query_embedding))
                    .limit(LIMIT_SEARCH)
                ).fetchall()

                # Xử lý kết quả semantic search
                for row in semantic_query:
                    if row.chunk_id not in seen_ids:
                        documents.append(
                            Document(
                                id=row.chunk_id,
                                page_content=row.page_content,
                                enriched_content=row.enriched_content,
                                text=row.text,
                                url=row.url,
                                images=row.images,
                                videos=row.videos,
                            )
                        )
                        seen_ids.add(row.chunk_id)
                    else:
                        logger.info(
                            f"Trùng kết quả semantic search và BM25 search với query = `{query_text}`, id = {row.chunk_id}"
                        )

            except Exception as e:
                logger.warning(f"Full text search failed: {str(e)}")
                self.session.rollback()
            # Nếu không tìm thấy tài liệu nào, sử dụng processed_query
            if not documents:
                cleaned_query = re.sub(r'[^\w\s]', '', query_text)
                processed_query = ' AND '.join(cleaned_query.split()[:10]).strip()
                try:
                    bm25_query = self.session.execute(
                        select(Embedding.chunk_id,
                               Embedding.url,
                               Embedding.page_content,
                               Embedding.enriched_content,
                               Embedding.text,
                               Embedding.images,
                               Embedding.videos,
                               text("paradedb.score(embeddings.chunk_id)"))
                        .where(and_(
                            Embedding.text.op('@@@')(processed_query),
                            Embedding.customer_id == "New Getfly"
                        ))
                        .order_by(text("score DESC"))
                        .limit(LIMIT_SEARCH)
                    ).fetchall()

                    # Xử lý kết quả BM25 search
                    for row in bm25_query:
                        if row.chunk_id not in seen_ids:
                            documents.append(
                                Document(
                                    id=row.chunk_id,
                                    page_content=row.page_content,
                                    enriched_content=row.enriched_content,
                                    text=row.text,
                                    url=row.url,
                                    images=row.images,
                                    videos=row.videos,
                                )
                            )
                            seen_ids.add(row.chunk_id)

                    # Query semantic search
                    semantic_query = self.session.execute(
                        select(Embedding.chunk_id,
                            Embedding.url,
                            Embedding.page_content,
                            Embedding.enriched_content,
                            Embedding.text,
                            Embedding.images,
                            Embedding.videos,
                            )
                        .where(and_(Embedding.customer_id == "New Getfly"))
                        .order_by(Embedding.embedding.l2_distance(query_embedding))
                        .limit(LIMIT_SEARCH)
                    ).fetchall()

                    # Xử lý kết quả semantic search
                    for row in semantic_query:
                        if row.chunk_id not in seen_ids:
                            documents.append(
                                Document(
                                    id=row.chunk_id,
                                    page_content=row.page_content,
                                    enriched_content=row.enriched_content,
                                    text=row.text,
                                    url=row.url,
                                    images=row.images,
                                    videos=row.videos,
                                )
                            )
                            seen_ids.add(row.chunk_id)
                        else:
                            logger.info(
                                f"Trùng kết quả semantic search và BM25 search với query = `{query_text}`, id = {row.chunk_id}"
                            )

                except Exception as e:
                    logger.error(f"BM25 search failed: {str(e)}")
                    self.session.rollback()
                    raise

            self.session.commit()

        except Exception as e:
            logger.error(f"Error in search_enrichment: {str(e)}")
            self.session.rollback()
            raise

        return [doc.to_dict() for doc in documents]


    @observe(name="Search_Enrichment")
    def search_enrichment(self, query_text: str) -> List[Document]:
        query_embedding = self.embedder.run(query_text)
        documents: List[Document] = []
        seen_ids: Set[str] = set()
        cleaned_query = re.sub(r'[^\w\s]', '', query_text)
        try:
            # Thử tìm kiếm full text với query_text
            try:
                full_text_query = self.session.execute(
                    select(Embedding.chunk_id,
                            Embedding.url,
                            Embedding.page_content,
                            Embedding.enriched_content,
                            Embedding.text,
                            Embedding.images,
                            Embedding.videos,
                            text("paradedb.score(embeddings.chunk_id)"))
                    .where(and_(
                        Embedding.enriched_content.op('@@@')(cleaned_query),
                        Embedding.customer_id == "New Getfly"
                    ))
                    .order_by(text("score DESC"))
                    .limit(LIMIT_SEARCH)
                ).fetchall()

                # Xử lý kết quả full text search
                for row in full_text_query:
                    if row.chunk_id not in seen_ids:
                        documents.append(
                            Document(
                                id=row.chunk_id,
                                page_content=row.page_content,
                                enriched_content=row.enriched_content,
                                text=row.text,
                                url=row.url,
                                images=row.images,
                                videos=row.videos,
                            )
                        )
                        seen_ids.add(row.chunk_id)

                # Query semantic search
                semantic_query = self.session.execute(
                    select(Embedding.chunk_id,
                        Embedding.url,
                        Embedding.page_content,
                        Embedding.enriched_content,
                        Embedding.text,
                        Embedding.images,
                        Embedding.videos,
                        )
                    .where(and_(Embedding.customer_id == "New Getfly"))
                    .order_by(Embedding.embedding_enrichment.l2_distance(query_embedding))
                    .limit(LIMIT_SEARCH)
                ).fetchall()

                # Xử lý kết quả semantic search
                for row in semantic_query:
                    if row.chunk_id not in seen_ids:
                        documents.append(
                            Document(
                                id=row.chunk_id,
                                page_content=row.page_content,
                                enriched_content=row.enriched_content,
                                text=row.text,
                                url=row.url,
                                images=row.images,
                                videos=row.videos,
                            )
                        )
                        seen_ids.add(row.chunk_id)
                    else:
                        logger.info(
                            f"Trùng kết quả semantic search và BM25 search với query = `{query_text}`, id = {row.chunk_id}"
                        )

            except Exception as e:
                logger.warning(f"Full text search failed: {str(e)}")
                self.session.rollback()
            # Nếu không tìm thấy tài liệu nào, sử dụng processed_query
            if not documents:
                cleaned_query = re.sub(r'[^\w\s]', '', query_text)
                # Xây dựng processed_query từ cleaned_query
                processed_query = ' AND '.join(cleaned_query.split()[:10]).strip()
                
                
                
                try:
                    bm25_query = self.session.execute(
                        select(Embedding.chunk_id,
                               Embedding.url,
                               Embedding.page_content,
                               Embedding.enriched_content,
                               Embedding.text,
                               Embedding.images,
                               Embedding.videos,
                               text("paradedb.score(embeddings.chunk_id)"))
                        .where(and_(
                            Embedding.enriched_content.op('@@@')(processed_query),
                            Embedding.customer_id == "New Getfly"
                        ))
                        .order_by(text("score DESC"))
                        .limit(LIMIT_SEARCH)
                    ).fetchall()

                    # Xử lý kết quả BM25 search
                    for row in bm25_query:
                        if row.chunk_id not in seen_ids:
                            documents.append(
                                Document(
                                    id=row.chunk_id,
                                    page_content=row.page_content,
                                    enriched_content=row.enriched_content,
                                    text=row.text,
                                    url=row.url,
                                    images=row.images,
                                    videos=row.videos,
                                )
                            )
                            seen_ids.add(row.chunk_id)

                    # Query semantic search
                    semantic_query = self.session.execute(
                        select(Embedding.chunk_id,
                            Embedding.url,
                            Embedding.page_content,
                            Embedding.enriched_content,
                            Embedding.text,
                            Embedding.images,
                            Embedding.videos,
                            )
                        .where(and_(Embedding.customer_id == "New Getfly"))
                        .order_by(Embedding.embedding_enrichment.l2_distance(query_embedding))
                        .limit(LIMIT_SEARCH)
                    ).fetchall()

                    # Xử lý kết quả semantic search
                    for row in semantic_query:
                        if row.chunk_id not in seen_ids:
                            documents.append(
                                Document(
                                    id=row.chunk_id,
                                    page_content=row.page_content,
                                    enriched_content=row.enriched_content,
                                    text=row.text,
                                    url=row.url,
                                    images=row.images,
                                    videos=row.videos,
                                )
                            )
                            seen_ids.add(row.chunk_id)
                        else:
                            logger.info(
                                f"Trùng kết quả semantic search và BM25 search với query = `{query_text}`, id = {row.chunk_id}"
                            )

                except Exception as e:
                    logger.error(f"BM25 search failed: {str(e)}")
                    self.session.rollback()
                    raise

            self.session.commit()

        except Exception as e:
            logger.error(f"Error in search_enrichment: {str(e)}")
            self.session.rollback()
            raise

        return [doc.to_dict() for doc in documents]

        

    @observe(name="Rerank_Document")
    def rerank_documents(self, query: str, documents: List[dict], use_enriched_content: bool = False, threshold: float = 0.35) -> List[Document]:
        try:
            documents = [Document(
                id=doc['id'],
                text=doc['text'],
                page_content=doc['page_content'],
                enriched_content=doc['enriched_content'],
                url=doc['url'],
                images=doc.get('images'),
                videos=doc.get('videos'),
                score=doc.get('score'),
                cross_score=doc.get('cross_score')
            ) for doc in documents]

            # Tạo các cặp câu truy vấn và nội dung tài liệu
            sentence_pairs = [[query, item.enriched_content if use_enriched_content else item.text] for item in documents]
            
            payload = json.dumps({
                "data": sentence_pairs
            })

            url = "http://35.197.153.145:8002/reranker/compute-score"
            headers = {
                'Content-Type': 'application/json'
            }

            try:
                # Gửi yêu cầu POST với payload đến API rerank
                response = requests.request("POST", url, headers=headers, data=payload)

                # In phản hồi từ server (nếu cần debug)
                # print(response.text)

                # Parse phản hồi JSON từ server
                api_response = json.loads(response.text)
                
                if api_response.get("code") == "M200" and "data" in api_response:
                    similarity_scores = api_response["data"]
                else:
                    logger.error(f"Invalid API response format: {api_response}")
                    # Trả về documents gốc thay vì raise error
                    return {
                        "top_reranked_documents": [doc.to_dict() for doc in documents[:5]],
                        "reranked_documents": [doc.to_dict() for doc in documents[:3]]
                    }

            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {str(e)}")
                # Trả về documents gốc nếu API fail
                return {
                    "top_reranked_documents": [doc.to_dict() for doc in documents[:5]],
                    "reranked_documents": [doc.to_dict() for doc in documents[:3]]
                }

            # Sigmoid và scoring
            def sigmoid(x):
                return 1 / (1 + np.exp(-x))

            # Gán điểm số từ API cho từng tài liệu
            for idx, document in enumerate(documents):
                document.cross_score = sigmoid(similarity_scores[idx])  # Lấy điểm từ API

            filter_documents = [doc for doc in documents if doc.cross_score >= threshold]

            no_filter_documents = sorted(
                documents,  # Sử dụng danh sách đã được lọc
                key=lambda item: item.cross_score,
                reverse=True  # Sắp xếp theo thứ tự giảm dần
            )[:3]


            # Sắp xếp tài liệu theo điểm số từ API (cross_score)
            reranked_documents = sorted(
                filter_documents,  # Sử dụng danh sách đã được lọc
                key=lambda item: item.cross_score,
                reverse=True  # Sắp xếp theo thứ tự giảm dần
            )

            # Chỉ lấy 5 tài liệu hàng đầu
            top_reranked_documents = reranked_documents[:5]

            print(f"Number of reranked documents: {len(reranked_documents)}")

            print("Top 5 hits with API rerank scores:")
            for item in top_reranked_documents:
                print("\t{:.3f}\t{}".format(item.cross_score, item.id))

            return {
                "top_reranked_documents": [doc.to_dict() for doc in top_reranked_documents],
                "reranked_documents": [doc.to_dict() for doc in no_filter_documents]
            }

        except Exception as e:
            logger.error(f"Error in rerank_documents: {str(e)}")
            # Trả về documents gốc trong trường hợp lỗi
            return {
                "top_reranked_documents": [doc.to_dict() for doc in documents[:5]],
                "reranked_documents": [doc.to_dict() for doc in documents[:3]]
            }