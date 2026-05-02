# LLM Memory

LLM memory refers to mechanisms that allow a language model application to retain useful information across turns or sessions. The base model itself does not permanently remember a user's information after a conversation unless the application stores that information externally and provides it again as context.

Memory can be short-term or long-term. Short-term memory usually means recent conversation history that is placed directly into the prompt. Long-term memory usually means user preferences, prior facts, summaries, or task history stored in a database and retrieved when relevant.

Memory can improve personalization because the assistant can adapt to a user's goals, constraints, and prior choices. For example, a travel assistant might remember that a user prefers morning flights and vegetarian meals. A coding assistant might remember a project's framework, naming conventions, and testing commands.

Memory also creates risks. Stored preferences may become stale, private information must be protected, and irrelevant memories can bias future answers. A good memory system should decide what to store, when to retrieve it, and how to let users inspect or delete remembered information.
