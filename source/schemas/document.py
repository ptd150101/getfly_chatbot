from typing import List, Optional

class Document:
    def __init__(self,
                id: str,
                page_content: str,
                url: str,
                enriched_content: str,
                text: str,
                images: Optional[List[str]] = None,
                videos: Optional[List[str]] = None,
                score=None,
                cross_score=None) -> None:
        self.id = id
        self.page_content = page_content 
        self.text = text
        self.url = url
        self.score = score
        self.cross_score = cross_score
        self.enriched_content = enriched_content
        self.images = images or []
        self.videos = videos or []



    def __str__(self):
        return f"Document(id={self.id}, text={self.text[:50]}...)"
    
    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {
            "id": self.id,
            "page_content": self.page_content,
            "url": self.url, 
            "text": self.text,
            "images": self.images,
            "videos": self.videos,
            "score": self.score,
            "cross_score": self.cross_score,
            "enriched_content": self.enriched_content
        }