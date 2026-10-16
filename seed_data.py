"""
seed_data.py
Pre-populates the Anonymized Neo4j Graph with:
1. Last Week's Flight Booking: Delhi to Lucknow (LKO), Window seat, Veg meal, IndiGo.
2. Last Week's Tourist Activity: Explored Metropolitan Delhi (Red Fort, Qutub Minar, India Gate).
3. Folders: Flight Booking, Tourist Places, General.
4. Anonymized Traveler Profile & Learned Preferences.
"""

from neo4j_store import graph_store
from anonymizer import anonymizer_instance

def seed_graph_database(force_reset: bool = False):
    """Initializes the knowledge graph with last week's memory if not already present."""
    if not force_reset and len(graph_store.nodes) > 0:
        return {"status": "already_seeded", "nodes": len(graph_store.nodes)}

    if force_reset:
        graph_store.nodes.clear()
        graph_store.edges.clear()

    # 1. Anonymized User Node
    user_id = "user_primary_anon"
    raw_user = {
        "id": "tushar_user",
        "name": "Tushar Sharma",
        "phone": "+91 9876543210",
        "seat_preference": "Window (Seat 12F)",
        "meal_preference": "Vegetarian",
        "preferred_class": "Economy",
        "preferred_airline": "IndiGo"
    }
    anon_user = anonymizer_instance.anonymize_user_profile(raw_user)
    graph_store.add_node("User", user_id, {
        "anon_id": anon_user["anon_id"],
        "display_pseudonym": anon_user["display_pseudonym"],
        "traveler_token": anon_user["traveler_token"],
        "masked_name": anon_user["masked_name"],
        "membership_tier": "Silver Traveler",
        "memory_window": "7_days_active"
    })

    # 2. Folder Nodes
    folders = [
        {"id": "folder_flights", "name": "Flight Booking", "icon": "plane", "tagline": "Auto-book flights based on past habit"},
        {"id": "folder_tourist", "name": "Tourist Places", "icon": "map-pin", "tagline": "Suggests sights from current location based on taste"},
        {"id": "folder_general", "name": "General Assistant", "icon": "sparkles", "tagline": "Open conversation with graph memory"}
    ]
    for f in folders:
        graph_store.add_node("Folder", f["id"], f)
        graph_store.add_relationship(user_id, f["id"], "HAS_FOLDER", {"created_at": "2026-10-01"})

    # 3. User Preferences Node (Learned from Last Week)
    pref_id = "pref_traveler_habits"
    graph_store.add_node("Preference", pref_id, {
        "seat_selection": "Window Seat",
        "meal_code": "VGML (Pure Vegetarian)",
        "cabin_class": "Economy",
        "favorite_airline": "IndiGo",
        "baggage_allowance": "15 Kg Check-in + 7 Kg Cabin",
        "tourist_affinity": ["Historical Monuments", "Architectural Heritage", "Cultural Landmarks", "Open Gardens"],
        "privacy_compliance": "Anonymized via AES-SHA256 Tokenization"
    })
    graph_store.add_relationship(user_id, pref_id, "HAS_PREFERENCE", {"confidence": 0.98})

    # 4. Last Week's Flight Booking: Delhi to Lucknow
    route_id = "route_del_lko"
    graph_store.add_node("Route", route_id, {
        "route_code": "DEL -> LKO",
        "origin_city": "Delhi",
        "origin_code": "DEL",
        "destination_city": "Lucknow",
        "destination_code": "LKO",
        "typical_duration": "1h 15m"
    })

    flight_lastweek_id = "flight_booking_del_lko_001"
    graph_store.add_node("FlightBooking", flight_lastweek_id, {
        "flight_number": "6E-2054",
        "airline": "IndiGo",
        "origin": "Delhi (DEL)",
        "destination": "Lucknow (LKO)",
        "departure_time": "08:15 AM",
        "arrival_time": "09:30 AM",
        "booking_date": "2026-10-04",
        "travel_date": "2026-10-04",
        "pnr": "6E-W8K92",
        "seat": "12F (Window)",
        "meal": "Vegetarian Snack",
        "class": "Economy",
        "fare": "₹3,850",
        "status": "COMPLETED_LAST_WEEK",
        "anonymized_passenger": anon_user["traveler_token"]
    })
    graph_store.add_relationship(user_id, flight_lastweek_id, "BOOKED_FLIGHT", {"timestamp": "2026-10-04T10:00:00"})
    graph_store.add_relationship(flight_lastweek_id, route_id, "FOR_ROUTE")
    graph_store.add_relationship(flight_lastweek_id, "folder_flights", "SAVED_IN_FOLDER")

    # 5. Last Week's Metropolitan Tourist Visits (Delhi Area)
    loc_delhi = "loc_delhi"
    graph_store.add_node("Location", loc_delhi, {
        "name": "Delhi",
        "type": "Metropolitan Capital",
        "region": "North India"
    })

    delhi_places = [
        {
            "id": "tourist_red_fort",
            "name": "Red Fort (Lal Qila)",
            "category": "Historical Monument",
            "style": "Mughal Architecture",
            "highlights": "Grand red sandstone ramparts, Diwan-i-Aam, royal heritage",
            "visit_date": "2026-10-05"
        },
        {
            "id": "tourist_qutub_minar",
            "name": "Qutub Minar",
            "category": "Ancient Monument",
            "style": "Indo-Islamic Architecture",
            "highlights": "73m minaret, intricate carvings, Iron Pillar of Delhi",
            "visit_date": "2026-10-06"
        },
        {
            "id": "tourist_india_gate",
            "name": "India Gate & Kartavya Path",
            "category": "Cultural Landmark",
            "style": "Memorial & Boulevard",
            "highlights": "War memorial, evening promenade, vibrant open atmosphere",
            "visit_date": "2026-10-07"
        }
    ]

    for p in delhi_places:
        graph_store.add_node("TouristPlace", p["id"], p)
        graph_store.add_relationship(p["id"], loc_delhi, "LOCATED_IN")
        graph_store.add_relationship(user_id, p["id"], "VISITED", {
            "date": p["visit_date"],
            "rating": 5,
            "impression": "Enjoys rich historical monuments & architectural heritage"
        })
        graph_store.add_relationship(p["id"], "folder_tourist", "SAVED_IN_FOLDER")

    # 6. Learned Affinity Node
    affinity_id = "affinity_heritage_history"
    graph_store.add_node("Preference", affinity_id, {
        "name": "Heritage & Historical Monuments Affinity",
        "primary_interest": "Heritage Architecture & Forts",
        "secondary_interest": "Cultural Landmarks & Local Heritage",
        "score": 0.95,
        "derived_from": "3 visits last week in Delhi Metropolitan area"
    })
    graph_store.add_relationship(user_id, affinity_id, "PREFERS", {"score": 0.95})

    # Save to disk
    graph_store._save_local_store()

    # Sync to Neo4j if server is active
    if graph_store.is_connected:
        graph_store.sync_all_to_neo4j()

    return {"status": "seeded", "nodes": len(graph_store.nodes), "edges": len(graph_store.edges)}

if __name__ == "__main__":
    result = seed_graph_database(force_reset=True)
    print(f"Seed completed: {result}")
