"""
向量数据库管理模块 - 支持Milvus和Qdrant
"""

from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import numpy as np
from abc import ABC, abstractmethod

from config.settings import settings


@dataclass
class Document:
    """文档对象"""
    id: str
    content: str
    metadata: Dict
    embedding: Optional[List[float]] = None


class VectorStore(ABC):
    """向量存储基类"""
    
    @abstractmethod
    def create_collection(self, collection_name: str, dimension: int):
        """创建集合"""
        pass
    
    @abstractmethod
    def insert(self, collection_name: str, documents: List[Document]):
        """插入文档"""
        pass
    
    @abstractmethod
    def search(self, collection_name: str, query_vector: List[float], top_k: int = 10) -> List[Document]:
        """搜索相似文档"""
        pass
    
    @abstractmethod
    def delete(self, collection_name: str, ids: List[str]):
        """删除文档"""
        pass


class MilvusStore(VectorStore):
    """Milvus向量存储实现"""
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        try:
            from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
            
            self.host = host or settings.milvus_host
            self.port = port or settings.milvus_port
            
            # 连接Milvus
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            
            self.Collection = Collection
            self.FieldSchema = FieldSchema
            self.CollectionSchema = CollectionSchema
            self.DataType = DataType
            self.utility = utility
            
        except ImportError:
            raise ImportError("请安装pymilvus: pip install pymilvus")
    
    def create_collection(self, collection_name: str, dimension: int = 768):
        """创建Milvus集合"""
        # 检查集合是否存在
        if self.utility.has_collection(collection_name):
            print(f"集合 {collection_name} 已存在")
            return
        
        # 定义schema
        fields = [
            self.FieldSchema(name="id", dtype=self.DataType.VARCHAR, is_primary=True, max_length=100),
            self.FieldSchema(name="content", dtype=self.DataType.VARCHAR, max_length=10000),
            self.FieldSchema(name="embedding", dtype=self.DataType.FLOAT_VECTOR, dim=dimension)
        ]
        
        schema = self.CollectionSchema(fields, description="Interview questions collection")
        
        # 创建集合
        collection = self.Collection(name=collection_name, schema=schema)
        
        # 创建索引
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        
        print(f"成功创建集合: {collection_name}")
    
    def insert(self, collection_name: str, documents: List[Document]):
        """插入文档到Milvus"""
        collection = self.Collection(collection_name)
        
        # 准备数据
        ids = [doc.id for doc in documents]
        contents = [doc.content for doc in documents]
        embeddings = [doc.embedding for doc in documents]
        
        # 插入数据
        collection.insert([ids, contents, embeddings])
        collection.flush()
        
        print(f"成功插入 {len(documents)} 条数据")
    
    def search(self, collection_name: str, query_vector: List[float], top_k: int = 10) -> List[Document]:
        """在Milvus中搜索"""
        collection = self.Collection(collection_name)
        collection.load()
        
        # 搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        # 执行搜索
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["id", "content"]
        )
        
        # 转换结果
        documents = []
        for hits in results:
            for hit in hits:
                doc = Document(
                    id=hit.entity.get("id"),
                    content=hit.entity.get("content"),
                    metadata={"score": hit.score},
                    embedding=None
                )
                documents.append(doc)
        
        return documents
    
    def delete(self, collection_name: str, ids: List[str]):
        """从Milvus删除文档"""
        collection = self.Collection(collection_name)
        expr = f"id in {ids}"
        collection.delete(expr)
        print(f"成功删除 {len(ids)} 条数据")


class QdrantStore(VectorStore):
    """Qdrant向量存储实现"""
    
    def __init__(self, url: Optional[str] = None):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            
            self.url = url or settings.qdrant_url
            self.client = QdrantClient(url=self.url)
            self.Distance = Distance
            self.VectorParams = VectorParams
            self.PointStruct = PointStruct
            
        except ImportError:
            raise ImportError("请安装qdrant-client: pip install qdrant-client")
    
    def create_collection(self, collection_name: str, dimension: int = 768):
        """创建Qdrant集合"""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=self.VectorParams(size=dimension, distance=self.Distance.COSINE)
        )
        print(f"成功创建集合: {collection_name}")
    
    def insert(self, collection_name: str, documents: List[Document]):
        """插入文档到Qdrant"""
        points = []
        for i, doc in enumerate(documents):
            point = self.PointStruct(
                id=doc.id,
                vector=doc.embedding,
                payload={
                    "content": doc.content,
                    "metadata": doc.metadata
                }
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        print(f"成功插入 {len(documents)} 条数据")
    
    def search(self, collection_name: str, query_vector: List[float], top_k: int = 10) -> List[Document]:
        """在Qdrant中搜索"""
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k
        )
        
        documents = []
        for result in results:
            doc = Document(
                id=str(result.id),
                content=result.payload.get("content", ""),
                metadata=result.payload.get("metadata", {}),
                embedding=None
            )
            doc.metadata["score"] = result.score
            documents.append(doc)
        
        return documents
    
    def delete(self, collection_name: str, ids: List[str]):
        """从Qdrant删除文档"""
        self.client.delete(
            collection_name=collection_name,
            points_selector={"points": ids}
        )
        print(f"成功删除 {len(ids)} 条数据")


class VectorStoreFactory:
    """向量存储工厂类"""
    
    @staticmethod
    def create_vector_store(store_type: Optional[str] = None) -> VectorStore:
        """创建向量存储实例"""
        store_type = store_type or settings.vector_db_type
        
        if store_type.lower() == "milvus":
            return MilvusStore()
        elif store_type.lower() == "qdrant":
            return QdrantStore()
        else:
            raise ValueError(f"不支持的向量数据库类型: {store_type}")


# 移除全局实例创建，改为按需创建
# vector_store = VectorStoreFactory.create_vector_store() 