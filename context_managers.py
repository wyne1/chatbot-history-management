import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
from utils.redis_client import get_redis_client
from utils.mongo_client import get_mongo_client
from summarization import summarize_chat_history
import threading
from datetime import datetime
from utils.token_counter import count_tokens

class ExistingApproach:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.mongo_db = get_mongo_client()
        self.collection = self.mongo_db['chat_history']

        self.clear_all_mongodb_data()
        self.clear_all_redis_data()
    def clear_all_redis_data(self):
        print("Clearing Redis data")
        try:
            self.redis_client.flushdb()
            print("Successfully cleared all data in the current Redis database.")
        except Exception as e:
            print(f"Error clearing Redis data: {e}")
    
    def clear_all_mongodb_data(self):
        try:
            # Delete all documents in the collection
            print("Clearing MongoDB data")
            result = self.collection.delete_many({})
        except Exception as e:
            print(f"Error clearing MongoDB data: {e}")

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

        if self._count_messages_with_batch(stack_key, batch_id) == 20:
            self._create_summary(user_id, batch_id)
            self.redis_client.set(batch_id_key, batch_id + 1)

    # def get_context(self, user_id):
    #     summary_key = f"{user_id}:summary"
    #     summary = self.redis_client.get(summary_key)
    #     history = []

    #     if summary:
    #         history.append(json.loads(summary))

    #     stack_key = f"{user_id}:stack"
    #     remaining_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
    #     history.extend(remaining_messages)

    #     print(f"History: {history}")

    #     return history

    def get_context(self, user_id):
        summary_key = f"{user_id}:summary"
        stack_key = f"{user_id}:stack"

        summaries = self.redis_client.get(summary_key)
        summaries = json.loads(summaries) if summaries else []

        recent_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]

        # Format the context
        context = ""

        # Add summaries of previous batches
        if summaries:
            context += "Summaries of previous conversations:\n"
            for summary in summaries:
                context += f"Batch {summary['batch_id']}: {summary['content']}\n\n"

        # Add current conversation
        if recent_messages:
            context += "Current conversation:\n"
            for msg in recent_messages:
                if isinstance(msg['content'], dict):
                    role = msg['content'].get('role', 'unknown')
                    content = msg['content'].get('content', '')
                    context += f"{role.capitalize()}: {content}\n"
                else:
                    context += f"Message: {msg['content']}\n"

        return context.strip()

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
        messages_to_summarize = [msg["content"] for msg in all_messages if msg["batch_id"] == batch_id]

        summary_content = summarize_chat_history(messages_to_summarize)
        summary = {
            "batch_id": batch_id,
            "content": summary_content,
            "count": len(messages_to_summarize)
        }

        summary_key = f"{user_id}:summary"
        existing_summaries = self.redis_client.get(summary_key)
        if existing_summaries:
            existing_summaries = json.loads(existing_summaries)
            existing_summaries.append(summary)
        else:
            existing_summaries = [summary]

        self.redis_client.set(summary_key, json.dumps(existing_summaries))

        remaining_messages = [msg for msg in all_messages if msg["batch_id"] != batch_id]
        self.redis_client.delete(stack_key)
        for msg in remaining_messages:
            self.redis_client.rpush(stack_key, json.dumps(msg))

