"""
app.py
Main Flask Application for the Neo4j Anonymized Memory Agent.
Provides web UI and REST API for:
- Folder-based Chatbot (Flight Booking, Tourist Places, General Memory)
- Neo4j Knowledge Graph Visualizer & Cypher Console
- Privacy & Anonymization Engine
"""

import os
from flask import Flask, render_template, request, jsonify, send_file
from neo4j_store import graph_store
from anonymizer import anonymizer_instance
from memory_service import memory_service
from seed_data import seed_graph_database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neo4j_memory_agent_secret_2026'

# Ensure graph is seeded on startup
seed_graph_database(force_reset=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download')
def download_zip():
    zip_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'neo4j-memory-agent-app.zip'))
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name='neo4j-memory-agent-app.zip')
    return jsonify({"success": False, "error": "Zip file not found"}), 404

@app.route('/api/folders', methods=['GET'])
def get_folders():
    folders = [
        {
            "id": "folder_flights",
            "name": "Flight Booking",
            "icon": "plane",
            "description": "Memorizes booking habits. Only asks where-to-where & date, then auto-books!",
            "badge": "Memory Active"
        },
        {
            "id": "folder_tourist",
            "name": "Tourist Places",
            "icon": "map-pin",
            "description": "Memorizes exploration affinity. Takes current location and recommends sights!",
            "badge": "Memory Active"
        },
        {
            "id": "folder_general",
            "name": "All Chats & Memories",
            "icon": "brain",
            "description": "Open conversation with full access to anonymized graph memory.",
            "badge": "Graph Connected"
        }
    ]
    return jsonify({"success": True, "folders": folders})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    folder_id = data.get("folder_id", "folder_general")

    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400

    if folder_id == "folder_flights":
        res = memory_service.handle_flight_booking(message)
    elif folder_id == "folder_tourist":
        res = memory_service.handle_tourist_recommendation(message)
    else:
        res = memory_service.handle_general_chat(message)

    # Attach current graph stats
    res["success"] = True
    res["graph_stats"] = {
        "total_nodes": len(graph_store.nodes),
        "total_edges": len(graph_store.edges),
        "neo4j_connected": graph_store.is_connected
    }

    return jsonify(res)

@app.route('/api/graph', methods=['GET'])
def get_graph():
    graph_data = graph_store.get_vis_graph_data()
    return jsonify({"success": True, "data": graph_data})

@app.route('/api/memories', methods=['GET'])
def get_memories():
    user_id = memory_service.user_id
    habits = graph_store.get_user_preferences(user_id)
    flight_history = graph_store.get_flight_history(user_id)
    tourist_history = graph_store.get_tourist_history(user_id)
    user_node = graph_store.nodes.get(user_id, {}).get("properties", {})

    return jsonify({
        "success": True,
        "user_profile": user_node,
        "habits": habits,
        "flight_history": flight_history,
        "tourist_history": tourist_history,
        "neo4j_connected": graph_store.is_connected,
        "neo4j_uri": graph_store.neo4j_uri
    })

@app.route('/api/mark-visited', methods=['POST'])
def mark_visited():
    data = request.get_json() or {}
    place_id = data.get("place_id")
    if not place_id:
        return jsonify({"success": False, "error": "place_id is required"}), 400

    result = memory_service.mark_place_visited(place_id)
    return jsonify(result)

@app.route('/api/neo4j/status', methods=['GET'])
def neo4j_status():
    return jsonify({
        "success": True,
        "is_connected": graph_store.is_connected,
        "uri": graph_store.neo4j_uri,
        "user": graph_store.neo4j_user,
        "error": graph_store.connection_error,
        "total_nodes": len(graph_store.nodes),
        "total_edges": len(graph_store.edges)
    })

@app.route('/api/neo4j/connect', methods=['POST'])
def neo4j_connect():
    data = request.get_json() or {}
    uri = data.get("uri", "bolt://localhost:7687").strip()
    user = data.get("user", "neo4j").strip()
    password = data.get("password", "password").strip()

    connected = graph_store.try_connect_neo4j(uri=uri, user=user, password=password)
    if connected:
        sync_result = graph_store.sync_all_to_neo4j()
        return jsonify({
            "success": True,
            "message": f"Successfully connected to Neo4j! {sync_result.get('message', '')}",
            "sync": sync_result
        })
    else:
        return jsonify({
            "success": False,
            "error": f"Failed to connect to Neo4j at {uri}: {graph_store.connection_error}"
        }), 400

@app.route('/api/neo4j/cypher-log', methods=['GET'])
def get_cypher_log():
    return jsonify({
        "success": True,
        "log": graph_store.cypher_query_log
    })

@app.route('/api/neo4j/cypher', methods=['POST'])
def execute_cypher():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "error": "Query is required"}), 400

    res = graph_store.execute_cypher(query)
    return jsonify(res)

@app.route('/api/reset', methods=['POST'])
def reset_database():
    res = seed_graph_database(force_reset=True)
    return jsonify({"success": True, "message": "Graph reset to initial last week memories!", "details": res})

if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    port = int(os.environ.get("PORT", 5055))
    print("==================================================")
    print(f"[*] Neo4j Anonymized Memory Agent running on http://127.0.0.1:{port}")
    print("==================================================")
    app.run(host='0.0.0.0', port=port, debug=False)
