from config.env_config import MILVUS_USERNAME, MILVUS_PASSWORD, MILVUS_HOST, MILVUS_PORT, MILVUS_DB, RUNTIME_ENVIRONMENT
from pymilvus import connections, utility, CollectionSchema, Collection, SearchResult
from pqdict import pqdict
from pathlib import Path
import sys
import yaml
import time
import threading
from typing import List, Any

import numpy as np

from utils.log_utils import get_logger
logger = get_logger(__name__)

# Load environment

HOME = str(Path(__file__).parent)
HOME = Path(HOME).parent

DEFAULT_TIMEOUT = 20

config_file = str(HOME) + "/config/milvus_connect.yaml"

with open(config_file, "r") as f:
    config = yaml.safe_load(f)

# Load by Queue


class MilvusLoadedQueue:
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.queue = pqdict.minpq()  # min heap

    def put(self, collection_name, log=True):
        if len(self.queue) >= self.maxsize and collection_name not in self.queue:
            oldest_collection_name, _ = self.queue.popitem()
            logger.info(f"Remove & release collection {oldest_collection_name}!")
            # release collection in another thread
            threading.Thread(target=release_collection, args=(collection_name,)).start()
        is_new = collection_name not in self.queue
        self.queue[collection_name] = time.time()
        if log:
            if is_new:
                logger.info(
                    "[%s/%s] Add collection %s: %s to queue!",
                    len(self.queue),
                    self.maxsize,
                    collection_name,
                    self.queue[collection_name],
                )
            else:
                logger.info(
                    "[%s/%s] Update collection %s: %s in queue!",
                    len(self.queue),
                    self.maxsize,
                    collection_name,
                    self.queue[collection_name],
                )


MAX_LOADED_COLLECTION = 20
MILVUS_LOADED_PQUEUE = MilvusLoadedQueue(MAX_LOADED_COLLECTION)

# Milvus utility function


def initialize_milvus_connection(timeout=DEFAULT_TIMEOUT):
    try:
        start_time = time.time()
        connections.connect(user=MILVUS_USERNAME, password=MILVUS_PASSWORD, host=MILVUS_HOST, port=MILVUS_PORT, db_name=MILVUS_DB, timeout=timeout)
        logger.info(
            f"Initialize Milvus connection successfully cost {str(time.time() - start_time)} seconds!"
        )
    except:
        logger.exception("Connect to Milvus failed!")
        sys.exit(1)
    return config


def create_schema(fields, name_collection):
    try:
        schema = CollectionSchema(
            fields,
            description=f"Vector DB Search for a {name_collection}.",
            enable_dynamic_field=True,
        )
    except:
        logger.exception("Create schema failed!")
        return None
    return schema


def check_collection(collection_name, timeout=DEFAULT_TIMEOUT):
    try:
        start_time = time.time()
        is_exist = utility.has_collection(collection_name, timeout=timeout)
        logger.info(
            f"Check collection {collection_name} cost {str(time.time() - start_time)} seconds!"
        )
        return is_exist
    except:
        logger.exception(f"Check collection {collection_name} failed!")
        return None


def check_collection(collection_name, timeout=DEFAULT_TIMEOUT):
    try:
        start_time = time.time()
        is_exist = utility.has_collection(collection_name, timeout=timeout)
        logger.info(
            f"Check collection {collection_name} cost {str(time.time() - start_time)} seconds!"
        )
        return is_exist
    except:
        logger.exception(f"Check collection {collection_name} failed!")
        return None


def load_collection(collection_name, timeout=DEFAULT_TIMEOUT, loaded=True):
    try:
        start_time = time.time()
        collection = Collection(name=collection_name, timeout=timeout)
        if loaded:
            collection.load(timeout=timeout)
            MILVUS_LOADED_PQUEUE.put(collection_name)
        logger.info(
            f"Load collection {collection_name} cost {str(time.time() - start_time)} seconds!"
        )
        return collection
    except:
        logger.exception(f"Load collection {collection_name} failed!")
        return None


def release_collection(collection_name, timeout=DEFAULT_TIMEOUT):
    try:
        start_time = time.time()
        collection = Collection(name=collection_name, timeout=timeout)
        logger.info(
            f"Release collection {collection_name} cost {str(time.time() - start_time)} seconds!"
        )
        return True
    except:
        logger.exception(f"Release collection {collection_name} failed!")
        return False


def drop_collection(collection_name, timeout=DEFAULT_TIMEOUT):
    try:
        start_time = time.time()
        if check_collection(collection_name, timeout=timeout):
            start_time = time.time()
            utility.drop_collection(collection_name, timeout=timeout)
        logger.info(
            f"Drop collection {collection_name} cost {str(time.time() - start_time)} seconds!"
        )
        return True
    except:
        logger.exception(f"Drop collection {collection_name} failed!")
        return False


