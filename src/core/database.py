import sqlite3
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_NAME = str(BASE_DIR / "cinemate.db")

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Movies table to cache movie/tv details
    # We add media_type. Primary key is still id, which is risky if collision, 
    # but for simplicity we'll assume no collision or handle it later.
    # Ideally PK should be (id, media_type).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER,
            title TEXT NOT NULL,
            genre TEXT,
            release_date TEXT,
            overview TEXT,
            media_type TEXT DEFAULT 'movie',
            PRIMARY KEY (id, media_type)
        )
    ''')
    
    # History table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            media_type TEXT DEFAULT 'movie',
            rating INTEGER,
            review TEXT,
            watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Watchlist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            media_type TEXT DEFAULT 'movie',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration: Check if media_type exists in movies, if not add it
    try:
        cursor.execute('SELECT media_type FROM movies LIMIT 1')
    except Exception:
        print("Migrating database: Adding media_type columns...")
        try:
            cursor.execute('ALTER TABLE movies ADD COLUMN media_type TEXT DEFAULT "movie"')
            cursor.execute('ALTER TABLE history ADD COLUMN media_type TEXT DEFAULT "movie"')
            cursor.execute('ALTER TABLE watchlist ADD COLUMN media_type TEXT DEFAULT "movie"')
        except Exception as e:
            print(f"Migration warning: {e}")

    conn.commit()
    conn.close()

def add_movie_cache(movie_id: int, title: str, genre: str, release_date: str, overview: str, media_type: str = "movie"):
    """Cache movie details to avoid repeated API calls."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO movies (id, title, genre, release_date, overview, media_type)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (movie_id, title, genre, release_date, overview, media_type))
    conn.commit()
    conn.close()

def add_to_history(movie_id: int, rating: int, review: str, media_type: str = "movie"):
    conn = get_connection()
    cursor = conn.cursor()
    # Remove existing entry for this movie to avoid duplicates
    cursor.execute('DELETE FROM history WHERE movie_id = ? AND media_type = ?', (movie_id, media_type))
    
    cursor.execute('''
        INSERT INTO history (movie_id, rating, review, media_type)
        VALUES (?, ?, ?, ?)
    ''', (movie_id, rating, review, media_type))
    conn.commit()
    conn.close()

def delete_from_history(movie_id: int, media_type: str = "movie"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM history WHERE movie_id = ? AND media_type = ?', (movie_id, media_type))
    conn.commit()
    conn.close()

def add_to_watchlist(movie_id: int, media_type: str = "movie"):
    conn = get_connection()
    cursor = conn.cursor()
    # Check if already in watchlist
    cursor.execute('SELECT id FROM watchlist WHERE movie_id = ? AND media_type = ?', (movie_id, media_type))
    if cursor.fetchone():
        conn.close()
        return False
        
    cursor.execute('''
        INSERT INTO watchlist (movie_id, media_type)
        VALUES (?, ?)
    ''', (movie_id, media_type))
    conn.commit()
    conn.close()
    return True

def remove_from_watchlist(movie_id: int, media_type: str = "movie"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM watchlist WHERE movie_id = ? AND media_type = ?', (movie_id, media_type))
    conn.commit()
    conn.close()

def get_history() -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.title, h.rating, h.review, h.watched_at, h.media_type
        FROM history h
        LEFT JOIN movies m ON h.movie_id = m.id AND h.media_type = m.media_type
        ORDER BY h.watched_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_watchlist() -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.title, m.genre, m.release_date, w.added_at, w.media_type
        FROM watchlist w
        LEFT JOIN movies m ON w.movie_id = m.id AND w.media_type = m.media_type
        ORDER BY w.added_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_history():
    """Clear all entries from watch history."""
    conn = get_connection()
    conn.execute("DELETE FROM history")
    conn.commit()
    conn.close()

def clear_watchlist():
    """Clear all entries from watchlist."""
    conn = get_connection()
    conn.execute("DELETE FROM watchlist")
    conn.commit()
    conn.close()

def get_user_stats() -> Dict[str, Any]:
    """Calculate user viewing statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # 1. Total watched
    cursor.execute('SELECT COUNT(*) FROM history')
    stats['total_watched'] = cursor.fetchone()[0]
    
    # 2. Average rating given
    cursor.execute('SELECT AVG(rating) FROM history')
    avg_rating = cursor.fetchone()[0]
    stats['avg_rating'] = round(avg_rating, 1) if avg_rating else 0
    
    # 3. Favorite Genre
    cursor.execute('''
        SELECT m.genre 
        FROM history h
        JOIN movies m ON h.movie_id = m.id AND h.media_type = m.media_type
    ''')
    rows = cursor.fetchall()
    
    from collections import Counter
    
    all_genre_ids = []
    for r in rows:
        if r[0]:
            ids = [x.strip() for x in r[0].split(",") if x.strip().isdigit()]
            all_genre_ids.extend(ids)
            
    if all_genre_ids:
        most_common = Counter(all_genre_ids).most_common(1)
        stats['favorite_genre_id'] = int(most_common[0][0])
        stats['favorite_genre_count'] = most_common[0][1]
    else:
        stats['favorite_genre_id'] = None
        stats['favorite_genre_count'] = 0
        
    conn.close()
    return stats

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
