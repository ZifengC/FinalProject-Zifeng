# Grounded Answer Generation

Grounding means constraining a language model answer to the retrieved context. A grounded RAG prompt should include the user question, the retrieved context, and clear instructions that the model must only use the provided context.

Source attribution is important because it allows users to verify claims. A prompt can label each retrieved chunk with a source name and chunk number. The model can then cite the source when answering.

If the retrieved context does not contain enough information, the model should say that the context is insufficient. This behavior is better than inventing an answer. In evaluation, unsupported claims are counted as hallucinations even if they sound plausible.