def create_collection(
    fields,
    name_prefix,
    name_collection,
    index_field,
    index_params,
    timeout=DEFAULT_TIMEOUT,
):
    start_time = time.time()
    schema = create_schema(fields, name_collection)
    if schema is None:
        return False
    name_index = name_prefix + name_collection
    try:
        is_exist_collection = check_collection(name_index)
        if is_exist_collection:
            logger.info(f"Collection {name_index} exists, re-create it!")
            _ = drop_collection(name_index)
        collection = Collection(name=name_index, schema=schema, timeout=timeout)
        collection.create_index(
            field_name=index_field, index_params=index_params, timeout=timeout
        )
        logger.info(
            f"Create collection {name_index} cost {str(time.time() - start_time)} seconds!"
        )
        result = True
    except:
        logger.exception("Create collection failed!")
        result = False
    return result


def insert_data(collection, datas, timeout=DEFAULT_TIMEOUT):

    try:
        start_time = time.time()
        status = collection.insert(datas, timeout=timeout)
        logger.info(
            "Insert data successfully, time used: %.2f", (time.time() - start_time)
        )
        return status
    except:
        logger.exception("Insert data failed")
        return None


def __search_extract__(search_results, text_filed, source_fileds, limit):
    """
    Extract Milvus search results to sources and  relevant contexts
    """
    if not search_results:
        return [], []
    relevant_contexts = {}
    for q_idx, _ in enumerate(search_results):
        for idx, _ in enumerate(search_results[q_idx].ids):
            chunk_id = search_results[q_idx].ids[idx]
            chunk_distance = search_results[q_idx].distances[idx]
            if chunk_id in relevant_contexts:
                relevant_contexts[chunk_id]["chunk_distance"] = min(
                    relevant_contexts[chunk_id]["chunk_distance"],
                    chunk_distance,
                )
            chunk_text = search_results[q_idx][idx].entity.get(text_filed)
            source_values = [
                search_results[q_idx][idx].entity.get(x) for x in source_fileds
            ]
            relevant_contexts[chunk_id] = {
                "chunk_text": chunk_text,
                "chunk_distance": float(chunk_distance),
                "name": source_values[0],
                "page": int(source_values[1]),
            }
            # sort by distance
    relevant_contexts = list(
        dict(
            sorted(
                relevant_contexts.items(),
                key=lambda item: item[1]["chunk_distance"],
            )
        ).items()
    )

    # To remove duplicate entries
    unique_relevant_contexts = []
    seen = set()
    for item in relevant_contexts:
        chunk_to_embed = item[1]["chunk_text"]
        if chunk_to_embed not in seen:
            unique_relevant_contexts.append(item)
            seen.add(chunk_to_embed)

    # return top limit chunk_text
    if unique_relevant_contexts:
        if unique_relevant_contexts[:limit][0][1]["chunk_distance"] > 0.4:
            relevant_chunks = []
        else:
            relevant_chunks = [
                x[1]["chunk_text"] for x in unique_relevant_contexts[:limit]
            ]

        relevant_sources = []
        for x in unique_relevant_contexts[:limit]:
            source_name = x[1]["name"]
            source_page = int(x[1]["page"])
            distance = float(x[1]["chunk_distance"])
            chunk_text = x[1]["chunk_text"]
            relevant_sources.append(
                {
                    "name": source_name,
                    "page": source_page,
                    "distance": distance,
                    "content": chunk_text,
                    "type": "pdf" if source_name.endswith(".pdf") else "website",
                }
            )
        return relevant_chunks, relevant_sources
    else:
        return [], []


def search(
    input_embeddings: List[Any],
    loaded_collection: Collection,
    embed_field: str,
    text_field: str,
    limit,
    source_fields: List[str] = [],
    search_limit: int = 20,
    method: str = "expand",
    search_param={"metric_type": "L2", "params": {"nprobe": 10}},
    timeout=DEFAULT_TIMEOUT,
):
    try:
        start_time = time.time()
        if method not in ["expand", "avg"]:
            raise ValueError(
                "Invalid method: {}, must be one of expand or avg".format(method)
            )
        if method == "avg":
            input_embeddings = [np.mean(input_embeddings, axis=0)]
        results: SearchResult = loaded_collection.search(
            data=input_embeddings,
            anns_field=embed_field,
            output_fields=[text_field] + source_fields,
            param=search_param,
            limit=search_limit,
            timeout=timeout,
        )
        logger.info(
            f"Search {len(input_embeddings)} embeddings cost {str(time.time() - start_time)} seconds!"
        )
        return results
        # return __search_extract__(results, text_field, source_fields, limit)
    except:
        logger.exception("Search failed!")
        return None, None
