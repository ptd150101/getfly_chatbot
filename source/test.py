from sentence_transformers import SentenceTransformer
from pyvi.ViTokenizer import tokenize
import numpy as np

# Các câu đầu vào
sentences = [
    """
    Khách hàng cá nhân
Bảo hiểm online
Bảo hiểm du lịch quốc tế Travelcare mang đến sự bảo vệ toàn diện
Đối tác
Đây là sản phẩm bảo hiểm được cung cấp bởi công ty Liberty Việt Nam.
Việc tham gia sản phẩm bảo hiểm không phải là yêu cầu bắt buộc để thực hiện hay hưởng một dịch vụ nào khác của Sacombank.
Hỏi đáp

1. Tại sao bảo hiểm du lịch lại cần thiết với tôi?
Bảo hiểm du lịch là cần thiết vì nó bảo vệ bạn khỏi những rủi ro mà bạn có thể gặp phải trong chuyến đi như bệnh tật, tai nạn, mất mát tài sản cá nhân hoặc hủy chuyến đi. Bảo hiểm du lịch cũng cung cấp các  dịch vụ hỗ trợ khẩn cấp và giúp bạn giải quyết các vấn đề khác trong quá trình du lịch.
2. Khi đi du lịch và gặp sự cố ở nước ngoài, tôi cần chuẩn bị gì để được bảo hiểm?
Để được bảo hiểm khi đi du lịch ở nước ngoài, bạn cần mua một hợp đồng bảo hiểm du lịch phù hợp với nhu cầu của mình. Trước khi đi, bạn nên đọc kỹ điều kiện, quy định và các quyền lợi được bảo hiểm của hợp đồng. Ngoài ra, bạn cũng nên chuẩn bị một bản sao các tài liệu quan trọng như hộ chiếu, thẻ tín dụng, giấy tờ đăng ký xe hơi (nếu đi xe hơi), và số điện thoại liên hệ khẩn cấp.
3. Trong trường hợp người đi cùng không đăng ký bảo hiểm, tôi có được sử dụng chung các quyền lợi bảo hiểm với người đó không?
Nếu người đi cùng không đăng ký bảo hiểm, họ sẽ không được sử dụng các quyền lợi bảo hiểm được cung cấp bởi hợp đồng bảo hiểm của bạn. Tuy nhiên, tùy vào hợp đồng bảo hiểm cụ thể mà các quyền lợi có thể được mở rộng để bao gồm người đi cùng của bạn, nếu họ bị ảnh hưởng bởi các rủi ro mà hợp đồng bảo hiểm đó bao phủ. Bạn nên đọc kỹ điều kiện của hợp đồng bảo hiểm để biết chính xác về phạm vi bảo hiểm và quyền lợi của mình.
    """,
    "Hà Nội là thủ đô của Việt Nam",
    "Thủ đô của Việt Nam là Hà Nội"




]

# Tokenize các câu sử dụng Pyvi
tokenizer_sent = [tokenize(sent) for sent in sentences]

# Sử dụng mô hình SentenceTransformer để mã hóa câu thành vector
model = SentenceTransformer('dangvantuan/vietnamese-embedding')
embeddings = model.encode(tokenizer_sent)

# In ra các embeddings
print("Embeddings:\n", embeddings)

# Tính toán cosine similarity giữa hai embeddings
embedding_1 = embeddings[0]
embedding_2 = embeddings[1]

# Tính dot product
dot_product = np.dot(embedding_1, embedding_2)

# Tính norm của từng embedding
norm_1 = np.linalg.norm(embedding_1)
norm_2 = np.linalg.norm(embedding_2)

# Tính cosine similarity
cosine_similarity = dot_product / (norm_1 * norm_2)

print("Cosine Similarity between the two sentences:", cosine_similarity)