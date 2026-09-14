from src.rag_index import SchemaRAG


rag = SchemaRAG(
    top_k=5
)


question = (
    "What are the top selling products?"
)


print("=" * 70)
print("RAG CONTEXT")
print("=" * 70)


context = rag.get_context(
    question
)


print(context)


print("\n")
print("✅ RAG CONTEXT TEST PASSED")