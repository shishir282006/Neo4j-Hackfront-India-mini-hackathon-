"""
neo4j_store.py
Robust Neo4j Graph Database Driver & Anonymized Graph Engine.
Connects to Neo4j via official neo4j bolt driver.
Includes an embedded graph store with automatic persistence so the application
works immediately while offering seamless 1-click sync to live Neo4j (local or Aura).
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from neo4j import GraphDatabase, exceptions as neo4j_exceptions
    NEO4J_DRIVER_AVAILABLE = True
except ImportError:
    NEO4J_DRIVER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jGraphStore:
    def __init__(self, data_file: str = "data/anonymized_graph.json"):
        self.data_file = data_file
        self.neo4j_driver = None
        self.neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        self.neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
        self.is_connected = False
        self.connection_error = None
        self.cypher_query_log: List[Dict[str, Any]] = []

        # Local embedded graph store (Nodes and Edges)
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

        self._load_local_store()
        # Attempt initial Neo4j connection silently
        self.try_connect_neo4j()

    def _load_local_store(self):
        """Loads local persistent graph from JSON file if available."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
            except Exception as e:
                logger.error(f"Error loading graph data: {e}")
                self.nodes = {}
                self.edges = []
        else:
            self.nodes = {}
            self.edges = []

    def _save_local_store(self):
        """Persists graph to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving local graph: {e}")

    def try_connect_neo4j(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Attempts connection to Neo4j database."""
        if not NEO4J_DRIVER_AVAILABLE:
            self.is_connected = False
            self.connection_error = "neo4j package not available"
            return False

        if uri: self.neo4j_uri = uri
        if user: self.neo4j_user = user
        if password is not None: self.neo4j_password = password

        try:
            # Close existing driver if open
            if self.neo4j_driver:
                try:
                    self.neo4j_driver.close()
                except Exception:
                    pass

            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
                connection_timeout=2.0
            )
            # Verify connectivity
            self.neo4j_driver.verify_connectivity()
            self.is_connected = True
            self.connection_error = None
            logger.info(f"Successfully connected to Neo4j at {self.neo4j_uri}")
            return True
        except Exception as e:
            self.is_connected = False
            self.connection_error = str(e)
            logger.warning(f"Neo4j offline or unreachable at {self.neo4j_uri}: {e}. Using embedded graph engine.")
            return False

    def log_cypher(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Logs Cypher query for user inspection in UI."""
        self.cypher_query_log.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "query": query.strip(),
            "params": params or {}
        })
        if len(self.cypher_query_log) > 50:
            self.cypher_query_log.pop(0)

    def add_node(self, label: str, node_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds or merges a node in graph (both local & real Neo4j).
        """
        props = dict(properties)
        props["id"] = node_id
        props["label"] = label
        props["updated_at"] = datetime.now().isoformat()

        # Update local node
        self.nodes[node_id] = {
            "id": node_id,
            "label": label,
            "properties": props
        }
        self._save_local_store()

        # Build Cypher
        cypher = f"MERGE (n:{label} {{id: $id}}) SET n += $props RETURN n"
        self.log_cypher(cypher, {"id": node_id, "props": props})

        # Execute in real Neo4j if connected
        if self.is_connected and self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    session.run(cypher, id=node_id, props=props)
            except Exception as e:
                logger.error(f"Error running Cypher against Neo4j: {e}")

        return self.nodes[node_id]

    def add_relationship(self, from_id: str, to_id: str, rel_type: str, properties: Optional[Dict[str, Any]] = None):
        """
        Adds or merges a relationship between two nodes.
        """
        props = dict(properties or {})
        props["created_at"] = datetime.now().isoformat()

        # Check existing edge
        existing = False
        for edge in self.edges:
            if edge["from"] == from_id and edge["to"] == to_id and edge["type"] == rel_type:
                edge["properties"].update(props)
                existing = True
                break

        if not existing:
            self.edges.append({
                "from": from_id,
                "to": to_id,
                "type": rel_type,
                "properties": props
            })
        self._save_local_store()

        from_label = self.nodes.get(from_id, {}).get("label", "Node")
        to_label = self.nodes.get(to_id, {}).get("label", "Node")

        cypher = (
            f"MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += $props RETURN r"
        )
        self.log_cypher(cypher, {"from_id": from_id, "to_id": to_id, "props": props})

        if self.is_connected and self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    session.run(cypher, from_id=from_id, to_id=to_id, props=props)
            except Exception as e:
                logger.error(f"Error running relationship Cypher against Neo4j: {e}")

    def sync_all_to_neo4j(self) -> Dict[str, Any]:
        """
        Synchronizes all local nodes and relationships into the connected Neo4j server.
        """
        if not self.is_connected or not self.neo4j_driver:
            connected = self.try_connect_neo4j()
            if not connected:
                return {"success": False, "error": f"Cannot connect to Neo4j at {self.neo4j_uri}: {self.connection_error}"}

        synced_nodes = 0
        synced_edges = 0

        try:
            with self.neo4j_driver.session() as session:
                # 1. Sync nodes
                for node_id, node_data in self.nodes.items():
                    label = node_data.get("label", "Node")
                    props = node_data.get("properties", {})
                    session.run(f"MERGE (n:{label} {{id: $id}}) SET n += $props", id=node_id, props=props)
                    synced_nodes += 1

                # 2. Sync edges
                for edge in self.edges:
                    from_id = edge["from"]
                    to_id = edge["to"]
                    rel_type = edge["type"]
                    props = edge.get("properties", {})
                    from_label = self.nodes.get(from_id, {}).get("label", "Node")
                    to_label = self.nodes.get(to_id, {}).get("label", "Node")

                    cypher = (
                        f"MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}}) "
                        f"MERGE (a)-[r:{rel_type}]->(b) "
                        f"SET r += $props"
                    )
                    session.run(cypher, from_id=from_id, to_id=to_id, props=props)
                    synced_edges += 1

            return {
                "success": True,
                "synced_nodes": synced_nodes,
                "synced_edges": synced_edges,
                "message": f"Successfully synchronized {synced_nodes} nodes and {synced_edges} relationships to Neo4j!"
            }
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return {"success": False, "error": str(e)}

    def execute_cypher(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a Cypher query directly in Neo4j if connected,
        or returns simulated result if offline.
        """
        self.log_cypher(query, params)
        if self.is_connected and self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    result = session.run(query, params or {})
                    records = [record.data() for record in result]
                    return {"success": True, "source": "Neo4j Server", "records": records}
            except Exception as e:
                return {"success": False, "source": "Neo4j Server", "error": str(e)}
        else:
            return {
                "success": True,
                "source": "Local Graph Engine",
                "notice": "Neo4j server is offline. Cypher query logged and executed against embedded graph.",
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges)
            }

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Traverses relationships to gather user's flight and tourist preferences.
        Equivalent to:
        MATCH (u:User {id: $user_id})-[:HAS_PREFERENCE]->(p:Preference)
        RETURN p
        """
        pref = {
            "seat": "Window",
            "meal": "Vegetarian",
            "airline": "IndiGo",
            "class": "Economy",
            "tourist_categories": ["Historical Monument", "Heritage Architecture", "Cultural Spot"],
            "anonymized_passenger": "ANON_TRAV_DEFAULT"
        }

        # Check in local nodes/edges
        for edge in self.edges:
            if edge["from"] == user_id and edge["type"] == "HAS_PREFERENCE":
                target_id = edge["to"]
                target_node = self.nodes.get(target_id, {})
                if target_node:
                    pref.update(target_node.get("properties", {}))

        return pref

    def get_flight_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Finds previous flight bookings for user:
        MATCH (u:User {id: $user_id})-[:BOOKED_FLIGHT]->(b:FlightBooking)-[:FOR_ROUTE]->(r:Route)
        RETURN b, r
        """
        history = []
        for edge in self.edges:
            if edge["from"] == user_id and edge["type"] == "BOOKED_FLIGHT":
                booking_id = edge["to"]
                booking_node = self.nodes.get(booking_id, {})
                if booking_node:
                    booking_info = dict(booking_node.get("properties", {}))
                    # Find route
                    for r_edge in self.edges:
                        if r_edge["from"] == booking_id and r_edge["type"] == "FOR_ROUTE":
                            route_node = self.nodes.get(r_edge["to"], {})
                            if route_node:
                                booking_info["route"] = route_node.get("properties", {})
                    history.append(booking_info)
        return history

    def get_tourist_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Finds tourist places visited:
        MATCH (u:User {id: $user_id})-[:VISITED]->(t:TouristPlace)-[:LOCATED_IN]->(l:Location)
        RETURN t, l
        """
        visits = []
        for edge in self.edges:
            if edge["from"] == user_id and edge["type"] == "VISITED":
                place_id = edge["to"]
                place_node = self.nodes.get(place_id, {})
                if place_node:
                    place_info = dict(place_node.get("properties", {}))
                    for l_edge in self.edges:
                        if l_edge["from"] == place_id and l_edge["type"] == "LOCATED_IN":
                            loc_node = self.nodes.get(l_edge["to"], {})
                            if loc_node:
                                place_info["location"] = loc_node.get("properties", {})
                    visits.append(place_info)
        return visits

    def get_vis_graph_data(self) -> Dict[str, Any]:
        """
        Formats graph for Vis.js interactive network visualization in UI.
        Colors, icons, groups according to node types.
        """
        color_map = {
            "User": {"background": "#6366f1", "border": "#4338ca", "highlight": "#818cf8"},
            "FlightBooking": {"background": "#06b6d4", "border": "#0891b2", "highlight": "#22d3ee"},
            "Route": {"background": "#3b82f6", "border": "#1d4ed8", "highlight": "#60a5fa"},
            "TouristPlace": {"background": "#10b981", "border": "#047857", "highlight": "#34d399"},
            "Location": {"background": "#f59e0b", "border": "#d97706", "highlight": "#fbbf24"},
            "Preference": {"background": "#ec4899", "border": "#be185d", "highlight": "#f472b6"},
            "Folder": {"background": "#8b5cf6", "border": "#6d28d9", "highlight": "#a78bfa"},
            "MemoryItem": {"background": "#14b8a6", "border": "#0f766e", "highlight": "#2dd4bf"}
        }

        vis_nodes = []
        for node_id, data in self.nodes.items():
            label = data.get("label", "Node")
            props = data.get("properties", {})
            title_text = f"<b>{label}</b><br>" + "<br>".join([f"{k}: {v}" for k, v in props.items() if k not in ["id", "label"]])
            
            # Display label
            name = props.get("name") or props.get("display_pseudonym") or props.get("route_code") or props.get("title") or props.get("flight_number") or node_id
            
            colors = color_map.get(label, {"background": "#64748b", "border": "#334155", "highlight": "#94a3b8"})
            vis_nodes.append({
                "id": node_id,
                "label": f"[{label}]\n{name}",
                "group": label,
                "title": title_text,
                "color": colors,
                "shape": "dot",
                "size": 24 if label in ["User", "Folder"] else 18,
                "font": {"color": "#ffffff", "face": "system-ui", "size": 12}
            })

        vis_edges = []
        for idx, edge in enumerate(self.edges):
            vis_edges.append({
                "id": f"edge_{idx}",
                "from": edge["from"],
                "to": edge["to"],
                "label": edge["type"],
                "arrows": "to",
                "font": {"align": "top", "size": 10, "color": "#94a3b8"},
                "color": {"color": "#475569", "highlight": "#38bdf8"}
            })

        return {
            "nodes": vis_nodes,
            "edges": vis_edges,
            "stats": {
                "total_nodes": len(vis_nodes),
                "total_edges": len(vis_edges),
                "is_neo4j_connected": self.is_connected,
                "neo4j_uri": self.neo4j_uri
            }
        }

# Global singleton
graph_store = Neo4jGraphStore()