class EnhancedExistingApproach:
    def __init__(self, max_tokens=4000):
        self.redis_client = get_redis_client()
        self.mongo_db = get_mongo_client()
        self.collection = self.mongo_db['chat_history']
        self.max_tokens = max_tokens

        self.clear_all_mongodb_data()
        self.clear_all_redis_data()

    def clear_all_redis_data(self):
        print("Clearing Redis data")
        try:
            self.redis_client.flushdb()
            print("Successfully cleared all data in the current Redis database.")
        except Exception as e:
            print(f"Error clearing Redis data: {e}")

    def clear_all_mongodb_data(self):
        try:
            # Delete all documents in the collection
            print("Clearing MongoDB data")
            result = self.collection.delete_many({})
        except Exception as e:
            print(f"Error clearing MongoDB data: {e}")

    def add_message(self, user_id, message_dict):
        stack_key = f"{user_id}:stack"
        summary_key = f"{user_id}:summary"
        batch_id_key = f"{user_id}:batch_id"

        batch_id = self.redis_client.get(batch_id_key)
        batch_id = int(batch_id) if batch_id else 1

        message = {
            "batch_id": batch_id,
            "content": message_dict['content'],
            "timestamp": datetime.now().isoformat()
        }

        self.redis_client.rpush(stack_key, json.dumps(message))
        self.collection.insert_one({
            "UserId": user_id,
            "Timestamp": message["timestamp"],
            "Content": message_dict['content'],
            "BatchId": batch_id
        })

        messages_in_batch = self._count_messages_with_batch(stack_key, batch_id)
        if messages_in_batch == 10:
            self._create_summary(user_id, batch_id)
            self.redis_client.set(batch_id_key, batch_id + 1)

        self._manage_token_limit(user_id)

    def get_context(self, user_id):
        context = self._get_full_context(user_id)
        return self._truncate_context(context)

    def _get_full_context(self, user_id):
        summary_key = f"{user_id}:summary"
        stack_key = f"{user_id}:stack"

        summary = self.redis_client.get(summary_key)
        summary = json.loads(summary) if summary else []

        recent_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]

        context = ""
        if summary:
            context += "Summary: " + " ".join([s['content'] for s in summary]) + "\n\n"
        if recent_messages:
            context += "Recent messages: " + " ".join([m['content'] for m in recent_messages])

        return context

    def _truncate_context(self, context):
        while count_tokens(context) > self.max_tokens:
            parts = context.split("\n\n", 1)
            if len(parts) > 1:
                summary, recent_messages = parts
                if summary.startswith("Summary:"):
                    summary_parts = summary.split(". ")
                    if len(summary_parts) > 1:
                        summary = "Summary: " + ". ".join(summary_parts[1:])
                    else:
                        summary = ""
                else:
                    recent_messages = recent_messages.split(". ", 1)[1] if ". " in recent_messages else ""
                context = f"{summary}\n\n{recent_messages}".strip()
            else:
                context = context[:int(self.max_tokens * 0.9)]

        return context

    def _manage_token_limit(self, user_id):
        context = self._get_full_context(user_id)
        truncated_context = self._truncate_context(context)
        
        summary_key = f"{user_id}:summary"
        stack_key = f"{user_id}:stack"
        
        parts = truncated_context.split("\n\n", 1)
        if len(parts) > 1:
            summary, recent_messages = parts
            self.redis_client.set(summary_key, json.dumps([{"content": summary[8:]}]))  # Remove "Summary: " prefix
            self.redis_client.delete(stack_key)
            for msg in recent_messages[17:].split(". "):  # Remove "Recent messages: " prefix
                self.redis_client.rpush(stack_key, json.dumps({"content": msg.strip()}))
        else:
            self.redis_client.delete(summary_key)
            self.redis_client.delete(stack_key)
            self.redis_client.rpush(stack_key, json.dumps({"content": truncated_context}))

    def _count_messages_with_batch(self, stack_key, batch_id):
        count = 0
        messages = self.redis_client.lrange(stack_key, 0, -1)
        for msg in messages:
            message = json.loads(msg)
            if message.get("batch_id") == batch_id:
                count += 1
        return count

    def _create_summary(self, user_id, batch_id):
        stack_key = f"{user_id}:stack"
        all_messages = [json.loads(msg) for msg in self.redis_client.lrange(stack_key, 0, -1)]
        messages_to_summarize = [msg["content"] for msg in all_messages if msg.get("batch_id") == batch_id]

        summary_content = summarize_chat_history(messages_to_summarize)
        summary = {
            "batch_id": batch_id,
            "content": summary_content,
            "count": len(messages_to_summarize)
        }

        summary_key = f"{user_id}:summary"
        existing_summary = self.redis_client.get(summary_key)
        if existing_summary:
            existing_summary = json.loads(existing_summary)
        else:
            existing_summary = []

        existing_summary.append(summary)

        self.redis_client.set(summary_key, json.dumps(existing_summary))

        remaining_messages = [msg for msg in all_messages if msg.get("batch_id") != batch_id]
        self.redis_client.delete(stack_key)
        for msg in remaining_messages:
            self.redis_client.rpush(stack_key, json.dumps(msg))

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

        print("Context: ", context)
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
    
