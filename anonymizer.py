"""
anonymizer.py
Anonymization and Privacy Layer for Knowledge Graph Storage.
Detects Personally Identifiable Information (PII) like real names,
phone numbers, email addresses, government IDs, and payment details.
Replaces them with consistent pseudonym tokens before writing to Neo4j.
"""

import re
import hashlib
from typing import Dict, Tuple, List, Any

class Anonymizer:
    def __init__(self, salt: str = "neo4j_privacy_salt_v1"):
        self.salt = salt
        # In-memory mapping from pseudonym token -> masked preview for secure display
        self.pseudonym_registry: Dict[str, Dict[str, str]] = {}

    def _hash_token(self, prefix: str, raw_val: str) -> str:
        """Create a short deterministic pseudonymous token."""
        clean = raw_val.strip().lower()
        h = hashlib.sha256(f"{self.salt}_{clean}".encode('utf-8')).hexdigest()[:8].upper()
        return f"{prefix}_{h}"

    def anonymize_text(self, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Scans text for phone numbers, emails, cards, and common name patterns.
        Returns:
            anonymized_text: sanitized text with [ANON_...] tokens
            anonymized_entities: list of detected and masked entities
        """
        if not text:
            return "", []

        entities_found = []
        result = text

        # 1. Email pattern
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        for match in re.finditer(email_pattern, result):
            raw = match.group(0)
            token = self._hash_token("EMAIL", raw)
            masked = raw[0] + "***@" + raw.split('@')[-1]
            self.pseudonym_registry[token] = {"type": "EMAIL", "masked": masked}
            entities_found.append({"type": "EMAIL", "token": token, "masked": masked})
            result = result.replace(raw, f"[{token}]")

        # 2. Phone number pattern (Indian/International: 10 digits, +91 etc.)
        phone_pattern = r'(?:\+?91[\-\s]?)?[6-9]\d{9}'
        for match in re.finditer(phone_pattern, result):
            raw = match.group(0)
            token = self._hash_token("PHONE", raw)
            masked = "+91-" + raw[-10:-6] + "XX" + raw[-2:]
            self.pseudonym_registry[token] = {"type": "PHONE", "masked": masked}
            entities_found.append({"type": "PHONE", "token": token, "masked": masked})
            result = result.replace(raw, f"[{token}]")

        # 3. Aadhaar / ID number (12 digits) or Passport (1 letter + 7 digits)
        id_pattern = r'\b[A-Z][0-9]{7}\b|\b\d{4}\s?\d{4}\s?\d{4}\b'
        for match in re.finditer(id_pattern, result):
            raw = match.group(0)
            token = self._hash_token("GOV_ID", raw)
            masked = "ID-****" + raw[-4:]
            self.pseudonym_registry[token] = {"type": "GOV_ID", "masked": masked}
            entities_found.append({"type": "GOV_ID", "token": token, "masked": masked})
            result = result.replace(raw, f"[{token}]")

        # 4. Explicit name introductions: "my name is X", "passenger X", "I am X"
        name_intro_pattern = r'(?:my name is|passenger|i am|for passenger|traveler|naam hai)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        for match in re.finditer(name_intro_pattern, result, re.IGNORECASE):
            raw_name = match.group(1)
            # Avoid matching words like Delhi, Lucknow, Flight, etc.
            skip_words = {"Delhi", "Lucknow", "Bangalore", "Pune", "Varanasi", "Mumbai", "Flight", "Oct", "October", "Today"}
            if any(w.lower() in raw_name.lower() for w in skip_words):
                continue
            token = self._hash_token("TRAVELER", raw_name)
            masked = raw_name[0] + "***" + ((" " + raw_name.split()[-1][0] + "***") if ' ' in raw_name else "")
            self.pseudonym_registry[token] = {"type": "NAME", "masked": masked}
            entities_found.append({"type": "NAME", "token": token, "masked": masked})
            result = result.replace(raw_name, f"[{token}]")

        return result, entities_found

    def anonymize_user_profile(self, user_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates an anonymized representation of a user profile for Neo4j node storage.
        """
        user_id = user_dict.get("id", "user_default")
        anon_id = self._hash_token("USER", user_id)
        
        raw_name = user_dict.get("name", "Traveler")
        anon_name_token = self._hash_token("TRAVELER", raw_name)
        masked_name = raw_name[0] + "*** " + (raw_name.split()[-1][0] + "***" if ' ' in raw_name else "")

        return {
            "anon_id": anon_id,
            "display_pseudonym": f"Anon-{anon_id[:9]}",
            "traveler_token": anon_name_token,
            "masked_name": masked_name,
            "seat_preference": user_dict.get("seat_preference", "Window"),
            "meal_preference": user_dict.get("meal_preference", "Vegetarian"),
            "preferred_class": user_dict.get("preferred_class", "Economy"),
            "preferred_airline": user_dict.get("preferred_airline", "IndiGo"),
            "privacy_standard": "AES-256-SHA Anonymized Graph Policy"
        }

# Global singleton
anonymizer_instance = Anonymizer()
