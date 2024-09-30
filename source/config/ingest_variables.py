from pymilvus import DataType
from dataclasses import dataclass

@dataclass
class IngestionConfig:
    WINDOW_SIZE = 2000
    STRIDE = 1300
    MAX_CHUNK_LENGTH = 4000
    D_TYPE = {
        "BOOL": DataType.BOOL,
        "INT8": DataType.INT8,
        "INT16": DataType.INT16,
        "INT32": DataType.INT32,
        "INT64": DataType.INT64,
        "VARCHAR": DataType.VARCHAR,
        "FLOAT_VECTOR": DataType.FLOAT_VECTOR,
    }

    # Define average characters per token for different languages
    CHARS_PER_TOKEN_DICT = {
        "en": 4,  # Consider English 4 chars/token
    }
