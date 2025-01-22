import sys
import os

# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from source.config.env_config import DB_URL
from source.config.utils_db import Utils_DB


utils_db = Utils_DB(DB_URL)

setting_bot = utils_db.get_setting_bot()
if setting_bot is None:
    raise ValueError("Không thể lấy thông tin từ bảng SettingBot.")

class Setting():
    bot_id = setting_bot.bot_id
    app_id = setting_bot.app_id
    piscale_api_key = setting_bot.piscale_api_key
    bot_token = setting_bot.bot_token
    open_question_mode = setting_bot.open_question_mode
    max_history_messages = setting_bot.max_history_messages
    timezone = setting_bot.timezone
    bot_name = setting_bot.bot_name
    temperature = setting_bot.temperature
    enable_references = setting_bot.enable_references
    max_references = setting_bot.max_references
    answer_prompt = setting_bot.answer_prompt
    rewrite_prompt = setting_bot.rewrite_prompt
    summary_prompt = setting_bot.summary_prompt
    detect_language_prompt = setting_bot.detect_language_prompt
    routing_prompt = setting_bot.routing_prompt
    llm_model = setting_bot.llm_model
    overload_message = setting_bot.overload_message
    default_message = setting_bot.default_message