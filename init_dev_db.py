#!/usr/bin/env python3
"""
Initialize dev.db with test data for local development.
Run this script to reset the development database to its initial state.
"""

import sqlite3
import json
from datetime import datetime

def init_dev_db():
    """Initialize dev.db with test data"""
    # Connect to dev.db
    conn = sqlite3.connect('dev.db')
    c = conn.cursor()

    print("🔧 Initializing dev.db...")

    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS watchlist_cache (
            id INTEGER PRIMARY KEY,
            account_id TEXT NOT NULL,
            data TEXT NOT NULL,
            cached_at TIMESTAMP NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS providers_cache (
            movie_id INTEGER PRIMARY KEY,
            data TEXT NOT NULL,
            cached_at TIMESTAMP NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS movie_details_cache (
            movie_id INTEGER PRIMARY KEY,
            runtime INTEGER,
            cached_at TIMESTAMP NOT NULL
        )
    ''')

    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_account ON watchlist_cache(account_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_providers_movie ON providers_cache(movie_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_details_movie ON movie_details_cache(movie_id)')

    # Insert test data
    now = datetime.now().isoformat()

    # Sample watchlist data - classic highly-rated movies
    test_movies = [
        {
            "id": 278,
            "title": "The Shawshank Redemption",
            "genre_ids": [18, 80],
            "genres": ["Drama", "Crime"],
            "release_date": "1994-09-23",
            "vote_average": 8.7,
            "poster_path": "/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg"
        },
        {
            "id": 238,
            "title": "The Godfather",
            "genre_ids": [18, 80],
            "genres": ["Drama", "Crime"],
            "release_date": "1972-03-14",
            "vote_average": 8.7,
            "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg"
        },
        {
            "id": 240,
            "title": "The Godfather Part II",
            "genre_ids": [18, 80],
            "genres": ["Drama", "Crime"],
            "release_date": "1974-12-20",
            "vote_average": 8.6,
            "poster_path": "/hek3koDUyRQk7FIhPXsa6mT2Zc3.jpg"
        },
        {
            "id": 424,
            "title": "Schindler's List",
            "genre_ids": [18, 36, 10752],
            "genres": ["Drama", "History", "War"],
            "release_date": "1993-12-15",
            "vote_average": 8.6,
            "poster_path": "/sF1U4EUQS8YHUYjNl3pMGNIQyr0.jpg"
        },
        {
            "id": 389,
            "title": "12 Angry Men",
            "genre_ids": [18],
            "genres": ["Drama"],
            "release_date": "1957-04-10",
            "vote_average": 8.5,
            "poster_path": "/ow3wq89wM8qd5X7hWKxiRfsFf9C.jpg"
        }
    ]

    # Clear existing data
    c.execute('DELETE FROM watchlist_cache WHERE account_id = ?', ('dev_account',))
    c.execute('DELETE FROM providers_cache')
    c.execute('DELETE FROM movie_details_cache')

    # Insert watchlist
    c.execute('''
        INSERT INTO watchlist_cache (account_id, data, cached_at)
        VALUES (?, ?, ?)
    ''', ('dev_account', json.dumps(test_movies), now))

    # Insert provider data
    providers_data = {
        278: {"US": {"flatrate": [{"provider_name": "Netflix"}, {"provider_name": "Amazon Prime Video"}]}},
        238: {"US": {"flatrate": [{"provider_name": "Paramount Plus"}]}},
        240: {"US": {"flatrate": [{"provider_name": "Paramount Plus"}]}},
        424: {"US": {"flatrate": [{"provider_name": "Netflix"}]}},
        389: {"US": {"flatrate": [{"provider_name": "Amazon Prime Video"}]}}
    }

    for movie_id, data in providers_data.items():
        c.execute('''
            INSERT INTO providers_cache (movie_id, data, cached_at)
            VALUES (?, ?, ?)
        ''', (movie_id, json.dumps(data), now))

    # Insert runtime data
    runtime_data = {
        278: 142,
        238: 175,
        240: 202,
        424: 195,
        389: 96
    }

    for movie_id, runtime in runtime_data.items():
        c.execute('''
            INSERT INTO movie_details_cache (movie_id, runtime, cached_at)
            VALUES (?, ?, ?)
        ''', (movie_id, runtime, now))

    conn.commit()
    conn.close()

    print("✓ dev.db initialized successfully!")
    print(f"  📽️  {len(test_movies)} movies in watchlist")
    print(f"  📺 {len(providers_data)} movies with provider data")
    print(f"  ⏱️  {len(runtime_data)} movies with runtime data")
    print("\n💡 To use this database:")
    print("   export DB_PATH=./dev.db")
    print("   export TMDB_ACCOUNT_ID=dev_account")
    print("   uv run python app.py")

if __name__ == "__main__":
    init_dev_db()
