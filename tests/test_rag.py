import pytest
from src.rag.chunker import DocumentChunker, Chunk


class TestDocumentChunker:
    def test_chunk_simple_text(self):
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
        text = "This is a simple test document. " * 20
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert len(chunk.text) <= 100 + 50

    def test_chunk_code_text(self):
        chunker = DocumentChunker(chunk_size=200, chunk_overlap=0)
        code = "def foo():\n    pass\n" * 50
        chunks = chunker.chunk_text(code, metadata={"language": "python"})
        assert len(chunks) > 0

    def test_chunk_empty_text(self):
        chunker = DocumentChunker()
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0

    def test_chunk_with_metadata(self):
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=0)
        text = "Hello world. " * 20
        chunks = chunker.chunk_text(text, metadata={"url": "http://example.com"})
        for chunk in chunks:
            assert "url" in chunk.metadata
            assert "chunk_index" in chunk.metadata


class TestVectorStore:
    def test_add_and_count(self):
        from src.rag.vector_store import VectorStore
        from src.rag.embedding import EmbeddingGenerator

        vs = VectorStore(persist_dir="./chroma_data_test", collection_name="test_collection")
        try:
            emb = EmbeddingGenerator()
            texts = ["SELECT * FROM users", "SELECT name FROM users WHERE id = 1"]
            embeddings = emb.embed(texts)
            vs.add_documents(
                ids=["doc1", "doc2"],
                documents=texts,
                embeddings=embeddings,
                metadatas=[{"lang": "sql"}, {"lang": "sql"}],
            )
            assert vs.count() == 2
        finally:
            vs.delete_collection()

    def test_query(self):
        from src.rag.vector_store import VectorStore
        from src.rag.embedding import EmbeddingGenerator

        vs = VectorStore(persist_dir="./chroma_data_test", collection_name="test_query")
        try:
            emb = EmbeddingGenerator()
            texts = [
                "How to write a SELECT query in SQL",
                "Python list comprehension examples",
                "SQL JOIN examples with multiple tables",
            ]
            embeddings = emb.embed(texts)
            vs.add_documents(
                ids=["d1", "d2", "d3"],
                documents=texts,
                embeddings=embeddings,
            )
            query_emb = emb.embed_single("SQL SELECT query")
            result = vs.query(query_emb, top_k=2)
            assert "ids" in result
            assert len(result["ids"][0]) == 2
        finally:
            vs.delete_collection()


class TestEmbeddingGenerator:
    def test_embed_single(self):
        from src.rag.embedding import EmbeddingGenerator
        emb = EmbeddingGenerator()
        vec = emb.embed_single("Hello world")
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(v, float) for v in vec)

    def test_embed_batch(self):
        from src.rag.embedding import EmbeddingGenerator
        emb = EmbeddingGenerator()
        texts = ["First text", "Second text", "Third text"]
        vecs = emb.embed(texts)
        assert len(vecs) == 3
        assert len(vecs[0]) == emb.dimension

    def test_dimension(self):
        from src.rag.embedding import EmbeddingGenerator
        emb = EmbeddingGenerator()
        assert emb.dimension > 0


class TestRetriever:
    def test_index_and_retrieve(self):
        from src.rag.retriever import Retriever
        from src.rag.vector_store import VectorStore

        vs = VectorStore(persist_dir="./chroma_data_test", collection_name="test_retriever")
        try:
            retriever = Retriever(vector_store=vs)
            docs = [
                {"content": "SELECT queries are used to retrieve data from databases", "url": "http://sql.com/select"},
                {"content": "INSERT queries add new records to tables", "url": "http://sql.com/insert"},
                {"content": "Python is a programming language for general purpose", "url": "http://python.org"},
            ]
            count = retriever.index_documents(docs)
            assert count > 0

            results = retriever.retrieve("How to query data from a database", top_k=2)
            assert len(results) <= 2
            assert len(results) > 0
        finally:
            vs.delete_collection()
