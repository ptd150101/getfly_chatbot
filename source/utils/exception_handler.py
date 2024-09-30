
# BOTH
SUCCESS = 200
VECTORDB_ERROR = -201
LLM_ERROR = -401
INTERNAL_SERVER_ERROR = -500
BAD_REQUEST = -501

# CHAT
SUCCESS = 200
DATABASE_ERROR = -201
NOT_FOUND_DATA = -202
OPENAI_ERROR = -301
INTERNAL_SERVER_ERROR = -500
BAD_REQUEST = -501
EMPTY_MESSAGE = -502
LOGIC_MODULE_ERROR = -503

# INGEST
DATA_ERROR = -10100
EMPTY_DATA = -10101
LANGUAGE_ERROR = -10102
READ_PERMISSION_ERROR = -10105
UNSUPPORTED_DOCUMENT_TYPE = -10106
UNREADABLE = -10503

class StatusCode:
    def __init__(self):
        self.status_chat_dict = {
            SUCCESS: "Success",
            DATABASE_ERROR: "Database Error",
            NOT_FOUND_DATA: "Not Found Data",
            LLM_ERROR: "Language Model Error",
            INTERNAL_SERVER_ERROR: "Internal Server Error",
            BAD_REQUEST: "Error in Input Data Validation",
            EMPTY_MESSAGE: "Empty Message",
            LOGIC_MODULE_ERROR: "Logic Module Error",
        }

    def get_response(self, status):
        if status in self.status_chat_dict:
            self.response = {
                "status_code": status,
                "message": self.status_chat_dict[status],
            }
        else:
            self.response = {"status_code": status, "message": ""}
        return self.response


class ChatbotServiceException:
    def __init__(self, error_code):
        status = StatusCode()
        self.result = status.get_response(error_code)


if __name__ == "__main__":
    print(ChatbotServiceException(SUCCESS).result)
