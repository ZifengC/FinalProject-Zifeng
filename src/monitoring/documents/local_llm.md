# Local LLM with Ollama and Qwen

Ollama is a local model runtime that can download and serve open-source language models. It provides a local HTTP API, usually at http://localhost:11434. A Python RAG program can send prompts to Ollama and receive generated answers.

Qwen2.5-7B-Instruct is an instruction-tuned open-source language model. In this project, Qwen is the model used for answer generation, and Ollama is the tool used to run the model locally. The Ollama model name is commonly qwen2.5:7b.

Using a local model satisfies the self-hosted requirement because the prompt and documents are processed on the user's machine. The trade-off is that generation can be slower than hosted APIs, especially on machines with limited memory or no GPU acceleration.
