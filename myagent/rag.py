"""
RAG 检索模块
- 向量数据库连接（默认 FAISS，可切换 Chroma）
- 文档加载、切分
- 检索器封装
"""

from typing import Optional


class RAGRetriever:
    def __init__(self, collection_name: str = "default", persist_dir: str = "./rag_data"):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self._index = None

    def load_documents(self, file_path: str) -> list:
        """加载文档，返回切分后的 chunks"""
        raise NotImplementedError("请实现文档加载逻辑，可使用 LangChain 的 TextLoader / PyPDFLoader 等")

    def build_index(self, documents: list):
        """从文档构建向量索引"""
        raise NotImplementedError("请实现向量索引构建，可使用 FAISS.from_documents 或 Chroma")

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """检索与 query 最相关的 top_k 条内容"""
        if self._index is None:
            return []
        raise NotImplementedError("请实现检索逻辑")

    def add_documents(self, file_path: str):
        """增量添加文档到已有索引"""
        raise NotImplementedError("请实现增量添加逻辑")
