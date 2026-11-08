"""Approximate geography for synthetic data. Distances are straight-line estimates."""
import math

# Approximate city centres used to place synthetic records and resolve request locations.
# Add cities here as needed for your demo.
CITY_COORDS: dict[str, tuple[float, float]] = {
    # Pakistan (Punjab) - matches the team's demo scenario
    "faisalabad": (31.4504, 73.1350),
    "lahore": (31.5204, 74.3587),
    "jhang": (31.2681, 72.3181),
    "chiniot": (31.7200, 72.9789),
    "sargodha": (32.0836, 72.6711),
    "gujranwala": (32.1877, 74.1945),
    "sheikhupura": (31.7131, 73.9783),
    "toba tek singh": (30.9709, 72.4826),
    "okara": (30.8138, 73.4534),
    "islamabad": (33.6844, 73.0479),
    "karachi": (24.8607, 67.0011),
    # India
    "bhubaneswar": (20.2961, 85.8245),
    "cuttack": (20.4625, 85.8830),
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
}


def lookup_city(text: str | None) -> tuple[str, tuple[float, float]] | None:
    """Find a known city mentioned in free text. Returns (city_name, (lat, lon))."""
    if not text:
        return None
    lowered = text.lower()
    # longest names first so "toba tek singh" wins over shorter partial matches
    for city in sorted(CITY_COORDS, key=len, reverse=True):
        if city in lowered:
            return city.title(), CITY_COORDS[city]
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