# class TopicClusterer:
#     def __init__(self, num_topics=5):
#         self.vectorizer = TfidfVectorizer()
#         self.kmeans = KMeans(n_clusters=num_topics)
#         self.messages = []
#         self.topics = []

    
#     def add_message(self, user_id, message_dict):
#         self.messages.append(message_dict['content'])
#         self._update_topics()

#     def _update_topics(self):
#         print("Updating topics")
#         if len(self.messages) > self.kmeans.n_clusters:
#             tfidf_matrix = self.vectorizer.fit_transform(self.messages)
#             self.topics = self.kmeans.fit_predict(tfidf_matrix)

#         print(f"Topics: {self.topics}")
#     def get_context(self, user_id, topic_id=None):
#         if topic_id is None or not self.topics:
#             return self.messages
#         return [msg for msg, topic in zip(self.messages, self.topics) if topic == topic_id]
    
#     def get_internal_state(self, user_id):
#         return {
#             "messages": self.messages,
#             "topics": self.topics.tolist() if len(self.topics) > 0 else []
#         }
    

class TopicClusterer:
    def __init__(self, max_tokens=4000, max_clusters=5):
        self.redis_client = get_redis_client()
        self.mongo_db = get_mongo_client()
        self.collection = self.mongo_db['chat_history']
        self.max_tokens = max_tokens
        self.max_clusters = max_clusters
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.kmeans = KMeans(n_clusters=self.max_clusters)

        self.clear_all_redis_data()
    def clear_all_redis_data(self):
        print("Clearing Redis data")
        try:
            self.redis_client.flushdb()
            print("Successfully cleared all data in the current Redis database.")
        except Exception as e:
            print(f"Error clearing Redis data: {e}")
    
    def add_message(self, user_id, message_dict):
        messages_key = f"{user_id}:messages"
        clusters_key = f"{user_id}:clusters"

        # Add message to Redis
        self.redis_client.rpush(messages_key, json.dumps(message_dict))

        # Retrieve all messages
        messages = [json.loads(msg) for msg in self.redis_client.lrange(messages_key, 0, -1)]

        # Perform clustering
        if len(messages) >= self.max_clusters:
            self._cluster_messages(user_id, messages)

        # Manage token limit
        self._manage_token_limit(user_id)

    def get_context(self, user_id):
        clusters_key = f"{user_id}:clusters"
        messages_key = f"{user_id}:messages"

        clusters = self.redis_client.get(clusters_key)
        clusters = json.loads(clusters) if clusters else []

        recent_messages = [json.loads(msg) for msg in self.redis_client.lrange(messages_key, -5, -1)]

        context = "Topic summaries:\n"
        for cluster in clusters:
            context += f"- {cluster['summary']}\n"

        context += "\nRecent messages:\n"
        for msg in recent_messages:
            context += f"{msg['role']}: {msg['content']}\n"

        return context

    def _cluster_messages(self, user_id, messages):
        texts = [msg['content'] for msg in messages]
        X = self.vectorizer.fit_transform(texts)
        labels = self.kmeans.fit_predict(X)

        clusters = [[] for _ in range(self.max_clusters)]
        for msg, label in zip(messages, labels):
            clusters[label].append(msg)

        summaries = []
        for cluster in clusters:
            if cluster:
                summary = summarize_chat_history([msg['content'] for msg in cluster])
                summaries.append({"summary": summary, "size": len(cluster)})

        clusters_key = f"{user_id}:clusters"
        self.redis_client.set(clusters_key, json.dumps(summaries))

    def _manage_token_limit(self, user_id):
        context = self.get_context(user_id)
        while count_tokens(context) > self.max_tokens:
            clusters_key = f"{user_id}:clusters"
            messages_key = f"{user_id}:messages"

            clusters = self.redis_client.get(clusters_key)
            clusters = json.loads(clusters) if clusters else []

            if clusters:
                # Remove the smallest cluster
                clusters.sort(key=lambda x: x['size'])
                clusters.pop(0)
                self.redis_client.set(clusters_key, json.dumps(clusters))
            elif self.redis_client.llen(messages_key) > 0:
                # If no clusters, remove oldest message
                self.redis_client.lpop(messages_key)
            else:
                # If both clusters and messages are empty, break to avoid infinite loop
                break

            context = self.get_context(user_id)
    
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
        print(f"Length of messages: {len(self.messages)}")
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