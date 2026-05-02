# Vector Databases

A vector database stores embedding vectors and supports nearest-neighbor search. When a user asks a question, the question is embedded and compared against stored document chunk embeddings. The database returns the top-k most similar chunks.

FAISS is a popular library for vector similarity search. For small datasets, an exact FAISS index such as IndexFlatIP or IndexFlatL2 is simple and reliable. For larger datasets, approximate indexes can improve speed by trading off a small amount of accuracy.

Chroma is another vector database option. It provides persistence and metadata filtering in a higher-level interface. FAISS is useful for learning because it exposes the vector search step clearly.

The top-k setting controls how many chunks are passed into the prompt. A small k can miss relevant evidence. A large k can add noise and increase generation latency.
