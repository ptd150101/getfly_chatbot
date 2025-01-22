from curses import pair_content
import sys
import os

# Thêm path của thư mục source vào PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(source_dir)

# Hardcode DB_URL
os.environ['DB_URL'] = "postgresql://postgres:123@localhost:1502/outline"

from source.services.chatbot.database import Embedding, SessionLocal
from sqlalchemy import select, update, and_, text
import pandas as pd
import structlog
import traceback

# Cấu hình structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer()  # In ra console dễ đọc
    ],
)


logger = structlog.get_logger(__name__)

class MappingLinkGetfly:
    def __init__(self):
        self.session = SessionLocal()



    
    
    
    def find_matching_content(self):
        try:
            print("Starting find_matching_content")
            df = pd.read_csv('/home/datpt/project/getfly/final_with_links1.csv')
            matches = []
            
            with open('mapping_log.txt', 'w', encoding='utf-8') as f:
                for index, row in df.iterrows():
                    try:
                        # Lấy dòng thứ 2 và nửa đầu của dòng cuối
                        csv_lines = row['text'].strip().split('\n')
                        if len(csv_lines) >= 2:  # Đảm bảo có ít nhất 2 dòng
                            second_line = csv_lines[1].strip()  # Lấy dòng thứ 2
                            last_line = csv_lines[-1].strip()   # Lấy dòng cuối
                            half_last_line = last_line[:len(last_line)//4]  # Lấy nửa đầu dòng cuối
                            
                            csv_id_child = row['child_link']
                            
                            print(f"\nProcessing row {index}")
                            print(f"Second line: {second_line}")
                            print(f"Half last line: {half_last_line}")
                            
                            f.write(f"\n\n=== CSV Text ===\n")
                            f.write(f"Second line: {second_line}\n")
                            f.write(f"Half last line: {half_last_line}\n")
                            
                            # Tìm trong database với điều kiện chứa cả dòng thứ 2 và nửa đầu dòng cuối
                            db_result = self.session.execute(
                                select(Embedding.chunk_id, 
                                    Embedding.page_content,
                                    Embedding.text,
                                    Embedding.url)
                                .where(
                                    and_(
                                        Embedding.text.contains(second_line),
                                        Embedding.text.contains(half_last_line)
                                    )
                                )
                                .limit(1)
                            ).first()
                            
                            if db_result:
                                print(f"Found match for row {index}")
                                f.write(f"\n=== DB Text ===\n{db_result.text}\n")
                                f.write(f"URL: {db_result.url}\n")
                                f.write(f"id_child: {csv_id_child}\n")
                                matches.append({
                                    'text': db_result.text,
                                    'id_child': csv_id_child,
                                    'second_line': second_line,
                                    'half_last_line': half_last_line
                                })
                            else:
                                print(f"No match found for row {index}")
                                f.write("\nNo matching found in database\n")
                                
                    except Exception as e:
                        print(f"Error processing row {index}: {str(e)}")
                        print(traceback.format_exc())
                        continue
            
            print(f"Total matches found: {len(matches)}")
            return matches
                        
        except Exception as e:
            print(f"Error in find_matching_content: {str(e)}")
            print(traceback.format_exc())
            raise

    def update_urls(self, matches):
        try:
            logger.info("Starting update_urls")
            for index, match in enumerate(matches):
                try:
                    second_line = match['second_line']
                    half_last_line = match['half_last_line']
                    id_child = match['id_child']
                    
                    logger.info(f"Updating match {index}")
                    
                    # Tìm và update records dựa trên dòng thứ 2 và nửa đầu dòng cuối
                    result = self.session.execute(
                        update(Embedding)
                        .where(
                            and_(
                                Embedding.text.contains(second_line),
                                Embedding.text.contains(half_last_line)
                            )
                        )
                        .values(url = id_child)
                    )
                    
                    # Log kết quả
                    with open('update_log.txt', 'a', encoding='utf-8') as f:
                        f.write(f"\n=== Updating Text ===\n")
                        f.write(f"Second line: {second_line}\n")
                        f.write(f"Half last line: {half_last_line}\n")
                        f.write(f"New URL (child_link): {id_child}\n")
                        f.write(f"Number of records updated: {result.rowcount}\n")
                        
                except Exception as match_error:
                    logger.error(f"Error updating match {index}: {str(match_error)}")
                    logger.error(traceback.format_exc())
                    continue
                        
            self.session.commit()
            logger.info("Updates committed successfully")
                
        except Exception as e:
            logger.error(f"Error in update_urls: {str(e)}")
            logger.error(traceback.format_exc())
            self.session.rollback()
            raise 
        
        
        
        
        
    def run(self):
        """Main function để chạy mapping"""
        try:
            # Tìm matches
            url_mapping = self.find_matching_content()
            
            # Update database
            if url_mapping:
                self.update_urls(url_mapping)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error in mapping process: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            return False

def main():
    try:
        # Khởi tạo mapping object với session
        mapping = MappingLinkGetfly()
        
        # Chạy mapping
        success = mapping.run()
        
        if success:
            logger.info("Mapping completed successfully")
        else:
            logger.error("Mapping failed")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")


def main():
    try:
        # Khởi tạo mapping object với session
        mapping = MappingLinkGetfly()
        
        # Chạy mapping
        success = mapping.run()
        
        if success:
            logger.info("Mapping completed successfully")
        else:
            logger.error("Mapping failed")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()