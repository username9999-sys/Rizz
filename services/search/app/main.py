"""
Search Service - Enterprise Search Platform
Built on Elasticsearch with advanced search capabilities
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

# Elasticsearch client
es_client = AsyncElasticsearch(
    hosts=[os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch:9200')],
    retry_on_timeout=True,
    max_retries=3
)

app = FastAPI(
    title="Rizz Search Service",
    description="Enterprise Search Platform with Elasticsearch",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Models =====

class SearchQuery(BaseModel):
    query: str
    index: str = 'posts'
    filters: Optional[Dict[str, Any]] = None
    sort: Optional[str] = '_score'
    size: int = 20
    from_: int = 0


class SearchResult(BaseModel):
    total: int
    hits: List[Dict[str, Any]]
    aggregations: Optional[Dict[str, Any]] = None
    took_ms: int


class SuggestionResult(BaseModel):
    suggestions: List[str]
    original: str


# ===== Index Management =====

@app.on_event("startup")
async def startup_event():
    """Initialize Elasticsearch indices"""
    try:
        # Create posts index with mappings
        await es_client.indices.create(
            index='posts',
            body={
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"},
                                "autocomplete": {
                                    "type": "text",
                                    "analyzer": "autocomplete"
                                }
                            }
                        },
                        "content": {"type": "text", "analyzer": "standard"},
                        "excerpt": {"type": "text"},
                        "author": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "view_count": {"type": "integer"},
                        "like_count": {"type": "integer"},
                        "comment_count": {"type": "integer"},
                        "created_at": {"type": "date"},
                        "published_at": {"type": "date"},
                        "user_id": {"type": "integer"}
                    }
                },
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1,
                    "analysis": {
                        "analyzer": {
                            "autocomplete": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "autocomplete_filter"]
                            }
                        },
                        "filter": {
                            "autocomplete_filter": {
                                "type": "edge_ngram",
                                "min_gram": 2,
                                "max_gram": 20
                            }
                        }
                    }
                }
            },
            ignore=400  # Ignore if index already exists
        )
        
        # Create users index
        await es_client.indices.create(
            index='users',
            body={
                "mappings": {
                    "properties": {
                        "username": {"type": "keyword"},
                        "email": {"type": "keyword"},
                        "is_active": {"type": "boolean"},
                        "is_verified": {"type": "boolean"},
                        "created_at": {"type": "date"},
                        "last_login_at": {"type": "date"}
                    }
                }
            },
            ignore=400
        )
        
        print("Elasticsearch indices initialized")
    except Exception as e:
        print(f"Elasticsearch connection error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close Elasticsearch connection"""
    await es_client.close()


# ===== API Endpoints =====

