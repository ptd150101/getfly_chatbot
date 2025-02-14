import sys
import os

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from model_database.outline_database import Embedding, Context


from langfuse.decorators import observe
from utils.log_utils import get_logger
from typing import List, Set
from schemas.document import RelevantDocument
import numpy as np
import json
import requests
from .embedder import Embedder
from sqlalchemy import text, select, and_, func
import re

LIMIT_SEARCH = 25

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
    

    def get_document_texts(self, chunk_ids: List[str]) -> Set[str]:  # Thay đổi kiểu trả về thành Set
        # Query từ bảng documents để lấy text đầy đủ cho nhiều doc_id
        results = self.session.execute(
            select(Embedding.text)
            .where(Embedding.chunk_id.in_(chunk_ids))
            .order_by(Embedding.chunk_id)
        ).fetchall()
        return set(result[0] for result in results if result)  # Trả về danh sách các text không rỗng

    def get_child_link_from_last_header(self, last_header: str) -> str:
        result = self.session.execute(
            select(Embedding.child_link)
            .where(Embedding.last_header == last_header)
        ).first()
        return result[0] if result else ""


    def get_all_chunk_ids(self, nested_parent: str) -> List[str]:
        results = self.session.execute(
            select(Embedding.chunk_id)
            .where(Embedding.nested_parent == nested_parent)
        ).fetchall()
        return [result[0] for result in results if result]  # Trả về danh sách các text không rỗng

    def count_children_documents(self, nested_parent: str) -> int:
        result = self.session.execute(
            select(func.count(Embedding.doc_id))
            .where(Embedding.nested_parent == nested_parent)
        ).first()
        return result[0] if result else 0


    def clean_link(sels, link):
        # Xóa phần /~/revisions/X4jWLQC5Kpi3KnYF2yLa từ link
        cleaned_url = re.sub(r'/~/revisions/[A-Za-z0-9]+', '', link)
        
        return cleaned_url

    @observe(name="RetrieverAndReranker")
    def run(self, query: str, threshold: float, context_string: str = "") -> List[RelevantDocument]:
        hybrid_search_documents = self.hybrid_search(query)
        rerank_hybrid_search = self.rerank_documents(
                                                    query,
                                                    hybrid_search_documents,
                                                    use_enriched_content=False,
                                                    threshold=threshold
                                                    )
        rerank_hybrid_search_documents = rerank_hybrid_search["top_reranked_documents"]
        backup_hybrid_search_documents = rerank_hybrid_search["reranked_documents"]

        parent_processed = set()  # Theo dõi parent đã xử lý
        final_documents = []
        parent_docs = {}  # Lưu documents theo parent

        # Nhóm documents theo nested_parent
        for doc in rerank_hybrid_search_documents:
            parent = doc.get('nested_parent')
            
            if not parent:
                final_documents.append(doc)
                continue

            if parent not in parent_docs:
                parent_docs[parent] = []
            parent_docs[parent].append(doc)

        # Xử lý gộp document
        for parent, children in parent_docs.items():
            if parent in parent_processed:
                continue

            n = len(children)  # số document con tìm được
            print('số document con: ', n)



            if n > 1:
                print("parent: ", parent)
                chunk_ids = self.get_all_chunk_ids(parent)
                print("chunk_ids: ", chunk_ids)
                # Query text đầy đủ từ bảng documents
                parent_texts = self.get_document_texts(chunk_ids)
                merged_text = " ".join(filter(None, list(parent_texts)))


                if merged_text:
                    # Tính toán điều kiện gộp
                    p = self.count_children_documents(parent)
                    if n - p <= 2 and n - p <= n / 3:
                        # Tìm dòng trước header cuối cùng
                        lines = merged_text.split('\n')
                        last_header_index = -1
                        
                        # Tìm vị trí header cuối cùng
                        for i, line in enumerate(lines):
                            if re.match(r'^#+\s+', line):
                                last_header_index = i
                                
                        # Lấy dòng trước header cuối cùng (nếu có)
                        last_header = lines[last_header_index - 1].strip() if last_header_index > 0 else ""
                        child_link = self.get_child_link_from_last_header(last_header)
                        child_link_merged = child_link if child_link else children[0]['child_link']
                        # Tạo document cha với text đầy đủ
                        parent_doc = {
                            'id': children[0]['id'],
                            'page_content': merged_text,
                            'url': children[0]['url'],
                            'text': merged_text,
                            'child_link': self.clean_link(child_link_merged.split('#')[0]),
                            'images': "",
                            'videos': "",
                            'cross_score': max(child['cross_score'] for child in children),
                            'nested_parent': children[0]['nested_parent'],
                            'last_header': last_header,
                            'merged': True
                        }
                        print('Thỏa mãn điều kiện gộp')
                        final_documents.append(parent_doc)
                    else:
                        print('Không thỏa mãn điều kiện gộp')
                        final_documents.extend(children)
                else:
                    print('Không có text đầy đủ')
                    final_documents.extend(children)
            else:
                print('chỉ có 1 tài liệu con, không cần gộp')
                # Nếu chỉ có 1 tài liệu con, thêm nó vào final_documents
                final_documents.extend(children)

            parent_processed.add(parent)

        # Loại bỏ trùng lặp cho final_rerank
        unique_documents = {doc['id']: doc for doc in final_documents}.values()
        
        # Giữ nguyên backup_rerank
        unique_backup_documents = {doc['id']: doc for doc in backup_hybrid_search_documents}.values()

        return {
            "final_rerank": list(unique_documents),
            "backup_rerank": list(unique_backup_documents),
            "final_documents": final_documents,
            "parent_docs": parent_docs,
        }

    
    @observe(name="DocumentRetriever_hybrid_search")
    def hybrid_search(self, query_text: str, context_string: str = "") -> List[RelevantDocument]:
        query_embedding = self.embedder.run(query_text)
        documents: List[RelevantDocument] = []
        seen_ids: Set[str] = set()
        cleaned_query = re.sub(r'[^\w\s]', '', query_text)

        
        try:
            base_conditions = [
                Embedding.customer_id == "getfly_171_2025",
            ]

            if context_string:
                base_conditions.append(Context.context_string.any(context_string))
            
            
            try:
                if cleaned_query:
                    full_text_conditions = base_conditions.copy()
                    full_text_conditions.append(Embedding.text.op('@@@')(cleaned_query))


                    full_text_query = self.session.execute(
                        select(Embedding.chunk_id,
                                Embedding.url,
                                Embedding.page_content,
                                Embedding.text,
                                Embedding.child_link,
                                Embedding.enriched_content,
                                Embedding.images,
                                Embedding.videos,
                                Embedding.nested_parent,
                                Embedding.last_header,
                                text("paradedb.score(embeddings.chunk_id)")
                                )
                        .where(and_(
                            *full_text_conditions
                        ))
                        .order_by(text("score DESC"))
                        .limit(LIMIT_SEARCH)
                    ).fetchall()
                    

                    print('full_text_query: ', len(full_text_query))
                    # Xử lý kết quả full text search
                    for row in full_text_query:
                        if row.chunk_id not in seen_ids:
                            documents.append(
                                RelevantDocument(
                                    id=row.chunk_id,
                                    page_content=row.page_content,
                                    text=row.text,
                                    child_link=self.clean_link(row.child_link),
                                    url=row.url,
                                    images=row.images,
                                    videos=row.videos,
                                    nested_parent=row.nested_parent,
                                    last_header=row.last_header,
                                    merged=False
                                )
                            )
                            seen_ids.add(row.chunk_id)
                if not documents:
                    processed_query = ' AND '.join(cleaned_query.split()[:10]).strip()
                    if processed_query:
                        bm25_conditions = base_conditions.copy()
                        bm25_conditions.append(Embedding.text.op('@@@')(processed_query))

                        bm25_query = self.session.execute(
                            select(Embedding.chunk_id,
                                Embedding.url,
                                Embedding.page_content,
                                Embedding.enriched_content,
                                Embedding.text,
                                Embedding.child_link,
                                Embedding.images,
                                Embedding.videos,
                                Embedding.nested_parent,
                                Embedding.last_header,
                                text("paradedb.score(embeddings.chunk_id)"))
                            .where(and_(
                                *bm25_conditions
                            ))
                            .order_by(text("score DESC"))
                            .limit(LIMIT_SEARCH)
                        ).fetchall()

                        print('bm25_query: ', len(bm25_query))
                        # Xử lý kết quả BM25 search
                        for row in bm25_query:
                            if row.chunk_id not in seen_ids:
                                documents.append(
                                    RelevantDocument(
                                        id=row.chunk_id,
                                        page_content=row.page_content,
                                        text=row.text,
                                        child_link=self.clean_link(row.child_link),
                                        url=row.url,
                                        images=row.images,
                                        videos=row.videos,
                                        nested_parent=row.nested_parent,
                                        last_header=row.last_header,
                                        merged=False
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
                        Embedding.child_link,
                        Embedding.images,
                        Embedding.videos,
                        Embedding.nested_parent,
                        Embedding.last_header,
                        )
                    .where(and_(
                        *base_conditions
                        )
                    )
                    .order_by(Embedding.embedding.l2_distance(query_embedding))
                    .limit(LIMIT_SEARCH)
                ).fetchall()

                print('semantic_query: ', len(semantic_query))

                # Xử lý kết quả semantic search
                for row in semantic_query:
                    if row.chunk_id not in seen_ids:
                        documents.append(
                            RelevantDocument(
                                id=row.chunk_id,
                                page_content=row.page_content,
                                text=row.text,
                                child_link=self.clean_link(row.child_link),
                                url=row.url,
                                images=row.images,
                                videos=row.videos,
                                nested_parent=row.nested_parent,
                                last_header=row.last_header,
                                merged=False
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
            

            self.session.commit()

        except Exception as e:
            logger.error(f"Error in hybrid_search: {str(e)}")
            self.session.rollback()
            raise
        return [doc.to_dict() for doc in documents]


    @observe(name="Rerank_Document")
    def rerank_documents(
        self,
        query: str,
        documents: List[dict],
        use_enriched_content: bool = False,
        threshold: float = 0.35
        ) -> List[RelevantDocument]:
        try:
            documents = [RelevantDocument(
                id=doc['id'],
                text=doc['text'],
                page_content=doc['page_content'],
                child_link=doc['child_link'],
                url=doc['url'],
                images=doc.get('images'),
                videos=doc.get('videos'),
                score=doc.get('score'),
                cross_score=doc.get('cross_score'),
                nested_parent=doc.get('nested_parent'),
                last_header=doc.get('last_header')
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
            )[:4]


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