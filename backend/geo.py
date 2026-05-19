"""Geolocation utilities for ArtLocal."""

import math


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in miles between two lat/lng points."""
    R = 3958.8  # Earth radius in miles

    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
