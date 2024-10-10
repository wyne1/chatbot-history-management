import faiss
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
from typing import List, Dict, Tuple
import json

class AdvancedContextManager:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.short_term_memory: List[Dict] = []
        self.long_term_memory: List[Dict] = []
        self.index = faiss.IndexFlatL2(384)  # 384 is the embedding dimension for the chosen model
        self.max_short_term_tokens = 800
        self.max_context_tokens = 2000

    def add_message(self, user_id: str, message: Dict):
        # Add to short-term memory
        print(message)
        self.short_term_memory.append(message)
        print("short_term_memory", self.short_term_memory)
        self._trim_short_term_memory()

        # Add to long-term memory
        embedding = self._get_embedding(message['content'])
        print("embedding", embedding)
        self.long_term_memory.append({**message, 'embedding': embedding})
        self.index.add(np.array([embedding]))

    def get_context(self, user_id: str) -> str:
        context = self._get_short_term_context()
        long_term_context = self._get_long_term_context(user_id)
        return json.dumps(context + long_term_context)

    def _get_embedding(self, text: str) -> np.ndarray:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

    def _trim_short_term_memory(self):
        while len(self.short_term_memory) > 4 or self._count_tokens(self.short_term_memory) > self.max_short_term_tokens:
            self.short_term_memory.pop(0)

    def _get_short_term_context(self) -> List[Dict]:
        return self.short_term_memory

    def _get_long_term_context(self, user_id: str) -> List[Dict]:
        if not self.long_term_memory:
            return []

        query = self.short_term_memory[-1]['content'] if self.short_term_memory else ""
        query_embedding = self._get_embedding(query)

        k = min(5, len(self.long_term_memory))  # Get top 5 or all if less than 5
        D, I = self.index.search(np.array([query_embedding]), k)

        results = [self.long_term_memory[i] for i in I[0]]
        results.sort(key=lambda x: x['timestamp'], reverse=True)  # Sort by recency

        return results[:2]  # Return top 2 most relevant and recent

    def _count_tokens(self, messages: List[Dict]) -> int:
        return sum(len(self.tokenizer.encode(msg['content'])) for msg in messages)

    def get_internal_state(self, user_id: str) -> Dict:
        return {
            "short_term_memory": self.short_term_memory,
            "long_term_memory_size": len(self.long_term_memory),
            "current_context_tokens": self._count_tokens(self.short_term_memory)
        }