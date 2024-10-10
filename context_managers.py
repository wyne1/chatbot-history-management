import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
from utils.redis_client import get_redis_client
from utils.mongo_client import get_mongo_client
from summarization import summarize_chat_history
import threading
from datetime import datetime

class ExistingApproach:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.mongo_db = get_mongo_client()
        self.collection = self.mongo_db['chat_history']

    def get_internal_state(self, user_id):
        return {
            "redis": self.get_redis_data(user_id),
            "mongodb": self.get_mongodb_data(user_id)
        }
    
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

    def get_mongodb_data(self, user_id):
        mongodb_data = list(self.collection.find({"UserId": user_id}).sort("Timestamp", 1))
        for doc in mongodb_data:
            doc['_id'] = str(doc['_id'])
        return mongodb_data
    
    def add_message(self, user_id, message_dict):
        stack_key = f"{user_id}:stack"
        batch_id_key = f"{user_id}:batch_id"

        batch_id = self.redis_client.get(batch_id_key)
        batch_id = int(batch_id) if batch_id else 1

        timestamp = datetime.now().isoformat()
        message = {
            "batch_id": batch_id,
            "content": message_dict,
            "timestamp": timestamp
        }

        self.redis_client.rpush(stack_key, json.dumps(message))

        message_doc = {
            "UserId": user_id,
            "Timestamp": timestamp,
            "Content": message_dict,
            "BatchId": batch_id
        }
        self.collection.insert_one(message_doc)

        if self._count_messages_with_batch(stack_key, batch_id) == 10:
            self._create_summary(user_id, batch_id)
            self.redis_client.set(batch_id_key, batch_id + 1)

    def get_context(self, user_id):
        summary_key = f"{user_id}:summary"
        summary = self.redis_client.get(summary_key)
        history = []

        if summary:
            history.append(json.loads(summary))

        stack_key = f"{user_id}:stack"
        remaining_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
        history.extend(remaining_messages)

        return history

    def _count_messages_with_batch(self, stack_key, batch_id):
        count = 0
        messages = self.redis_client.lrange(stack_key, 0, -1)
        for msg in messages:
            message = json.loads(msg)
            if message["batch_id"] == batch_id:
                count += 1
        return count

    def _create_summary(self, user_id, batch_id):
        stack_key = f"{user_id}:stack"
        all_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
        messages = [msg for msg in all_messages if msg["batch_id"] == batch_id]

        summary_content = summarize_chat_history(messages)
        summary = {
            "batch_id": batch_id,
            "content": summary_content,
            "count": len(messages)
        }

        summary_key = f"{user_id}:summary"
        self.redis_client.set(summary_key, json.dumps(summary))

        remaining_messages = [msg for msg in all_messages if msg["batch_id"] != batch_id]

        self.redis_client.delete(stack_key)
        for msg in remaining_messages:
            self.redis_client.rpush(stack_key, json.dumps(msg))

class HierarchicalSummary:
    def __init__(self):
        self.levels = {1: [], 2: [], 3: [], 4: []}

    def add_message(self, user_id, message_dict):
        self.levels[1].append(message_dict)
        if len(self.levels[1]) % 10 == 0:
            summary = summarize_chat_history(self.levels[1][-10:])
            self.levels[2].append(summary)
            if len(self.levels[2]) % 10 == 0:
                summary = summarize_chat_history(self.levels[2][-10:])
                self.levels[3].append(summary)
                if len(self.levels[3]) % 10 == 0:
                    summary = summarize_chat_history(self.levels[3][-10:])
                    self.levels[4].append(summary)

    def get_context(self, user_id, num_messages=10):
        context = []
        context.extend(self.levels[4][-1:])
        context.extend(self.levels[3][-3:])
        context.extend(self.levels[2][-5:])
        context.extend(self.levels[1][-num_messages:])
        return context
    
    def get_internal_state(self, user_id):
        return {
            "level1": self.levels[1],
            "level2": self.levels[2],
            "level3": self.levels[3],
            "level4": self.levels[4]
        }

class KeywordExtractor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.messages = []
        self.importance_scores = np.array([])

    def add_message(self, user_id, message):
        self.messages.append(message['content'])
        self._update_importance_scores()

    def _update_importance_scores(self):
        if len(self.messages) > 1:
            tfidf_matrix = self.vectorizer.fit_transform(self.messages)
            self.importance_scores = np.mean(tfidf_matrix.toarray(), axis=1)

    def get_context(self, user_id, top_n=10):
        if self.importance_scores.size == 0:
            return self.messages
        indices = np.argsort(self.importance_scores)[-top_n:]
        return [self.messages[i] for i in indices]

    def get_internal_state(self, user_id):
        return {
            "messages": self.messages,
            "importance_scores": self.importance_scores.tolist() if self.importance_scores.size > 0 else []
        }
    
class TopicClusterer:
    def __init__(self, num_topics=5):
        self.vectorizer = TfidfVectorizer()
        self.kmeans = KMeans(n_clusters=num_topics)
        self.messages = []
        self.topics = []

    def add_message(self, user_id, message_dict):
        self.messages.append(message_dict['content'])
        self._update_topics()

    def _update_topics(self):
        if len(self.messages) > self.kmeans.n_clusters:
            tfidf_matrix = self.vectorizer.fit_transform(self.messages)
            self.topics = self.kmeans.fit_predict(tfidf_matrix)

    def get_context(self, user_id, topic_id=None):
        if topic_id is None or not self.topics:
            return self.messages
        return [msg for msg, topic in zip(self.messages, self.topics) if topic == topic_id]
    
    def get_internal_state(self, user_id):
        return {
            "messages": self.messages,
            "topics": self.topics.tolist() if len(self.topics) > 0 else []
        }

class SlidingWindowContext:
    def __init__(self, window_size=20):
        self.window_size = window_size
        self.messages = []

    def add_message(self, user_id, message_dict):
        self.messages.append(message_dict)
        if len(self.messages) > self.window_size:
            self.messages.pop(0)

    def get_context(self, user_id):
        return self.messages
    
    def get_internal_state(self, user_id):
        return {
            "window": self.messages
        }

class HybridStorage:
    def __init__(self):
        self.memory_cache = {}
        self.redis_client = get_redis_client()
        self.mongo_client = get_mongo_client()

    def add_message(self, user_id, message_dict):
        if user_id not in self.memory_cache:
            self.memory_cache[user_id] = []
        self.memory_cache[user_id].append(message_dict)
        if len(self.memory_cache[user_id]) > 200:
            self.memory_cache[user_id].pop(0)

        # Add to Redis (recent history)
        self.redis_client.lpush(f"user:{user_id}:messages", json.dumps(message_dict))
        self.redis_client.ltrim(f"user:{user_id}:messages", 0, 999)

        # Add to MongoDB (long-term storage)
        self.mongo_client.chat_history.insert_one({"user_id": user_id, "message": message_dict})

    def get_context(self, user_id):
        context = {
            "recent": self.memory_cache.get(user_id, []),
            "mid_term": [json.loads(msg) for msg in self.redis_client.lrange(f"user:{user_id}:messages", 0, -1)],
            "long_term": list(self.mongo_client.chat_history.find({"user_id": user_id}).sort("_id", -1).limit(1000))
        }
        return context
    
    def get_internal_state(self, user_id):
        return {
            "memory_cache": self.memory_cache.get(user_id, []),
            "redis": [json.loads(msg) for msg in self.redis_client.lrange(f"user:{user_id}:messages", 0, -1)],
            "mongodb": list(self.mongo_client.chat_history.find({"user_id": user_id}).sort("_id", -1).limit(1000))
        }