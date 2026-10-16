"""
memory_service.py
Core Intelligence & Habit Execution Service.
- Memorizes past user conversations and bookings in Neo4j.
- Detects user intent and parameters (origin, destination, date, city).
- In 'Flight Booking' mode: only prompts for where-to-where & date, then auto-books
  applying stored habits (Window seat, Veg meal, IndiGo airline, Economy class).
- In 'Tourist Place' mode: prompts for current location, then recommends sights
  tailored to user's past exploration affinity (heritage monuments, architecture).
"""

import re
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from neo4j_store import graph_store
from anonymizer import anonymizer_instance

# Curated City Knowledge for Tourist Suggestions
CITY_TOURIST_DATABASE = {
    "lucknow": [
        {
            "id": "tourist_lko_bara_imambara",
            "name": "Bara Imambara & Bhool Bhulaiya",
            "category": "Historical Monument",
            "heritage_type": "Awadhi & Mughal Architectural Marvel",
            "highlights": "Grand unsupported arched hall, maze of Bhool Bhulaiya, step-well (Bowli)",
            "timing": "6:00 AM - 5:00 PM",
            "entry_fee": "₹50 (Indians) / ₹500 (Foreigners)",
            "affinity_reason": "Matches your Red Fort visit last week: magnificent arched halls & grand historical masonry.",
            "image": "https://images.unsplash.com/photo-1598890777032-bde835ba27c2?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_lko_rumi_darwaza",
            "name": "Rumi Darwaza & Chota Imambara",
            "category": "Ancient Monument",
            "heritage_type": "Turkish Gateway Architecture",
            "highlights": "60-foot grand gateway, intricate chandelier collections in Chota Imambara",
            "timing": "Open 24 Hours (Exterior) / 6:00 AM - 5:00 PM",
            "entry_fee": "Free for Gate / ₹50 for Chota Imambara",
            "affinity_reason": "Matches your Qutub Minar interest: iconic ancient stone engineering & towering grandeur.",
            "image": "https://images.unsplash.com/photo-1628155930542-3c7a64e2c833?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_lko_residency",
            "name": "The British Residency",
            "category": "Historical Memorial",
            "heritage_type": "1857 Uprising Historic Ruins & Museum",
            "highlights": "Cannon-shot scarred brick ruins, peaceful green lawns, dedicated historical gallery",
            "timing": "10:00 AM - 5:00 PM",
            "entry_fee": "₹25",
            "affinity_reason": "Matches your India Gate memorial visit: poignant historic battlefield memorial set in manicured gardens.",
            "image": "https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_lko_ambedkar_park",
            "name": "Ambedkar Memorial Park & Gomti Riverfront",
            "category": "Metropolitan Landmark",
            "heritage_type": "Grand Pink Sandstone Architecture",
            "highlights": "Hundreds of elephant stone pillars, colossal pink stupa, sunset river walk",
            "timing": "11:00 AM - 9:00 PM",
            "entry_fee": "₹20",
            "affinity_reason": "Matches your appreciation of grand metropolitan public architecture.",
            "image": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=600&auto=format&fit=crop&q=80"
        }
    ],
    "varanasi": [
        {
            "id": "tourist_vns_kashi_vishwanath",
            "name": "Kashi Vishwanath Corridor & Temple",
            "category": "Heritage Corridor",
            "heritage_type": "Ancient Sacred Architectural Corridor",
            "highlights": "Newly transformed riverfront corridor linking Ganga to the golden-spired Jyotirlinga",
            "timing": "3:00 AM - 11:00 PM",
            "entry_fee": "Free (General Entry)",
            "affinity_reason": "Matches your historical monument preference: deeply ancient architecture with grand sandstone courtyards.",
            "image": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_vns_dashashwamedh_ghat",
            "name": "Dashashwamedh Ghat (Grand Ganga Aarti)",
            "category": "Cultural Landmark",
            "heritage_type": "Ancient Riverfront Promenade",
            "highlights": "Grand brass lamps ceremony, historic ghat steps, evening boat rides",
            "timing": "Evening 6:30 PM (Aarti)",
            "entry_fee": "Free",
            "affinity_reason": "Matches your India Gate cultural promenade habit: spectacular open-air cultural gathering.",
            "image": "https://images.unsplash.com/photo-1609137144822-09c314b10b0e?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_vns_ramnagar_fort",
            "name": "Ramnagar Fort & Vintage Museum",
            "category": "Historical Monument",
            "heritage_type": "18th-Century Mughal-Rajput Sandstone Fort",
            "highlights": "Chunar sandstone bastions, royal vintage car collection, armory museum overlooking the river",
            "timing": "10:00 AM - 5:00 PM",
            "entry_fee": "₹50",
            "affinity_reason": "Direct match for your Red Fort visit last week: grand defensive sandstone ramparts by the river.",
            "image": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_vns_sarnath",
            "name": "Sarnath Archaeological Ruins & Dhamek Stupa",
            "category": "Ancient Monument",
            "heritage_type": "UNESCO Tentative Ancient Stupa (500 CE)",
            "highlights": "43-meter cylindrical stone stupa, Ashoka Pillar edicts, Deer Park excavations",
            "timing": "6:00 AM - 6:00 PM",
            "entry_fee": "₹25",
            "affinity_reason": "Matches your Qutub Minar interest: profound ancient stone masonry and carved cylindrical monuments.",
            "image": "https://images.unsplash.com/photo-1598890777032-bde835ba27c2?w=600&auto=format&fit=crop&q=80"
        }
    ],
    "pune": [
        {
            "id": "tourist_pune_shaniwar_wada",
            "name": "Shaniwar Wada",
            "category": "Historical Monument",
            "heritage_type": "18th Century Peshwa Fort & Palace Grounds",
            "highlights": "Delhi Darwaza spiked gates, stone fortification ramparts, fountain court, sound & light show",
            "timing": "9:30 AM - 5:30 PM",
            "entry_fee": "₹25",
            "affinity_reason": "Direct match for your Red Fort exploration: historic fortress gates and royal seat of governance.",
            "image": "https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_pune_aga_khan_palace",
            "name": "Aga Khan Palace",
            "category": "Heritage Memorial",
            "heritage_type": "Italian Arches & Freedom Movement Landmark",
            "highlights": "Graceful Italianate arches, sprawling manicured gardens, Gandhi memorials and archives",
            "timing": "9:00 AM - 5:30 PM",
            "entry_fee": "₹25",
            "affinity_reason": "Matches your India Gate memorial visit: historic national heritage set within tranquil open lawns.",
            "image": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_pune_sinhagad_fort",
            "name": "Sinhagad Fort",
            "category": "Ancient Monument",
            "heritage_type": "Hilltop Military Fortress",
            "highlights": "Tanaji Malusare memorial, ancient cliff bastions, traditional pithla bhakri food stalls",
            "timing": "5:00 AM - 6:00 PM",
            "entry_fee": "₹50 (Vehicle Entry)",
            "affinity_reason": "Matches your love for grand stone fortresses and historical legends.",
            "image": "https://images.unsplash.com/photo-1598890777032-bde835ba27c2?w=600&auto=format&fit=crop&q=80"
        }
    ],
    "bangalore": [
        {
            "id": "tourist_blr_palace",
            "name": "Bangalore Palace",
            "category": "Historical Monument",
            "heritage_type": "Tudor-Style Royal Castle",
            "highlights": "Fortified towers, Gothic stained glass, vintage paintings, sprawling royal courtyards",
            "timing": "10:00 AM - 5:30 PM",
            "entry_fee": "₹250 (Indians) / ₹450 (Foreigners)",
            "affinity_reason": "Matches your Red Fort appreciation: magnificent royal residence with fortified stone towers.",
            "image": "https://images.unsplash.com/photo-1598890777032-bde835ba27c2?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_blr_tipu_palace",
            "name": "Tipu Sultan's Summer Palace",
            "category": "Ancient Monument",
            "heritage_type": "Indo-Islamic Teakwood Architecture",
            "highlights": "Ornate teakwood pillars, fluted arches, floral wall motifs, historical museum",
            "timing": "8:30 AM - 5:30 PM",
            "entry_fee": "₹20",
            "affinity_reason": "Matches your Mughal architecture taste from last week: exquisite Indo-Islamic arches and wooden artistry.",
            "image": "https://images.unsplash.com/photo-1628155930542-3c7a64e2c833?w=600&auto=format&fit=crop&q=80"
        },
        {
            "id": "tourist_blr_lalbagh",
            "name": "Lalbagh Botanical Garden & Glass House",
            "category": "Heritage Garden",
            "heritage_type": "Historic 240-Acre Royal Botanical Haven",
            "highlights": "Victorian-style Glass House inspired by Crystal Palace, 3,000-million-year-old rock, ancient trees",
            "timing": "6:00 AM - 7:00 PM",
            "entry_fee": "₹30",
            "affinity_reason": "Matches your India Gate & Sunder Nursery open-air heritage strolls.",
            "image": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=600&auto=format&fit=crop&q=80"
        }
    ]
}

