from src.rag_index import SchemaRAG


print("=" * 70)
print("HYBRID SCHEMA RAG TEST")
print("=" * 70)


rag = SchemaRAG(
    top_k=5
)


questions = [

    "What are the top selling products?",

    "Which customers placed the most orders?",

    "Which employees handled the most orders?",

    "What are the total sales by category?",

    "Which country has the highest number of customers?",

    "What is the monthly order trend?"

]


for question in questions:

    print("\n")
    print("=" * 70)

    print(
        "QUESTION:",
        question
    )

    print("=" * 70)


    results = rag.search(
        question
    )


    print("\nRELEVANT TABLES:")


    for result in results:

        print(
            f"- {result['table']}"
        )

        print(
            f"  Final score: "
            f"{result['score']:.3f}"
        )

        print(
            f"  TF-IDF: "
            f"{result['tfidf_score']:.3f}"
        )

        print(
            f"  Business: "
            f"{result['business_score']:.3f}"
        )


print("\n")
print("=" * 70)
print("✅ HYBRID RAG TEST COMPLETED")
print("=" * 70)