@app.get('/health')
async def health_check():
    """Health check with Elasticsearch connectivity"""
    try:
        info = await es_client.info()
        return {
            'status': 'healthy',
            'service': 'search',
            'elasticsearch': 'connected',
            'version': info['version']['number'],
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            'status': 'degraded',
            'service': 'search',
            'elasticsearch': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@app.post('/api/search', response_model=SearchResult)
async def search(search_query: SearchQuery):
    """Full-text search with filters and aggregations"""
    try:
        # Build query
        query_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": search_query.query,
                                "fields": ["title^3", "content^2", "excerpt"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "from": search_query.from_,
            "size": search_query.size,
            "_source": ["title", "content", "excerpt", "author", "tags", "created_at", "view_count"]
        }
        
        # Add filters
        if search_query.filters:
            for key, value in search_query.filters.items():
                query_body["query"]["bool"]["filter"] = [{"term": {key: value}}]
        
        # Add sorting
        if search_query.sort != '_score':
            query_body["sort"] = [{search_query.sort: {"order": "desc"}}]
        
        # Add aggregations
        query_body["aggs"] = {
            "tags": {"terms": {"field": "tags", "size": 10}},
            "authors": {"terms": {"field": "author", "size": 10}},
            "status": {"terms": {"field": "status"}},
            "avg_views": {"avg": {"field": "view_count"}}
        }
        
        # Execute search
        response = await es_client.search(
            index=search_query.index,
            body=query_body
        )
        
        return SearchResult(
            total=response['hits']['total']['value'],
            hits=[hit['_source'] for hit in response['hits']['hits']],
            aggregations=response.get('aggregations'),
            took_ms=response['took']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/search/autocomplete')
async def autocomplete(
    q: str = Query(..., min_length=2, max_length=50),
    index: str = 'posts',
    limit: int = 10
):
    """Autocomplete suggestions"""
    try:
        response = await es_client.search(
            index=index,
            body={
                "suggest": {
                    "title-suggest": {
                        "prefix": q,
                        "completion": {
                            "field": "title.autocomplete",
                            "size": limit,
                            "skip_duplicates": True
                        }
                    }
                }
            }
        )
        
        suggestions = [
            option['text']
            for suggestion in response['suggest']['title-suggest']
            for option in suggestion['options']
        ]
        
        return SuggestionResult(suggestions=suggestions, original=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/search/facets')
async def faceted_search(
    q: Optional[str] = None,
    index: str = 'posts'
):
    """Faceted search for filters"""
    try:
        query_body = {
            "size": 0,
            "aggs": {
                "tags": {"terms": {"field": "tags", "size": 20}},
                "authors": {"terms": {"field": "author", "size": 20}},
                "status": {"terms": {"field": "status"}},
                "created_at_histogram": {
                    "date_histogram": {
                        "field": "created_at",
                        "calendar_interval": "month"
                    }
                },
                "avg_views": {"avg": {"field": "view_count"}},
                "max_likes": {"max": {"field": "like_count"}}
            }
        }
        
        if q:
            query_body["query"] = {
                "multi_match": {
                    "query": q,
                    "fields": ["title", "content", "tags"]
                }
            }
        else:
            query_body["query"] = {"match_all": {}}
        
        response = await es_client.search(index=index, body=query_body)
        
        return {
            'facets': {
                'tags': response['aggregations']['tags']['buckets'],
                'authors': response['aggregations']['authors']['buckets'],
                'status': response['aggregations']['status']['buckets'],
                'timeline': response['aggregations']['created_at_histogram']['buckets'],
                'avg_views': response['aggregations']['avg_views']['value'],
                'max_likes': response['aggregations']['max_likes']['value']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/search/index/{index_name}')
async def index_document(index_name: str, document: Dict[str, Any], id: Optional[str] = None):
    """Index a document"""
    try:
        response = await es_client.index(
            index=index_name,
            id=id,
            body=document
        )
        
        return {
            'status': 'indexed',
            'index': index_name,
            'id': response['_id'],
            'result': response['result']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete('/api/search/index/{index_name}/{doc_id}')
async def delete_document(index_name: str, doc_id: str):
    """Delete a document"""
    try:
        response = await es_client.delete(index=index_name, id=doc_id)
        
        return {
            'status': 'deleted',
            'index': index_name,
            'id': doc_id
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail='Document not found')


@app.put('/api/search/index/{index_name}/{doc_id}')
async def update_document(index_name: str, doc_id: str, document: Dict[str, Any]):
    """Update a document"""
    try:
        response = await es_client.update(
            index=index_name,
            id=doc_id,
            body={"doc": document}
        )
        
        return {
            'status': 'updated',
            'index': index_name,
            'id': doc_id,
            'result': response['result']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/search/analytics')
async def search_analytics():
    """Search analytics and statistics"""
    try:
        # Get index stats
        stats = await es_client.indices.stats(index='posts')
        
        # Get document count
        count = await es_client.count(index='posts')
        
        return {
            'analytics': {
                'total_documents': count['count'],
                'index_size_bytes': stats['indices']['posts']['total']['store']['size_in_bytes'],
                'shards': {
                    'total': stats['indices']['posts']['shards']['total'],
                    'primaries': len(stats['indices']['posts']['shards'])
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8003)
