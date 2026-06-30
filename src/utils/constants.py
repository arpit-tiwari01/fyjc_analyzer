"""
src/utils/constants.py
======================
All static constants used across the application.
Centralizing them here avoids magic strings scattered in code.
"""

# ─── Streams ──────────────────────────────────────────────────────────────────
STREAMS = {
    "science": ["Science", "SCIENCE", "sci"],
    "commerce": ["Commerce", "COMMERCE", "com"],
    "arts": ["Arts", "ARTS", "art", "Humanities"],
}

STREAM_DISPLAY = ["Science", "Commerce", "Arts"]

# ─── Reservation Categories ───────────────────────────────────────────────────
# Maps user-friendly names to column names in the dataset
CATEGORY_MAP = {
    "General (Open)": "General",
    "SC (Scheduled Caste)": "SC",
    "ST (Scheduled Tribe)": "ST",
    "VJA (Vimukta Jati A)": "VJA",
    "NTB (Nomadic Tribe B)": "NTB",
    "NTC (Nomadic Tribe C)": "NTC",
    "NTD (Nomadic Tribe D)": "NTD",
    "OBC (Other Backward Class)": "OBC",
    "SBC (Special Backward Class)": "SBC",
    "SEBC (Socially & Educationally Backward Class)": "SEBC",
    "EWS (Economically Weaker Section)": "EWS",
}

# Short codes for display
CATEGORY_SHORT = {v: k.split(" ")[0] for k, v in CATEGORY_MAP.items()}

ALL_CATEGORIES = list(CATEGORY_MAP.values())

# ─── Medium of Instruction ────────────────────────────────────────────────────
MEDIUMS = ["English", "Marathi", "Semi-English", "Urdu", "Hindi", "Gujarati"]

# ─── Admission Rounds ─────────────────────────────────────────────────────────
ROUNDS = {
    1: "Round 1 (CAP Round 1)",
    2: "Round 2 (CAP Round 2)",
    3: "Round 3 (CAP Round 3)",
    4: "Special Round",
    5: "Institutional Round",
}

# ─── Known Areas / Localities in Maharashtra ──────────────────────────────────
# Used for area-based filtering via fuzzy matching on college names / addresses
MUMBAI_AREAS = [
    "Mulund", "Thane", "Kalwa", "Bhandup", "Airoli", "Vikhroli",
    "Ghatkopar", "Kurla", "Chembur", "Dadar", "Worli", "Andheri",
    "Borivali", "Kandivali", "Malad", "Goregaon", "Jogeshwari",
    "Santacruz", "Vile Parle", "Powai", "Belapur", "Kharghar",
    "Panvel", "Dombivli", "Kalyan", "Ulhasnagar", "Ambernath",
    "Badlapur", "Mira Road", "Bhayander", "Vasai", "Virar",
    "Nalasopara", "Palghar",
]

PUNE_AREAS = [
    "Pune", "Pimpri", "Chinchwad", "Hadapsar", "Kothrud", "Shivajinagar",
    "Deccan", "Camp", "Kondhwa", "Wagholi", "Magarpatta", "Baner",
    "Aundh", "Wakad", "Hinjewadi", "Nigdi", "Akurdi",
]

NASHIK_AREAS = ["Nashik", "Malegaon", "Deolali"]
NAGPUR_AREAS = ["Nagpur", "Wardha", "Amravati"]
AURANGABAD_AREAS = ["Aurangabad", "Jalna", "Nanded", "Latur"]

ALL_AREAS = sorted(
    MUMBAI_AREAS + PUNE_AREAS + NASHIK_AREAS + NAGPUR_AREAS + AURANGABAD_AREAS
)

# ─── College Status Types ─────────────────────────────────────────────────────
COLLEGE_STATUS = {
    "G": "Government",
    "A": "Aided",
    "U": "Unaided",
    "J": "Junior College",
}

# ─── Classification Labels ────────────────────────────────────────────────────
CLASSIFICATION = {
    "safe": "🟢 Safe",
    "moderate": "🟡 Moderate",
    "dream": "🔴 Dream",
}

# ─── SSC Marks Range ─────────────────────────────────────────────────────────
SSC_MIN_MARKS = 0
SSC_MAX_MARKS = 100  # Percentage

# ─── Gender Options ───────────────────────────────────────────────────────────
GENDER_OPTIONS = ["Male", "Female", "Other"]

# ─── Display Column Labels ────────────────────────────────────────────────────
DISPLAY_COLUMNS = {
    "collegename": "College Name",
    "stream": "Stream",
    "medium": "Medium",
    "districtid": "District",
    "cutoff": "Cutoff %",
    "user_marks": "Your Marks %",
    "difference": "Difference",
    "classification": "Category",
    "round_id": "Round",
}