# Fallback generic attractions for any city
DEFAULT_TOURIST_SUGGESTIONS = [
    {
        "id": "tourist_gen_fort",
        "name": "City Heritage Fort & Citadel",
        "category": "Historical Monument",
        "heritage_type": "Ancient Stone Architecture",
        "highlights": "Grand ramparts, watchtowers, royal halls and heritage museum",
        "timing": "9:00 AM - 5:00 PM",
        "entry_fee": "₹50",
        "affinity_reason": "Matches your past affinity for majestic fortresses and architectural history.",
        "image": "https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?w=600&auto=format&fit=crop&q=80"
    },
    {
        "id": "tourist_gen_museum",
        "name": "State Archaeological & Culture Museum",
        "category": "Cultural Landmark",
        "heritage_type": "Heritage Gallery & Antiquities",
        "highlights": "Sculptures from 10th century, numismatics, royal artifacts",
        "timing": "10:00 AM - 5:00 PM",
        "entry_fee": "₹30",
        "affinity_reason": "Matches your preference for cultural depth and historical artifacts.",
        "image": "https://images.unsplash.com/photo-1598890777032-bde835ba27c2?w=600&auto=format&fit=crop&q=80"
    }
]

AIRPORT_CODES = {
    "delhi": "DEL", "del": "DEL", "new delhi": "DEL",
    "lucknow": "LKO", "lko": "LKO",
    "bangalore": "BLR", "blr": "BLR", "bengaluru": "BLR",
    "pune": "PNQ", "pnq": "PNQ",
    "varanasi": "VNS", "vns": "VNS", "banaras": "VNS", "kashi": "VNS",
    "mumbai": "BOM", "bom": "BOM",
    "jaipur": "JAI", "jai": "JAI",
    "kolkata": "CCU", "ccu": "CCU",
    "hyderabad": "HYD", "hyd": "HYD",
    "chennai": "MAA", "maa": "MAA",
    "goa": "GOI", "goi": "GOI"
}

