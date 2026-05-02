# Retrieval-Augmented Generation Overview

Retrieval-Augmented Generation, usually called RAG, is an architecture that combines information retrieval with text generation. Instead of asking a language model to answer only from its internal parameters, a RAG system first searches an external knowledge base and then provides relevant context to the model.

The main benefit of RAG is that it can reduce hallucination. The model is instructed to answer from retrieved documents, so factual claims can be grounded in source text. RAG is especially useful when the knowledge changes over time or when the answer must come from a private document collection.

A typical RAG pipeline has two stages. The indexing stage prepares documents by chunking them, embedding each chunk, and storing the vectors in a vector database. The query stage embeds the user question, retrieves similar chunks, constructs a prompt, and sends that prompt to a language model for the final answer.
