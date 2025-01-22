from markdown2 import markdown
from bs4 import BeautifulSoup

def markdown_to_text(markdown_content):
    # Convert markdown to HTML with extra features like lists
    html = markdown(markdown_content, extras=["fenced-code-blocks", "cuddled-lists", "tables", "numbering"])
    
    # Parse the HTML to preserve list formatting
    soup = BeautifulSoup(html, "html.parser")
    
    # Process ordered lists and unordered lists
    def process_list_items(soup):
        for ol in soup.find_all("ol"):
            start = int(ol.get("start", 1))  # Get start attribute if exists, default to 1
            for i, li in enumerate(ol.find_all("li"), start):
                li.insert_before(f"{i}. ")  # Add numbering before each list item
            ol.unwrap()  # Remove the ol tag, but keep its contents

        for ul in soup.find_all("ul"):
            for li in ul.find_all("li"):
                li.insert_before("- ")  # Add a dash before each list item
            ul.unwrap()  # Remove the ul tag, but keep its contents

    process_list_items(soup)
    
    text = soup.get_text()
    return text