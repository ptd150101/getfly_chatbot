class Document:
    # def __init__(self, id: str, full_product_name: str, product_name: str) -> None:
    def __init__(self, id: str, page_content: str, file_path: str, text: str) -> None:

        self.id = id
        self.page_content = page_content
        self.file_path = file_path
        self.text = text
