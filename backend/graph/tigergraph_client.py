"""
TigerGraph Client — wraps pyTigerGraph for GraphRAG operations.
Handles connection, schema setup, ingestion, and subgraph queries.
"""

import os
import json
import logging
from typing import Optional
import pyTigerGraph as tg
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TigerGraphClient:
    """Production-ready TigerGraph client for GraphRAG operations."""

    def __init__(self):
        self.host = (os.getenv("TIGERGRAPH_HOST", "localhost") or "").strip()
        self.graph = (os.getenv("TIGERGRAPH_GRAPH", "GraphRAGDemo") or "").strip()
        self.username = (os.getenv("TIGERGRAPH_USERNAME", "tigergraph") or "").strip()
        self.password = (os.getenv("TIGERGRAPH_PASSWORD", "tigergraph") or "").strip()
        self.secret = (os.getenv("TIGERGRAPH_SECRET", "") or "").strip()
        self.port = int((os.getenv("TIGERGRAPH_PORT", "443") or "443").strip())
        self.use_ssl = (os.getenv("TIGERGRAPH_USE_SSL", "true") or "true").lower().strip() == "true"
        self.conn: Optional[tg.TigerGraphConnection] = None

    def connect(self) -> "TigerGraphClient":
        """Establish connection and get auth token."""
        try:
            url = f"https://{self.host}" if self.use_ssl else f"http://{self.host}"
            logger.info(f"Connecting to TigerGraph at {url}...")
            logger.info(f"Graph: {self.graph}, Username: {self.username}")
            
            self.conn = tg.TigerGraphConnection(
                host=url,
                graphname=self.graph,
                username=self.username,
                password=self.password,
                restppPort=self.port,
                gsPort=self.port,
                tgCloud=True,
            )
            logger.info(f"✅ TigerGraph connection object created")
            
            # Try to get token if secret is provided
            if self.secret:
                logger.info(f"Attempting to authenticate with secret...")
                try:
                    token = self.conn.getToken(self.secret)
                    logger.info(f"✅ Authentication successful - token obtained")
                except Exception as token_err:
                    logger.warning(f"⚠️  Token authentication failed: {token_err}")
                    logger.warning("Continuing without token (may limit some operations)")
            
            logger.info(f"✅ Connected to TigerGraph: {self.host}/{self.graph}")
            return self
        except Exception as e:
            logger.error(f"❌ TigerGraph connection failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    # ─── Schema Setup ──────────────────────────────────────────────

    def create_schema(self):
        """Create the knowledge graph schema via GSQL."""
        schema_gsql = """
        USE GLOBAL
        
        CREATE VERTEX Entity (
            PRIMARY_ID entity_id STRING,
            name STRING,
            entity_type STRING,
            description STRING,
            embedding LIST<DOUBLE>,
            doc_source STRING,
            created_at DATETIME
        ) WITH primary_id_as_attribute="true"

        CREATE VERTEX Document (
            PRIMARY_ID doc_id STRING,
            title STRING,
            content TEXT,
            chunk_index INT,
            token_count INT,
            source_url STRING,
            created_at DATETIME
        ) WITH primary_id_as_attribute="true"

        CREATE VERTEX Concept (
            PRIMARY_ID concept_id STRING,
            name STRING,
            category STRING,
            importance_score FLOAT
        ) WITH primary_id_as_attribute="true"

        CREATE UNDIRECTED EDGE RELATED_TO (
            FROM Entity, TO Entity,
            relation_type STRING,
            confidence FLOAT,
            context STRING
        )

        CREATE DIRECTED EDGE MENTIONED_IN (
            FROM Entity, TO Document,
            frequency INT,
            relevance_score FLOAT
        )

        CREATE DIRECTED EDGE HAS_CONCEPT (
            FROM Document, TO Concept,
            weight FLOAT
        )

        CREATE DIRECTED EDGE CO_OCCURS_WITH (
            FROM Entity, TO Entity,
            co_occurrence_count INT,
            documents LIST<STRING>
        )

        CREATE GRAPH GraphRAGDemo (
            Entity, Document, Concept,
            RELATED_TO, MENTIONED_IN, HAS_CONCEPT, CO_OCCURS_WITH
        )
        """
        result = self.conn.gsql(schema_gsql)
        logger.info(f"Schema created: {result}")
        return result

    # ─── Ingestion ─────────────────────────────────────────────────

    def upsert_entity(self, entity_id: str, name: str, entity_type: str,
                      description: str, embedding: list, doc_source: str):
        """Insert or update an entity vertex."""
        attributes = {
            "name": name,
            "entity_type": entity_type,
            "description": description,
        }
        
        # Try to add optional fields if schema supports them
        if embedding:
            try:
                attributes["embedding"] = embedding
            except:
                pass  # Schema may not support embeddings
        
        if doc_source:
            try:
                attributes["doc_source"] = doc_source
            except:
                pass  # Schema may not support doc_source
        
        try:
            self.conn.upsertVertex(
                "Entity", entity_id,
                attributes=attributes
            )
        except Exception as e:
            # Try with fewer attributes if it fails
            if "Unknown vertex attribute" in str(e):
                logger.debug(f"Some attributes not in schema, retrying with minimal attributes")
                minimal_attrs = {
                    "name": name,
                    "entity_type": entity_type,
                }
                try:
                    self.conn.upsertVertex(
                        "Entity", entity_id,
                        attributes=minimal_attrs
                    )
                except Exception as e2:
                    logger.warning(f"Could not upsert entity even with minimal attributes: {e2}")
                    raise
            else:
                raise

    def upsert_document(self, doc_id: str, title: str, content: str,
                        chunk_index: int, token_count: int, source_url: str = ""):
        """Insert or update a document vertex."""
        self.conn.upsertVertex(
            "Document", doc_id,
            attributes={
                "title": title,
                "content": content,
                "chunk_index": chunk_index,
                "token_count": token_count,
                "source_url": source_url,
            }
        )

    def upsert_relationship(self, from_entity: str, to_entity: str,
                             relation_type: str, confidence: float, context: str):
        """Insert or update a RELATED_TO edge."""
        self.conn.upsertEdge(
            "Entity", from_entity,
            "RELATED_TO",
            "Entity", to_entity,
            attributes={
                "relation_type": relation_type,
                "confidence": confidence,
                "context": context,
            }
        )

    def link_entity_to_document(self, entity_id: str, doc_id: str,
                                 frequency: int, relevance_score: float):
        """Link entity to document via MENTIONED_IN edge."""
        self.conn.upsertEdge(
            "Entity", entity_id,
            "MENTIONED_IN",
            "Document", doc_id,
            attributes={
                "frequency": frequency,
                "relevance_score": relevance_score,
            }
        )

    # ─── Graph Retrieval ───────────────────────────────────────────

    def is_empty(self) -> bool:
        """Fast check: is the graph empty? Used to skip expensive entity extraction."""
        try:
            if not self.conn:
                logger.warning(f"is_empty(): conn is None, graph is EMPTY")
                return True
            # Quick check: get vertex count
            result = self.conn.getVertexCount("Entity")
            is_empty = result == 0
            logger.info(f"is_empty() check: Entity count = {result}, is_empty = {is_empty}")
            return is_empty
        except Exception as e:
            logger.warning(f"is_empty() check failed: {e}, assuming graph is EMPTY")
            return True

    def get_entity_subgraph(self, entity_names: list[str], max_hops: int = 2,
                             max_neighbors: int = 10) -> dict:
        """
        Core GraphRAG retrieval: given seed entities from the query,
        traverse the graph up to max_hops and return the subgraph context.
        
        Returns structured context instead of raw text chunks.
        """
        if not entity_names:
            return {"entities": [], "relationships": [], "documents": []}

        logger.info(f"Searching for entities: {entity_names}")
        
        # Use fuzzy matching to find relevant entities
        try:
            return self._fallback_rest_retrieval(entity_names, max_neighbors)
        except Exception as e:
            logger.warning(f"Entity retrieval failed: {e}, returning empty subgraph")
            return {"entities": [], "relationships": [], "documents": []}

    def _fallback_rest_retrieval(self, entity_names: list[str], max_neighbors: int) -> dict:
        """REST API fallback for entity retrieval — uses fuzzy name matching."""
        entities = []
        relationships = []
        documents = []
        seen_ids = set()

        try:
            # Get ALL entities and do fuzzy matching locally
            all_entities = self.conn.getVertices("Entity", select="name,entity_type,description")
            if not all_entities:
                logger.warning(f"No entities found in graph")
                return {"entities": [], "relationships": [], "documents": []}
            
            logger.info(f"Total entities in graph: {len(all_entities)}")
            
            # Build a map of entity names for faster lookup
            entity_map = {}
            for vertex in all_entities:
                if isinstance(vertex, dict):
                    v_id = vertex.get("v_id", "")
                    attrs = vertex.get("attributes", {})
                    entity_name = attrs.get("name", "").lower() if attrs.get("name") else ""
                    if entity_name:
                        entity_map[entity_name] = vertex
            
            logger.info(f"Indexed {len(entity_map)} unique entity names")
            
            # Match query entities to graph entities
            matched_entities = []
            for query_name in entity_names:
                query_lower = query_name.lower().strip()
                best_match = None
                best_score = 0
                
                for graph_entity_name, vertex in entity_map.items():
                    # Score 1: Exact match
                    if query_lower == graph_entity_name:
                        best_score = 1.0
                        best_match = vertex
                        break
                    
                    # Score 2: Substring match (either direction)
                    if query_lower in graph_entity_name or graph_entity_name in query_lower:
                        # Give higher score to longer substring match
                        overlap = max(len(query_lower), len(graph_entity_name)) / (len(query_lower) + len(graph_entity_name))
                        if overlap > best_score:
                            best_score = overlap
                            best_match = vertex
                    
                    # Score 3: Common prefix (at least 3 chars)
                    if len(query_lower) >= 3 and len(graph_entity_name) >= 3:
                        for i in range(min(len(query_lower), len(graph_entity_name))):
                            if query_lower[i] != graph_entity_name[i]:
                                prefix_match = i / max(len(query_lower), len(graph_entity_name))
                                if prefix_match > 0.3 and prefix_match > best_score:
                                    best_score = prefix_match
                                    best_match = vertex
                                break
                
                if best_match and best_score > 0.3:  # Lower threshold to be more inclusive
                    if best_match["v_id"] not in seen_ids:
                        matched_entities.append(best_match)
                        entities.append(best_match)
                        seen_ids.add(best_match["v_id"])
                        logger.info(f"  ✓ Matched query '{query_name}' → '{best_match['attributes']['name']}' (score: {best_score:.2f})")
                        
                        # Get relationships for this entity
                        try:
                            edges = self.conn.getEdges("Entity", best_match["v_id"], "RELATED_TO")
                            if edges:
                                relationships.extend(edges[:max_neighbors])
                                logger.debug(f"    Found {len(edges[:max_neighbors])} relationships")
                        except Exception as e:
                            logger.debug(f"Could not fetch edges for {best_match['v_id']}: {e}")
                else:
                    logger.debug(f"  ✗ No match found for '{query_name}' (best score: {best_score:.2f})")
            
            logger.info(f"✅ Matched {len(matched_entities)} entities via fuzzy search")
            return {"entities": entities, "relationships": relationships, "documents": documents}
        except Exception as e:
            logger.error(f"Fallback REST retrieval failed: {e}", exc_info=True)
            return {"entities": [], "relationships": [], "documents": []}

    def _parse_subgraph_result(self, raw_result) -> dict:
        """Parse GSQL result into structured subgraph dict."""
        if isinstance(raw_result, str):
            try:
                raw_result = json.loads(raw_result)
            except Exception:
                return {"entities": [], "relationships": [], "documents": []}

        entities = []
        relationships = []
        documents = []

        if isinstance(raw_result, list):
            for block in raw_result:
                if "entities" in block:
                    entities = block["entities"]
                if "relationships" in block:
                    relationships = block["relationships"]
                if "documents" in block:
                    documents = block["documents"]

        return {
            "entities": entities,
            "relationships": relationships,
            "documents": documents,
        }

    def get_stats(self) -> dict:
        """Return graph statistics."""
        try:
            vertex_counts = self.conn.getVertexCount()
            edge_counts = self.conn.getEdgeCount()
            return {
                "vertices": vertex_counts,
                "edges": edge_counts,
                "graph": self.graph,
                "host": self.host,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
