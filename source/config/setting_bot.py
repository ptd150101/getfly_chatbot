DEFAULT_BOT_SETTINGS = {
    "open_question_mode": "never",
    "max_history_messages": 4,
    "timezone": "Asia/Ho_Chi_Minh", 
    "bot_name": "Getfly Pro",
    "min_sentences": 4,
    "max_sentences": 8,
    "temperature": 0.1,
    "open_question_formats": {
        "always": {
            "instruction": "7. Luôn luôn kết thúc phản hồi của bạn bằng một câu hỏi mở để xem liệu người dùng có thêm câu hỏi hoặc cần hỗ trợ thêm không.\nNOTE: CÂU HỎI MỞ PHẢI LIÊN QUAN ĐẾN NGỮ CẢNH TRUY XUẤT, ĐẦU VÀO, CÂU TRẢ LỜI TRƯỚC ĐÓ CỦA NGƯỜI DÙNG VÀ LỊCH SỬ TÓM TẮT.",
            "format": "\nCâu hỏi mở\n"
        },
        "never": {
            "instruction": "7. Không sử dụng câu hỏi mở trong câu trả lời.",
            "format": ""
        },
        "auto": {
            "instruction": "7. Tự quyết định việc sử dụng câu hỏi mở dựa trên ngữ cảnh và nội dung trả lời.", 
            "format": "\nCâu hỏi mở (nếu có)\n"
        }
    }
}

# Cấu hình cho từng bot cụ thể 
GETFLY_BOT_SETTINGS = {
    **DEFAULT_BOT_SETTINGS,
    "bot_name": "Getfly Pro",
    # Override các settings khác
}

CUSTOM_BOT_SETTINGS = {
    **DEFAULT_BOT_SETTINGS,
    "bot_name": "Custom Bot", 
    # Override các settings khác
}