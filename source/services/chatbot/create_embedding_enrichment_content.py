import sys
import os
import asyncio
# Thêm path của thư mục source vào PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(source_dir)
from source.services.chatbot.database import get_db, Embedding
from source.services.chatbot.embedder import Embedder
from google.oauth2.service_account import Credentials
from tenacity import retry, wait_exponential



# Khởi tạo credentials
credentials = Credentials.from_service_account_file(
    "/home/datpt/project/communi_ai_6061cfee10dd.json",
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Khởi tạo Embedder
embedder = Embedder()

async def update_embedding(chunk_id: int, page_content: str):
    try:
        # Gọi hàm run của Embedder để lấy embedding
        embedding_vector = embedder.run(page_content)
        return embedding_vector
    except Exception as e:
        print(f"Error embedding chunk {chunk_id}: {str(e)}")
        return None

async def process_all():
    db = next(get_db())
    embeddings = db.query(Embedding).filter(
        Embedding.customer_id == 'VPBank').all()

    for embedding in embeddings:
        try:
            print(f"Processing chunk {embedding.chunk_id}")
            enriched_embedding = await update_embedding(embedding.chunk_id, embedding.enriched_content)
            origin_embedding = await update_embedding(embedding.chunk_id, embedding.text)
            if enriched_embedding is not None:
                embedding.embedding_enrichment = enriched_embedding
                db.commit()
                print(f"Successfully updated chunk {embedding.chunk_id}")
            await asyncio.sleep(3)  # Delay 3s

            if embedding is not None:
                embedding.embedding = origin_embedding
                db.commit()
                print(f"Successfully updated chunk {embedding.chunk_id}")
            await asyncio.sleep(3)  # Delay 3s

        except Exception as e:
            print(f"Error processing chunk {embedding.chunk_id}: {str(e)}")
            continue

if __name__ == "__main__":
    asyncio.run(process_all())