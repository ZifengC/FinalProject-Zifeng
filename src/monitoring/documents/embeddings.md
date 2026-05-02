# Embedding Models

Embedding models convert text into dense numerical vectors. Texts with similar meanings should have vectors that are close to each other in the embedding space. This makes it possible to search by semantic meaning instead of exact keyword overlap.

Sentence-transformers is a common Python library for generating text embeddings. The model all-MiniLM-L6-v2 is often used for prototypes because it is small, fast, and produces 384-dimensional vectors. Larger embedding models may improve quality but usually require more memory and time.

In a RAG system, the same embedding model should be used for both document chunks and user queries. If documents and queries are embedded with different models, similarity scores may be unreliable.
