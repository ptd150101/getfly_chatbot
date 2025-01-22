from typing import List, Optional

class RelevantDocument:
    def __init__(self,
                id: str,
                page_content: str,
                url: str,
                child_link: str,
                text: str,
                images: Optional[List[str]] = None,
                videos: Optional[List[str]] = None,
                score=None,
                cross_score=None,
                context_string=None,
                context=None,
                nested_parent=None,
                last_header=None,
                merged=False) -> None:
        self.id = id
        self.page_content = page_content 
        self.text = text
        self.url = url
        self.score = score
        self.cross_score = cross_score
        self.child_link = child_link
        self.images = images or []
        self.videos = videos or []
        self.context_string = context_string
        self.context = context
        self.nested_parent = nested_parent
        self.last_header = last_header
        self.merged = merged

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
            "child_link":self.child_link,
            "images": self.images,
            "videos": self.videos,
            "score": self.score,
            "cross_score": self.cross_score,
            "context_string": self.context_string,
            "context": self.context,
            "nested_parent": self.nested_parent,
            "last_header": self.last_header,
            "merged": self.merged
        }
