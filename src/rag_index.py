import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.db_utils import get_schema


class SchemaRAG:
    """
    Hybrid schema retrieval system.

    Retrieval uses:
    1. TF-IDF similarity
    2. Business-domain keyword matching
    3. Table/column matching

    The goal is to identify the database tables
    required to answer a business question.
    """

    # ========================================================
    # BUSINESS VOCABULARY
    # ========================================================

    BUSINESS_TERMS = {

        # Product-related questions
        "product": [
            "products",
            "productname",
            "productid",
            "product",
            "item",
            "items"
        ],

        # Sales-related questions
        "sales": [
            "order details",
            "orders",
            "products",
            "unitprice",
            "quantity",
            "discount",
            "sales",
            "revenue",
            "selling",
            "sold",
            "purchase"
        ],

        # Customer-related questions
        "customer": [
            "customers",
            "customerid",
            "orders",
            "customer",
            "buyer",
            "buyers"
        ],

        # Employee-related questions
        "employee": [
            "employees",
            "employeeid",
            "orders",
            "employee",
            "staff",
            "representative"
        ],

        # Supplier-related questions
        "supplier": [
            "suppliers",
            "supplierid",
            "products",
            "supplier",
            "vendor",
            "vendors"
        ],

        # Category-related questions
        "category": [
            "categories",
            "categoryid",
            "products",
            "category",
            "categories"
        ],

        # Shipping-related questions
        "shipping": [
            "shippers",
            "shipvia",
            "shippeddate",
            "requireddate",
            "shipcountry",
            "shipcity",
            "freight",
            "shipping"
        ],

        # Country-related questions
        "country": [
            "customers",
            "suppliers",
            "orders",
            "country",
            "shipcountry"
        ],

        # Time-related questions
        "time": [
            "orders",
            "orderdate",
            "shippeddate",
            "requireddate",
            "month",
            "year",
            "date",
            "trend"
        ]
    }


    def __init__(self, top_k=5):

        self.top_k = top_k

        self.documents = []

        self.vectorizer = None

        self.matrix = None

        self._build_index()


    # ========================================================
    # NORMALIZE TEXT
    # ========================================================

    @staticmethod
    def _normalize(text):
        """
        Normalize text for matching.
        """

        text = text.lower()

        text = text.replace(
            "order details",
            "orderdetails"
        )

        text = re.sub(
            r"[^a-z0-9 ]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    # ========================================================
    # BUILD INDEX
    # ========================================================

    def _build_index(self):
        """
        Build searchable schema documents.
        """

        schema = get_schema()

        self.documents = []


        for table, columns in schema.items():

            column_names = [
                column["name"]
                for column in columns
            ]


            # Create searchable text
            document_text = (
                f"Table: {table}. "
                f"Columns: "
                f"{', '.join(column_names)}"
            )


            # Normalized representation
            searchable_text = self._normalize(
                f"{table} "
                f"{' '.join(column_names)}"
            )


            self.documents.append(
                {
                    "table": table,
                    "columns": column_names,
                    "text": document_text,
                    "searchable": searchable_text
                }
            )


        texts = [
            document["searchable"]
            for document in self.documents
        ]


        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2)
        )


        self.matrix = (
            self.vectorizer.fit_transform(texts)
        )


    # ========================================================
    # FIND BUSINESS INTENT
    # ========================================================

    def _detect_intent(self, query):
        """
        Identify business concepts in the question.
        """

        normalized_query = self._normalize(
            query
        )


        detected = []


        for intent, terms in self.BUSINESS_TERMS.items():

            for term in terms:

                normalized_term = self._normalize(
                    term
                )

                if normalized_term in normalized_query:

                    detected.append(
                        intent
                    )

                    break


        return list(
            set(detected)
        )


    # ========================================================
    # BUSINESS SCORE
    # ========================================================

    def _business_score(
        self,
        query,
        document
    ):
        """
        Calculate business-domain relevance.
        """

        intents = self._detect_intent(
            query
        )


        if not intents:

            return 0.0


        table = self._normalize(
            document["table"]
        )


        columns = [
            self._normalize(column)
            for column in document["columns"]
        ]


        document_words = (
            table.split()
            + columns
        )


        score = 0.0


        for intent in intents:

            terms = self.BUSINESS_TERMS[
                intent
            ]


            for term in terms:

                normalized_term = (
                    self._normalize(term)
                )


                # Exact table match
                if normalized_term == table:

                    score += 3.0


                # Table contains concept
                elif normalized_term in table:

                    score += 2.0


                # Column match
                elif normalized_term in document_words:

                    score += 1.5


                # Partial column match
                elif any(
                    normalized_term in column
                    or column in normalized_term
                    for column in columns
                ):

                    score += 1.0


        return score


    # ========================================================
    # SEARCH
    # ========================================================

    def search(self, query):
        """
        Retrieve the most relevant tables.
        """

        if not query or not query.strip():

            return []


        # ----------------------------------------------------
        # TF-IDF score
        # ----------------------------------------------------

        query_vector = (
            self.vectorizer.transform(
                [query]
            )
        )


        tfidf_scores = cosine_similarity(
            query_vector,
            self.matrix
        )[0]


        # ----------------------------------------------------
        # Calculate hybrid scores
        # ----------------------------------------------------

        scored_documents = []


        for index, document in enumerate(
            self.documents
        ):

            tfidf_score = float(
                tfidf_scores[index]
            )


            business_score = (
                self._business_score(
                    query,
                    document
                )
            )


            # Combine scores
            final_score = (
                tfidf_score
                + (business_score * 0.15)
            )


            scored_documents.append(
                {
                    "table":
                        document["table"],

                    "text":
                        document["text"],

                    "tfidf_score":
                        tfidf_score,

                    "business_score":
                        business_score,

                    "score":
                        final_score
                }
            )


        # ----------------------------------------------------
        # Rank
        # ----------------------------------------------------

        scored_documents.sort(
            key=lambda x: x["score"],
            reverse=True
        )


        # ----------------------------------------------------
        # Return results
        # ----------------------------------------------------

        return scored_documents[
            :self.top_k
        ]


    # ========================================================
    # GET CONTEXT
    # ========================================================

    def get_context(self, query):

        results = self.search(
            query
        )


        if not results:

            return (
                "No relevant database "
                "schema found."
            )


        # The relevance score is a retrieval diagnostic, not
        # information the SQL writer can use - it was costing
        # tokens on every call and saying nothing. Scores stay
        # available via search() for debugging.
        return "\n".join(
            result["text"]
            for result in results
        )