class MemoryChatService:
    def __init__(self):
        self.user_id = "user_primary_anon"

    def parse_flight_request(self, text: str) -> Dict[str, Optional[str]]:
        """
        Parses origin, destination, and travel date from user query.
        Handles English and Hinglish patterns:
        - "lko to banglore on 12 oct"
        - "pune to varansai 12 oct"
        - "delhi se lucknow 15 october"
        - "delhi to lko"
        """
        clean_text = text.lower()

        # 1. Extract Origin and Destination
        # Pattern: "<from> to <to>" or "<from> se <to>"
        origin = None
        destination = None

        route_match = re.search(
            r'([a-z\s]+?)\s+(?:to|se|-|->)\s+([a-z\s]+?)(?:\s+(?:on|ko|tarikh|date|\d{1,2})|$)',
            clean_text
        )
        if route_match:
            cand_from = route_match.group(1).strip()
            cand_to = route_match.group(2).strip()
            # Clean common words
            cand_from = re.sub(r'\b(flight|tickets?|book|booking|karo|chahiye|from)\b', '', cand_from).strip()
            cand_to = re.sub(r'\b(flight|tickets?|book|booking|karo|chahiye|tak|jaana|jana)\b', '', cand_to).strip()

            if cand_from:
                origin = cand_from.title()
            if cand_to:
                destination = cand_to.title()

        # 2. Extract Date
        # e.g. "12 oct", "12 october", "15th nov", "tomorrow", "kal", "12/10/2026"
        date_cand = None
        date_match = re.search(r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)', clean_text)
        if date_match:
            date_cand = date_match.group(1).title()
        else:
            num_date_match = re.search(r'\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b', clean_text)
            if num_date_match:
                date_cand = num_date_match.group(1)
            elif "tomorrow" in clean_text or "kal" in clean_text:
                tomorrow = datetime.now() + timedelta(days=1)
                date_cand = tomorrow.strftime("%d %b %Y")
            elif "today" in clean_text or "aaj" in clean_text:
                date_cand = datetime.now().strftime("%d %b %Y")

        return {
            "origin": origin,
            "destination": destination,
            "date": date_cand
        }

    def parse_location_query(self, text: str) -> Optional[str]:
        """
        Extracts city name for tourist recommendations.
        Handles: "I am in Lucknow", "current location Varanasi", "Lucknow", "Pune", "at Bangalore"
        """
        clean_text = text.lower().strip()

        # Check known cities
        for city in ["lucknow", "varanasi", "pune", "bangalore", "bengaluru", "delhi", "mumbai", "jaipur", "kolkata"]:
            if city in clean_text:
                return "Bangalore" if city == "bengaluru" else city.title()

        # Match phrases: "in <City>", "at <City>", "location <City>"
        loc_match = re.search(r'(?:in|at|location|location is|shehar|area|city)\s+([a-zA-Z]+)', clean_text)
        if loc_match:
            cand = loc_match.group(1).title()
            if cand.lower() not in ["the", "my", "this", "tourist", "place"]:
                return cand

        # If user just typed 1 or 2 words (e.g. "Lucknow" or "New Delhi")
        words = clean_text.split()
        if len(words) <= 2 and not any(w in clean_text for w in ["hi", "hello", "suggest", "kya", "batao", "tourist", "place"]):
            return text.strip().title()

        return None

    def handle_flight_booking(self, message: str) -> Dict[str, Any]:
        """
        Flight booking execution:
        Pulls past habits from Neo4j, asks ONLY origin, destination, and date.
        When provided, automatically completes the flight booking!
        """
        # Anonymize any incoming user PII
        anon_msg, pii_detected = anonymizer_instance.anonymize_text(message)

        parsed = self.parse_flight_request(message)
        origin = parsed.get("origin")
        destination = parsed.get("destination")
        date = parsed.get("date")

        # Retrieve saved habits from Neo4j
        habits = graph_store.get_user_preferences(self.user_id)
        user_node = graph_store.nodes.get(self.user_id, {}).get("properties", {})
        passenger_token = user_node.get("traveler_token", "ANON_TRAV_784")
        masked_passenger = user_node.get("masked_name", "T*** S***")

        # If origin or destination or date is missing, politely and directly ask:
        if not origin or not destination:
            return {
                "reply": (
                    "✈️ **Flight Booking Assistant**\n\n"
                    "Mai aapki pichli booking (Delhi to Lucknow) aur preferences yaad rakhta hu! "
                    "Aapko koi extra details dene ki zaroorat nahi hai.\n\n"
                    "👉 **Bas mujhe ye bata dijiye:**\n"
                    "**Kaha se kaha jana hai aur kis date ko?**\n"
                    "*(e.g., 'LKO to Bangalore on 12 Oct' ya 'Pune to Varanasi 12 Oct')*\n\n"
                    "Jaise hi aap bataenge, mai aapki saved preferences ke sath automatically flight book kar dunga!"
                ),
                "quick_chips": [
                    "LKO to Bangalore on 12 Oct",
                    "Pune to Varanasi on 12 Oct",
                    "Delhi to Lucknow on 15 Oct",
                    "Mumbai to Goa on 18 Oct"
                ],
                "action_type": "NEED_FLIGHT_INPUT",
                "pii_anonymized": pii_detected
            }

        if not date:
            return {
                "reply": (
                    f"✈️ **{origin} se {destination}** ke liye flight route set hai!\n\n"
                    "📅 **Bas date bata dijiye:** (e.g. `12 Oct` ya `Tomorrow` ya `15 Oct`)\n\n"
                    "Mai aapki saved preferences ke sath turant book kar dunga!"
                ),
                "quick_chips": [
                    f"{origin} to {destination} on 12 Oct",
                    f"{origin} to {destination} on 15 Oct",
                    f"{origin} to {destination} tomorrow"
                ],
                "action_type": "NEED_DATE_INPUT",
                "pii_anonymized": pii_detected
            }

        # BOTH ROUTE & DATE ARE PRESENT -> AUTOMATICALLY BOOK FLIGHT!
        orig_code = AIRPORT_CODES.get(origin.lower(), origin[:3].upper())
        dest_code = AIRPORT_CODES.get(destination.lower(), destination[:3].upper())
        flight_number = f"6E-{random.randint(2000, 7999)}"
        pnr = f"6E-{dest_code}{random.randint(10, 99)}"

        seat = habits.get("seat_selection") or habits.get("seat", "12F (Window)")
        meal = habits.get("meal_code") or habits.get("meal", "Vegetarian Snack Combo")
        airline = habits.get("favorite_airline") or habits.get("airline", "IndiGo")
        cabin_class = habits.get("cabin_class") or habits.get("class", "Economy")
        fare = f"₹{random.randint(4200, 6800):,}"

        dep_hour = random.choice(["06:30 AM", "08:15 AM", "11:40 AM", "03:10 PM", "07:25 PM"])
        arr_hour = random.choice(["08:45 AM", "10:30 AM", "02:00 PM", "05:30 PM", "09:40 PM"])

        # Create Neo4j Nodes and Relationships
        route_id = f"route_{orig_code.lower()}_{dest_code.lower()}"
        graph_store.add_node("Route", route_id, {
            "route_code": f"{orig_code} -> {dest_code}",
            "origin_city": origin,
            "origin_code": orig_code,
            "destination_city": destination,
            "destination_code": dest_code,
            "created_via": "Auto-Memory"
        })

        booking_id = f"flight_booking_{pnr.lower()}"
        booking_data = {
            "flight_number": flight_number,
            "airline": airline,
            "origin": f"{origin} ({orig_code})",
            "destination": f"{destination} ({dest_code})",
            "departure_time": dep_hour,
            "arrival_time": arr_hour,
            "booking_date": datetime.now().strftime("%Y-%m-%d"),
            "travel_date": date,
            "pnr": pnr,
            "seat": seat,
            "meal": meal,
            "class": cabin_class,
            "fare": fare,
            "status": "CONFIRMED_AUTOMATICALLY",
            "anonymized_passenger": passenger_token,
            "masked_passenger": masked_passenger,
            "auto_applied_memory": True
        }
        graph_store.add_node("FlightBooking", booking_id, booking_data)

        # Graph Relationships
        graph_store.add_relationship(self.user_id, booking_id, "BOOKED_FLIGHT", {"auto_generated": True})
        graph_store.add_relationship(booking_id, route_id, "FOR_ROUTE")
        graph_store.add_relationship(booking_id, "folder_flights", "SAVED_IN_FOLDER")

        reply_text = (
            f"🎉 **Flight Ticket Automatically Booked!**\n\n"
            f"Aapne pichle conversation me **Delhi to Lucknow** book kiya tha, wahi se seekh kar "
            f"maine aapki saved habits automatically apply kar di hain:\n\n"
            f"- ✈️ **Flight:** {airline} `{flight_number}`\n"
            f"- 📍 **Route:** **{origin} ({orig_code})** ➔ **{destination} ({dest_code})**\n"
            f"- 📅 **Travel Date:** **{date}**\n"
            f"- 💺 **Seat:** **{seat}** *(Memorized)*\n"
            f"- 🍱 **Meal:** **{meal}** *(Memorized)*\n"
            f"- 🎫 **Cabin Class:** {cabin_class}\n"
            f"- 👤 **Passenger:** `{masked_passenger}` *(Privacy Token: {passenger_token})*\n"
            f"- 🔖 **PNR Code:** **`{pnr}`**\n\n"
            f"🔒 *Ye transaction Neo4j graph database me anonymize karke store ho gaya hai.*"
        )

        return {
            "reply": reply_text,
            "action_type": "FLIGHT_BOOKED",
            "flight_ticket": booking_data,
            "pii_anonymized": pii_detected,
            "quick_chips": [
                "Book return flight",
                "View Neo4j Graph",
                "Explore Tourist Places in " + destination
            ]
        }

    def handle_tourist_recommendation(self, message: str) -> Dict[str, Any]:
        """
        Tourist place execution:
        Takes user's current location, leverages last week's visit memory
        (metropolitan monuments, heritage architecture) to suggest top sights.
        """
        anon_msg, pii_detected = anonymizer_instance.anonymize_text(message)

        city = self.parse_location_query(message)
        if not city:
            return {
                "reply": (
                    "📍 **Tourist Place Guide (Memory-Powered)**\n\n"
                    "Pichle hafte aapne Delhi (metropolitan area) me Red Fort, Qutub Minar aur India Gate visit kiya tha. "
                    "Mujhe aapki **historical monuments aur architectural heritage** ki preference yaad hai!\n\n"
                    "👉 **Bas mujhe apni current location / city bata dijiye:**\n"
                    "*(e.g., 'Lucknow', 'Varanasi', 'Pune', 'Bangalore', ya niche click karein)*\n\n"
                    "Mai waha ke best places aapke taste ke mutabiq suggest kar dunga!"
                ),
                "quick_chips": [
                    "📍 Lucknow",
                    "📍 Varanasi",
                    "📍 Pune",
                    "📍 Bangalore"
                ],
                "action_type": "NEED_LOCATION_INPUT",
                "pii_anonymized": pii_detected
            }

        city_key = city.lower().strip()
        places = CITY_TOURIST_DATABASE.get(city_key, DEFAULT_TOURIST_SUGGESTIONS)

        # Store Location & Recommendation in Neo4j
        loc_id = f"loc_{city_key}"
        graph_store.add_node("Location", loc_id, {
            "name": city,
            "visited_state": "Current Location Detected",
            "updated_at": datetime.now().strftime("%Y-%m-%d")
        })

        for p in places:
            graph_store.add_node("TouristPlace", p["id"], p)
            graph_store.add_relationship(p["id"], loc_id, "LOCATED_IN")
            graph_store.add_relationship(self.user_id, p["id"], "RECOMMENDED_FOR_HABIT", {
                "basis": "Last week metropolitan heritage visits",
                "city": city
            })
            graph_store.add_relationship(p["id"], "folder_tourist", "SAVED_IN_FOLDER")

        reply_text = (
            f"🏛️ **Top Tourist Places in {city}**\n\n"
            f"Pichle hafte aapne metropolitan area me **Red Fort, Qutub Minar aur India Gate** visit kiye the. "
            f"Aapke **heritage architecture aur grand monuments** ke taste ke basis par, "
            f"**{city}** me ye top recommendations hain:\n\n"
        )

        for idx, p in enumerate(places, 1):
            reply_text += (
                f"**{idx}. {p['name']}** ({p['category']})\n"
                f"- 💡 *Kyu pasand aayega:* {p['affinity_reason']}\n"
                f"- 🕒 *Timing:* {p['timing']} | 🎟️ *Entry:* {p['entry_fee']}\n\n"
            )

        reply_text += "✨ *Aap kisi bhi jagah ko 'Visited' mark kar sakte hain, ye Neo4j graph me save ho jayegi!*"

        return {
            "reply": reply_text,
            "action_type": "TOURIST_RECOMMENDED",
            "city": city,
            "tourist_places": places,
            "pii_anonymized": pii_detected,
            "quick_chips": [
                f"Mark 1st spot as visited",
                f"Book flight from {city}",
                "View Neo4j Graph"
            ]
        }

    def mark_place_visited(self, place_id: str) -> Dict[str, Any]:
        """Marks a tourist place as visited by user in Neo4j."""
        place_node = graph_store.nodes.get(place_id, {})
        place_name = place_node.get("properties", {}).get("name", "Tourist Place")

        graph_store.add_relationship(self.user_id, place_id, "VISITED", {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "User Check-in"
        })
        return {
            "success": True,
            "message": f"✅ '{place_name}' has been marked as visited and saved to your Neo4j memory graph!",
            "place_name": place_name
        }

    def handle_general_chat(self, message: str) -> Dict[str, Any]:
        """Handles general conversation and guides the user."""
        anon_msg, pii_detected = anonymizer_instance.anonymize_text(message)
        clean = message.lower()

        # Check if flight intent in general chat
        if any(w in clean for w in ["flight", "book flight", "plane", "ticket"]):
            return self.handle_flight_booking(message)

        # Check if tourist intent in general chat
        if any(w in clean for w in ["tourist", "sightseeing", "visit", "ghoomne", "place", "location"]):
            return self.handle_tourist_recommendation(message)

        reply = (
            "👋 Namaste! Mai aapka Neo4j Anonymized Memory Agent hu.\n\n"
            "Maine aapki pichle hafte ki chat aur activities memorise ki hui hain:\n"
            "- ✈️ **Flight Booking Memory:** Delhi to Lucknow (Window Seat, Veg Meal, IndiGo)\n"
            "- 🏛️ **Tourist Exploration Memory:** Metropolitan Delhi (Red Fort, Qutub Minar, India Gate)\n\n"
            "Aap left sidebar ke folders use kar sakte hain:\n"
            "1. **Flight Booking Folder:** Bas mujhe origin, destination aur date batao, baki sab mai auto-book kar dunga!\n"
            "2. **Tourist Place Folder:** Bas apni current location batao, mai aapke taste ke according best places suggest kar dunga!\n"
            "3. **Neo4j Graph View:** Live visual graph nodes aur Cypher queries check karein!"
        )

        return {
            "reply": reply,
            "action_type": "GENERAL_REPLY",
            "pii_anonymized": pii_detected,
            "quick_chips": [
                "Open Flight Booking",
                "Open Tourist Places",
                "Book LKO to Bangalore 12 Oct",
                "Current Location: Lucknow",
                "View Neo4j Graph"
            ]
        }

# Global singleton
memory_service = MemoryChatService()
