import psycopg2
import logging

# Khởi tạo logger
logger = logging.getLogger(__name__)

class Utils_DB():
    def __init__(self, db_url):
        # Khởi tạo logger
        self.connection = psycopg2.connect(db_url)

    def get_setting_bot(self, bot_id):
        """Lấy thông tin từ bảng SettingBot."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM setting_bots WHERE bot_id = %s;", (bot_id,))
            result = cursor.fetchone()  # Lấy một dòng dữ liệu
            cursor.close()
            if result is None:
                return None  # Trả về None nếu không có dữ liệu
            return result  # Trả về kết quả hợp lệ
        except Exception as e:
            logger.error(f"Không thể lấy thông tin từ bảng SettingBot: {str(e)}")
            return None