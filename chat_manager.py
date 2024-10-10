# chat_manager.py

import threading
import json
from datetime import datetime
from context_managers import ExistingApproach, HierarchicalSummary, KeywordExtractor, TopicClusterer, SlidingWindowContext, HybridStorage
from advanced_context_manager import AdvancedContextManager
from utils.redis_client import get_redis_client
from utils.mongo_client import get_mongo_client
from summarization import summarize_chat_history
import logging

logger = logging.getLogger(__name__)
# class ChatManager:
#     def __init__(self):
#         self.redis_client = get_redis_client()
#         self.mongo_db = get_mongo_client()
#         self.collection = self.mongo_db['chat_history']
#         self.lock = threading.Lock()

#     def count_messages_with_batch(self, stack_key, batch_id):
#         """
#         Count the number of messages in the specified stack that have the given batch_id.
#         """
#         count = 0
#         # Retrieve all messages from the Redis stack
#         messages = self.redis_client.lrange(stack_key, 0, -1)

#         # Count messages with the specified batch_id
#         for msg in messages:
#             message = json.loads(msg)
#             if message["batch_id"] == batch_id:
#                 count += 1
#         return count

#     def handle_new_message(self, user_id, message_dict):
#         with self.lock:
#             # Define keys for Redis
#             stack_key = f"{user_id}:stack"  # Stores individual messages for a particular user
#             batch_id_key = f"{user_id}:batch_id"  # Stores the current batch ID for a user

#             # Retrieve the current batch ID from Redis, or initialize it
#             batch_id = self.redis_client.get(batch_id_key)
#             if batch_id is None:
#                 batch_id = 1
#             else:
#                 batch_id = int(batch_id)

#             # Create a new message dictionary with a timestamp
#             timestamp = datetime.now().isoformat()
#             message = {
#                 "batch_id": batch_id,
#                 "content": message_dict,
#                 "timestamp": timestamp
#             }

#             # Add the new message to the cache stack for the user.
#             self.redis_client.rpush(stack_key, json.dumps(message))

#             # Persist the message to MongoDB
#             message_doc = {
#                 "UserId": user_id,
#                 "Timestamp": timestamp,
#                 "Content": message_dict,
#                 "BatchId": batch_id
#             }
#             self.collection.insert_one(message_doc)

#             # Check if the stack has 20 messages for the current batch ID
#             count = self.count_messages_with_batch(stack_key, batch_id)
#             if count == 20:
#                 threading.Thread(target=self._create_summary, args=(user_id, batch_id)).start()
#                 self.redis_client.set(batch_id_key, batch_id + 1)

#     def _create_summary(self, user_id, batch_id):
#         with self.lock:
#             # Retrieve all messages for the user with the specified batch ID
#             stack_key = f"{user_id}:stack"
#             all_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
#             messages = [msg for msg in all_messages if msg["batch_id"] == batch_id]

#             # Create a summary of those messages
#             summary_content = summarize_chat_history(messages)
#             summary = {
#                 "batch_id": batch_id,
#                 "content": summary_content,
#                 "count": len(messages)
#             }

#             # Store the summary in Redis
#             summary_key = f"{user_id}:summary"
#             self.redis_client.set(summary_key, json.dumps(summary))

#             # Gather all messages from the cache which have not been summarized yet
#             remaining_messages = [msg for msg in all_messages if msg["batch_id"] != batch_id]

#             # Clear the stack and repopulate with the remaining messages
#             self.redis_client.delete(stack_key)
#             for msg in remaining_messages:
#                 self.redis_client.rpush(stack_key, json.dumps(msg))

#     def get_chat_history(self, user_id):
#         # Retrieve the summary for the user and add it to the history
#         summary_key = f"{user_id}:summary"
#         summary = self.redis_client.get(summary_key)
#         history = []

#         if summary is not None:
#             history.append(json.loads(summary))

#         # Retrieve all messages from the Redis stack which have not been summarized
#         stack_key = f"{user_id}:stack"
#         remaining_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
#         history.extend(remaining_messages)

#         return history

#     def load_messages_from_mongodb(self, user_id):
#         # Query the collection with a limit of 20 items
#         messages = list(
#             self.collection.find({"UserId": user_id})
#             .sort("Timestamp", -1)
#             .limit(20)
#         )

#         # Reset Redis state and populate messages
#         stack_key = f"{user_id}:stack"
#         summary_key = f"{user_id}:summary"
#         self.redis_client.delete(stack_key)
#         self.redis_client.delete(summary_key)

#         # Rehydrate redis cache
#         for item in reversed(messages):
#             message = {
#                 "batch_id": int(item['BatchId']),
#                 "content": item['Content'],
#                 "timestamp": item['Timestamp']
#             }
#             self.redis_client.rpush(stack_key, json.dumps(message))

#     def get_redis_data(self, user_id):
#         # Retrieve all keys related to the user
#         stack_key = f"{user_id}:stack"
#         summary_key = f"{user_id}:summary"
#         batch_id_key = f"{user_id}:batch_id"

#         redis_data = {}
#         redis_data['stack'] = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
#         summary = self.redis_client.get(summary_key)
#         redis_data['summary'] = json.loads(summary) if summary else None
#         redis_data['batch_id'] = self.redis_client.get(batch_id_key)

#         return redis_data

#     def get_mongodb_data(self, user_id):
#         # Fetch all messages for the user from MongoDB
#         mongodb_data = list(self.collection.find({"UserId": user_id}).sort("Timestamp", 1))
#         # Convert ObjectId to string
#         for doc in mongodb_data:
#             doc['_id'] = str(doc['_id'])
#         return mongodb_data


class ChatManager:
    def __init__(self):
        self.approaches = {
            'existing': ExistingApproach(),
            'hierarchical': HierarchicalSummary(),
            'keyword': KeywordExtractor(),
            'topic': TopicClusterer(),
            'sliding_window': SlidingWindowContext(),
            # 'hybrid': HybridStorage(),
            # 'advanced': AdvancedContextManager()
        }
        self.current_approach = 'existing'
        self.redis_client = get_redis_client()
        self.mongo_db = get_mongo_client()
        self.collection = self.mongo_db['chat_history']

    def set_approach(self, approach):
        if approach in self.approaches:
            self.current_approach = approach

    def handle_new_message(self, user_id, message_dict):
        self.approaches[self.current_approach].add_message(user_id, message_dict)

    def get_context(self, user_id):
        return self.approaches[self.current_approach].get_context(user_id)

    def get_redis_data(self, user_id):
        stack_key = f"{user_id}:stack"
        summary_key = f"{user_id}:summary"
        batch_id_key = f"{user_id}:batch_id"

        redis_data = {}
        redis_data['stack'] = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
        summary = self.redis_client.get(summary_key)
        redis_data['summary'] = json.loads(summary) if summary else None
        redis_data['batch_id'] = self.redis_client.get(batch_id_key)

        return redis_data
    
    def get_internal_state(self, user_id):
        logger.info(f"Getting internal state for user {user_id} with approach {self.current_approach}")
        try:
            return self.approaches[self.current_approach].get_internal_state(user_id)
        except Exception as e:
            logger.error(f"Error in get_internal_state: {str(e)}")
            raise
    
    def get_mongodb_data(self, user_id):
        mongodb_data = list(self.collection.find({"UserId": user_id}).sort("Timestamp", 1))
        for doc in mongodb_data:
            doc['_id'] = str(doc['_id'])
        return mongodb_data