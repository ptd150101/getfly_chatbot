import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from typing import List
tokenizer = AutoTokenizer.from_pretrained('BAAI/bge-reranker-v2-m3')
model = AutoModelForSequenceClassification.from_pretrained('BAAI/bge-reranker-v2-m3')
model.eval()

pairs = [['what is panda?', 'hi'], ['what is panda?', 'The giant panda (Ailuropoda melanoleuca), sometimes called a panda bear or simply panda, is a bear species endemic to China.']]
with torch.no_grad():
    inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors='pt', max_length=512)
    scores = model(**inputs, return_dict=True).logits.view(-1, ).float()
    print("scores: ", scores)
    print(type(scores))
    
    
    
    
    
    
    
    
    
    
    
    
    


# Giả lập class Document
class Document:
    def __init__(self, text, doc_id):
        self.text = text
        self.id = doc_id
        self.cross_score = None

# Hàm rerank_documents cần test
def rerank_documents(query: str, documents: List[Document]) -> List[Document]:
    from sentence_transformers import CrossEncoder
    
    # Sử dụng CrossEncoder đã được huấn luyện
    cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    # Tạo các cặp câu truy vấn và nội dung tài liệu
    sentence_pairs = [[query, item.text] for item in documents]
    similarity_scores = cross_encoder_model.predict(sentence_pairs)
    print("similarity_scores: ", similarity_scores)
    print(type(similarity_scores))
    # Gán điểm số vào các tài liệu
    for idx, document in enumerate(documents):
        document.cross_score = similarity_scores[idx].item()

    # Sắp xếp các tài liệu theo điểm số cross-encoder
    reranked_documents = sorted(
        documents,
        key=lambda item: item.cross_score,
        reverse=True
    )
    top_reranked_documents = reranked_documents[:10]
    print(f"Number of reranked documents: {len(reranked_documents)}")

    print("Top 10 hits with CrossEncoder:")
    for item in top_reranked_documents:
        print("\t{:.3f}\t{}".format(item.cross_score, item.id))

    return top_reranked_documents

# Giả lập các tài liệu
documents = [
    Document("This is a document about pandas.", "doc1"),
    Document("Pandas are native to China.", "doc2"),
    Document("A panda's diet consists mostly of bamboo.", "doc3"),
    Document("Pandas are considered a national treasure in China.", "doc4"),
]

# Truy vấn ví dụ
query = "Tell me about pandas."

# Gọi hàm rerank_documents
reranked_results = rerank_documents(query, documents)

# Kết quả reranked_results sẽ chứa các tài liệu được sắp xếp lại