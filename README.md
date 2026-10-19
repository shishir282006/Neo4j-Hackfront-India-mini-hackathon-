# 🧠 Neo4j Anonymized Memory Agent Web App

An intelligent AI chatbot web application with an **Anonymized Graph Database (Neo4j)** that memorizes your past week's chats and habits to perform repetitive tasks automatically with minimal user friction.

---


## 🌟 Key Features


### 1. 📁 Categorized Folders
- ✈️ **Flight Booking Folder (`flight booking`)**:
  - Remembers your past flight booking from last week (**Delhi to Lucknow**).
  - Automatically recalls your preferences: **Seat (12F Window)**, **Meal (Pure Vegetarian)**, **Airline (IndiGo)**, **Class (Economy)**, and **Masked Traveler ID**.
  - **Zero hassle flow:** *Sirf date aur kaha se kaha jana hai puchta hai* (e.g. `LKO to Bangalore on 12 Oct` ya `Pune to Varanasi on 12 Oct`).
  - Once provided, it **automatically generates a confirmed flight ticket & PNR**, logging the new route in Neo4j.

- 📍 **Tourist Places Folder (`tourist place`)**:
  - Memorizes that last week you visited **Metropolitan Area (Delhi)** exploring **Red Fort (Mughal architecture)**, **Qutub Minar (ancient stone monument)**, and **India Gate (national cultural memorial)**.
  - **Zero hassle flow:** *Sirf aapki current location leta hai* (e.g. `Lucknow`, `Varanasi`, `Pune`, `Bangalore`).
  - Suggests top tourist sights in that area specifically matching your learned taste profile (historical monuments & architectural marvels).
  - Allows marking places as **"Visited"**, which links directly to your Neo4j knowledge graph.

- 🧠 **All Chats & Graph Memory (`all history`)**:
  - Open conversation mode with full access to semantic memory.

---

### 2. 🔒 Anonymized ("Anomalised") Database Layer
- **PII Protection:** Real passenger names, phone numbers, emails, and ID credentials are intercepted before Neo4j graph storage and hashed into persistent pseudonym tokens (e.g., `[ANON_TRAV_784]`, `[PHONE_MASKED]`, `[GOV_ID_MASKED]`).
- **Graph Topology:** Stores habits as semantic relationships:
  ```cypher
  (:User)-[:BOOKED_FLIGHT]->(:FlightBooking)-[:FOR_ROUTE]->(:Route)
  (:User)-[:HAS_PREFERENCE]->(:Preference)
  (:User)-[:VISITED]->(:TouristPlace)-[:LOCATED_IN]->(:Location)
  ```

---

### 3. 🕸️ Neo4j Dual-Engine Architecture
- **Official Neo4j Driver:** Uses `neo4j` Python driver (`bolt://localhost:7687` or Neo4j Aura).
- **Embedded Graph Engine Fallback:** Persistent JSON store (`data/anonymized_graph.json`) that works immediately without needing Neo4j to be started beforehand.
- **1-Click Sync:** Connect to your live Neo4j instance anytime from the web UI to push all nodes and edges via Cypher!
- **Interactive Visualizer:** Vis.js network graph in the UI with live node inspection and a built-in Cypher console.

---

## 🚀 Quick Start Guide

### 1. Run the Web Application
```powershell
cd C:\Users\Tushar\.gemini\antigravity\scratch\neo4j-memory-agent-app
python app.py
```
Open your browser at: **`http://127.0.0.1:5000`**

---

### 2. (Optional) Connect to Real Neo4j Server

#### Option A: Local Neo4j (Docker)
```powershell
docker run --name neo4j-memory -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password -d neo4j:latest
```

#### Option B: Neo4j Desktop / Neo4j Aura Cloud
1. In the web app, click **"Neo4j: Ready / Embedded"** in the top header.
2. Enter your Bolt URI (e.g., `bolt://localhost:7687` or `neo4j+s://...`).
3. Enter username & password.
4. Click **"Connect & Sync to Neo4j"**. All nodes and relationships will be synchronized instantly!

---


## 💬 Sample Prompts to Try

1. **In Flight Booking Folder:**
   - *"LKO to Bangalore on 12 Oct"*
   - *"Pune to Varanasi on 12 Oct"*
   - *"Delhi to Lucknow 15 Oct"*

2. **In Tourist Place Folder:**
   - *"Current location: Lucknow"*
   - *"Current location: Varanasi"*
   - *"Pune"*
   - *"Bangalore"*
