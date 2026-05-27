# -*- coding: utf-8 -*-
"""
向量知识库模块
使用ChromaDB存储和检索新闻知识

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
"""

import os
import json
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

import requests


class KnowledgeVectorDB:
    """向量知识库"""

    def __init__(self, persist_directory=None, api_key=None, api_base=None, model=None):
        self.persist_directory = persist_directory or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'vectordb'
        )
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.api_base = api_base or os.environ.get('OPENAI_API_BASE', 'https://api.xiaomimimo.com/v1')
        self.model = model or os.environ.get('OPENAI_MODEL', 'mimo-v2-flash')

        if not self.api_base.endswith('/v1'):
            self.api_base = self.api_base.rstrip('/') + '/v1'

        self.client = None
        self.collection = None

        if CHROMADB_AVAILABLE:
            self._init_chromadb()
        else:
            print("警告: ChromaDB未安装，向量搜索功能不可用")

    def _init_chromadb(self):
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="news_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

    def add_news(self, news_items):
        if not CHROMADB_AVAILABLE or not self.collection:
            return 0

        added_count = 0
        for item in news_items:
            title = item.get('title', '')
            if not title:
                continue

            doc_id = f"news_{hash(title)}_{datetime.now().strftime('%Y%m%d')}"

            try:
                existing = self.collection.get(ids=[doc_id])
                if existing and existing['ids']:
                    continue
            except:
                pass

            metadata = {
                'source': item.get('source', 'unknown'),
                'date': item.get('date', datetime.now().strftime('%Y-%m-%d')),
                'sentiment': item.get('sentiment', 'neutral'),
                'is_finance': item.get('is_finance', False),
                'timestamp': datetime.now().isoformat()
            }

            self.collection.add(
                documents=[title],
                metadatas=[metadata],
                ids=[doc_id]
            )
            added_count += 1

        return added_count

    def search(self, query, n_results=10, filter_metadata=None):
        if not CHROMADB_AVAILABLE or not self.collection:
            return []

        try:
            where = filter_metadata if filter_metadata else None
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

            items = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    items.append({
                        'title': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })

            return items
        except Exception as e:
            print(f"搜索失败: {e}")
            return []

    def search_by_sentiment(self, sentiment, n_results=10):
        return self.search(
            query="",
            n_results=n_results,
            filter_metadata={"sentiment": sentiment}
        )

    def search_finance_news(self, query, n_results=10):
        return self.search(
            query=query,
            n_results=n_results,
            filter_metadata={"is_finance": True}
        )

    def get_stats(self):
        if not CHROMADB_AVAILABLE or not self.collection:
            return {
                'available': False,
                'total_count': 0
            }

        try:
            count = self.collection.count()
            return {
                'available': True,
                'total_count': count,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }

    def import_from_sqlite(self, db_path):
        if not CHROMADB_AVAILABLE:
            return 0

        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT title, source, date, sentiment, is_finance
                FROM news
                ORDER BY date DESC
                LIMIT 1000
            ''')

            news_items = []
            for row in cursor.fetchall():
                news_items.append({
                    'title': row[0],
                    'source': row[1],
                    'date': row[2],
                    'sentiment': row[3] or 'neutral',
                    'is_finance': bool(row[4])
                })

            return self.add_news(news_items)
        except Exception as e:
            print(f"导入失败: {e}")
            return 0
        finally:
            conn.close()


if __name__ == '__main__':
    db = KnowledgeVectorDB()
    stats = db.get_stats()
    print(f"知识库状态: {json.dumps(stats, ensure_ascii=False, indent=2)}")

    if stats.get('available'):
        test_news = [
            {
                'title': '央行宣布降准0.5个百分点，释放长期资金约1万亿元',
                'source': '财联社',
                'date': '2026-05-27',
                'sentiment': 'positive',
                'is_finance': True
            },
            {
                'title': 'A股三大指数集体高开，半导体板块领涨',
                'source': '东方财富',
                'date': '2026-05-27',
                'sentiment': 'positive',
                'is_finance': True
            }
        ]

        added = db.add_news(test_news)
        print(f"添加了 {added} 条新闻")

        results = db.search("央行降准")
        print(f"搜索结果: {json.dumps(results, ensure_ascii=False, indent=2)}")
