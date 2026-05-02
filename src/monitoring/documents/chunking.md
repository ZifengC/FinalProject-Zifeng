# Document Chunking

Document chunking is the process of splitting long documents into smaller passages. Chunking matters because embedding models and language models have context limits, and retrieval works better when each indexed item has a focused topic.

Common chunking strategies include fixed-size chunking, paragraph-based chunking, sentence-boundary chunking, and recursive chunking. Fixed-size chunking is simple but may break ideas in the middle. Paragraph and sentence-aware chunking usually preserves meaning better.

Chunk size is a design decision. Small chunks can improve precision because each result is focused, but they may lose surrounding context. Large chunks preserve more context but can reduce retrieval precision. Overlap helps by copying some words from one chunk into the next so that important information near a boundary is not lost.

For a small class project, a chunk size around 256 to 512 tokens with 40 to 80 tokens of overlap is a reasonable starting point.
