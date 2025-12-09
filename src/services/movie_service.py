import os
import httpx
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from core import database
import socket
from unittest.mock import patch
import contextlib

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

if not TMDB_API_KEY:
    print("Warning: TMDB_API_KEY not found in environment variables.")


async def get_tmdb_ip() -> Optional[str]:
    """Resolve TMDB IP using Google DNS-over-HTTPS to bypass ISP blocks."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://dns.google/resolve",
                params={"name": "api.themoviedb.org", "type": "A"}
            )
            data = resp.json()
            if "Answer" in data:
                return data["Answer"][0]["data"]
    except Exception as e:
        print(f"DNS-over-HTTPS failed: {e}")
    return None

# Global cache for the IP
_TMDB_IP: Optional[str] = None

@contextlib.asynccontextmanager
async def dns_bypass():
    """Context manager to patch DNS resolution for TMDB."""
    global _TMDB_IP
    if not _TMDB_IP:
        _TMDB_IP = await get_tmdb_ip()
    
    if not _TMDB_IP:
        yield
        return

    original_getaddrinfo = socket.getaddrinfo
    
    def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # Handle both str and bytes
        if host == "api.themoviedb.org" or host == b"api.themoviedb.org":
            # print(f"Redirecting {host} to {_TMDB_IP}")
            return original_getaddrinfo(_TMDB_IP, port, family, type, proto, flags)
        return original_getaddrinfo(host, port, family, type, proto, flags)
        
    with patch("socket.getaddrinfo", side_effect=new_getaddrinfo):
        yield

async def make_request(endpoint: str, params: dict) -> Dict[str, Any]:
    url = f"{BASE_URL}{endpoint}"
    
    # Use the DNS bypass context manager
    async with dns_bypass():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

async def search_movies(query: str) -> List[Dict[str, Any]]:
    """Search for movies and TV shows by title."""
    if not TMDB_API_KEY:
        return []
    
    try:
        data = await make_request("/search/multi", {"api_key": TMDB_API_KEY, "query": query, "language": "en-US", "page": 1})
        results = data.get("results", [])
        
        # Filter out people, only keep movie and tv
        filtered_results = [r for r in results if r.get("media_type") in ["movie", "tv"]]
        
        # Cache results
        for item in filtered_results:
            title = item.get("title") if item.get("media_type") == "movie" else item.get("name")
            release_date = item.get("release_date") if item.get("media_type") == "movie" else item.get("first_air_date")
            
            database.add_movie_cache(
                item["id"],
                title or "Unknown",
                ", ".join([str(g) for g in (item.get("genre_ids") or [])]),
                release_date or "",
                item.get("overview", ""),
                item.get("media_type", "movie")
            )
        return filtered_results
    except Exception as e:
        print(f"Search failed: {e}")
        return []

async def get_movie_details(movie_id: int, media_type: str = "movie") -> Dict[str, Any]:
    """Get detailed information about a specific movie or TV show."""
    if not TMDB_API_KEY:
        return {}
        
    try:
        return await make_request(f"/{media_type}/{movie_id}", {"api_key": TMDB_API_KEY, "language": "en-US"})
    except Exception:
        return {}

async def get_genres() -> Dict[int, str]:
    """Fetch genre list to map IDs to names (combines Movie and TV genres)."""
    if not TMDB_API_KEY:
        return {}
        
    try:
        resp_movie = await make_request("/genre/movie/list", {"api_key": TMDB_API_KEY, "language": "en-US"})
        resp_tv = await make_request("/genre/tv/list", {"api_key": TMDB_API_KEY, "language": "en-US"})
        
        genres = {}
        for g in resp_movie.get("genres", []):
            genres[g["id"]] = g["name"]
        for g in resp_tv.get("genres", []):
            genres[g["id"]] = g["name"]
            
        return genres
    except Exception:
        return {}

async def get_watch_providers(movie_id: int, country_code: str = "US", media_type: str = "movie") -> Dict[str, Any]:
    """Get streaming and rental providers for a movie or TV show."""
    if not TMDB_API_KEY:
        return {}

    try:
        data = await make_request(f"/{media_type}/{movie_id}/watch/providers", {"api_key": TMDB_API_KEY})
        results = data.get("results", {})
        return results.get(country_code, {})
    except Exception:
        return {}
