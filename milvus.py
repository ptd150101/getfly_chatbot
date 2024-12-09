from pymilvus import connections, Collection
import pandas as pd

# Kết nối đến Milvus server
connections.connect(
    alias="default",
    host="10.0.0.14", 
    port="19530"
)

# Lấy collection cần xuất dữ liệu
collection_name = "VPBank"
collection = Collection(collection_name)

# Truy vấn tất cả dữ liệu trong collection
results = collection.query(
    expr="",  # Empty expression
    output_fields=['page_content', 'text', 'file_directory'],
    limit=collection.num_entities  # Thêm limit bằng tổng số entities trong collection
)

# Chuyển kết quả thành DataFrame
df = pd.DataFrame(results)
print(len(df))


df.to_json("VPBank.json", orient="records", force_ascii=False, indent=4)


# Đóng kết nối
connections.disconnect("default")