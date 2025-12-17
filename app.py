from flask import Flask, render_template, jsonify, request
import requests
import os
from functools import lru_cache
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# TMDb API configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '')
TMDB_ACCOUNT_ID = os.environ.get('TMDB_ACCOUNT_ID', '')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
# Authentication method: 'bearer' or 'api_key' (defaults to 'api_key')
TMDB_AUTH_METHOD = os.environ.get('TMDB_AUTH_METHOD', 'api_key').lower()

# Cache configuration (in hours)
WATCHLIST_CACHE_HOURS = int(os.environ.get('WATCHLIST_CACHE_HOURS', '6'))
PROVIDERS_CACHE_HOURS = int(os.environ.get('PROVIDERS_CACHE_HOURS', '24'))

# Streaming services configuration
# Set this in your .env file as a comma-separated list, e.g.:
# MY_STREAMING_SERVICES=Netflix,Amazon Prime Video,Disney Plus,Hulu
MY_STREAMING_SERVICES = os.environ.get('MY_STREAMING_SERVICES', '')

# User region for streaming providers (default: US)
USER_REGION = os.environ.get('USER_REGION', 'US')

# Database setup
DB_PATH = os.environ.get('DB_PATH', '/app/flickstream_cache.db')

def init_db():
    """Initialize the SQLite database for caching"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Watchlist cache table
        c.execute('''
            CREATE TABLE IF NOT EXISTS watchlist_cache (
                id INTEGER PRIMARY KEY,
                account_id TEXT NOT NULL,
                data TEXT NOT NULL,
                cached_at TIMESTAMP NOT NULL
            )
        ''')
        
        # Providers cache table
        c.execute('''
            CREATE TABLE IF NOT EXISTS providers_cache (
                movie_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL,
                cached_at TIMESTAMP NOT NULL
            )
        ''')
        
        # Movie details cache table (for runtime and other details)
        c.execute('''
            CREATE TABLE IF NOT EXISTS movie_details_cache (
                movie_id INTEGER PRIMARY KEY,
                runtime INTEGER,
                cached_at TIMESTAMP NOT NULL
            )
        ''')
        
        # Create index for faster lookups
        c.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_account ON watchlist_cache(account_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_providers_movie ON providers_cache(movie_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_details_movie ON movie_details_cache(movie_id)')
        
        conn.commit()
        conn.close()
        print(f"✓ Database initialized at {DB_PATH}")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        import traceback
        traceback.print_exc()

# Initialize database on startup
init_db()

def make_tmdb_request(endpoint, params=None):
    """
    Make a request to TMDb API with proper authentication.
    Supports both Bearer token and API key query parameter methods.
    
    Args:
        endpoint: The API endpoint (e.g., '/genre/movie/list')
        params: Optional query parameters dict
    
    Returns:
        requests.Response object
    """
    url = f'{TMDB_BASE_URL}{endpoint}'
    
    if params is None:
        params = {}
    
    if TMDB_AUTH_METHOD == 'bearer':
        # Use Bearer token in Authorization header
        headers = {'Authorization': f'Bearer {TMDB_API_KEY}'}
        return requests.get(url, headers=headers, params=params)
    else:
        # Use API key as query parameter (default)
        params['api_key'] = TMDB_API_KEY
        return requests.get(url, params=params)

@lru_cache(maxsize=1)
def get_all_genres():
    """Fetch all movie genres from TMDb"""
    try:
        response = make_tmdb_request('/genre/movie/list')
        response.raise_for_status()
        return {genre['id']: genre['name'] for genre in response.json()['genres']}
    except Exception as e:
        print(f"Error fetching genres: {e}")
        return {}

def get_cached_watchlist(account_id):
    """Get cached watchlist if available and not expired"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT data, cached_at FROM watchlist_cache 
        WHERE account_id = ? 
        ORDER BY cached_at DESC LIMIT 1
    ''', (account_id,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        cached_data, cached_at = row
        cached_time = datetime.fromisoformat(cached_at)
        expiry_time = cached_time + timedelta(hours=WATCHLIST_CACHE_HOURS)
        
        if datetime.now() < expiry_time:
            print(f"✓ Using cached watchlist (cached {cached_time.strftime('%Y-%m-%d %H:%M:%S')})")
            return json.loads(cached_data)
        else:
            print(f"✗ Cached watchlist expired (was from {cached_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    return None

def cache_watchlist(account_id, movies):
    """Store watchlist in cache"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Delete old cache for this account
    c.execute('DELETE FROM watchlist_cache WHERE account_id = ?', (account_id,))
    
    # Insert new cache
    c.execute('''
        INSERT INTO watchlist_cache (account_id, data, cached_at)
        VALUES (?, ?, ?)
    ''', (account_id, json.dumps(movies), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print(f"✓ Cached {len(movies)} movies for account {account_id}")

def get_cached_providers(movie_ids):
    """Get cached providers for multiple movies"""
    if not movie_ids:
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    placeholders = ','.join('?' * len(movie_ids))
    c.execute(f'''
        SELECT movie_id, data, cached_at FROM providers_cache 
        WHERE movie_id IN ({placeholders})
    ''', movie_ids)
    
    rows = c.fetchall()
    conn.close()
    
    cached_providers = {}
    expired_ids = []
    
    for movie_id, data, cached_at in rows:
        cached_time = datetime.fromisoformat(cached_at)
        expiry_time = cached_time + timedelta(hours=PROVIDERS_CACHE_HOURS)
        
        if datetime.now() < expiry_time:
            cached_providers[movie_id] = json.loads(data)
        else:
            expired_ids.append(movie_id)
    
    if cached_providers:
        print(f"✓ Using cached providers for {len(cached_providers)} movies")
    if expired_ids:
        print(f"✗ Expired provider cache for {len(expired_ids)} movies")
    
    return cached_providers

def cache_providers(providers_data):
    """Store provider data in cache"""
    if not providers_data:
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    now = datetime.now().isoformat()
    
    for movie_id, data in providers_data.items():
        # Upsert: delete old, insert new
        c.execute('DELETE FROM providers_cache WHERE movie_id = ?', (movie_id,))
        c.execute('''
            INSERT INTO providers_cache (movie_id, data, cached_at)
            VALUES (?, ?, ?)
        ''', (movie_id, json.dumps(data), now))
    
    conn.commit()
    conn.close()
    print(f"✓ Cached provider data for {len(providers_data)} movies")

def get_watchlist():
    """Fetch watchlist from TMDb (with caching)"""
    # Try cache first
    cached = get_cached_watchlist(TMDB_ACCOUNT_ID)
    if cached is not None:
        return cached
    
    # Cache miss - fetch from API
    try:
        movies = []
        page = 1
        
        print(f"Fetching watchlist from API for account: {TMDB_ACCOUNT_ID}")
        
        while True:
            response = make_tmdb_request(
                f'/account/{TMDB_ACCOUNT_ID}/watchlist/movies',
                params={'page': page, 'sort_by': 'created_at.desc'}
            )
            print(f"Watchlist API response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            print(f"Page {page}: Found {len(data['results'])} movies")
            movies.extend(data['results'])
            
            if page >= data['total_pages']:
                break
            page += 1
        
        print(f"Total movies fetched: {len(movies)}")
        
        # Cache the results
        cache_watchlist(TMDB_ACCOUNT_ID, movies)
        
        return movies
    except Exception as e:
        print(f"Error fetching watchlist: {e}")
        print(traceback.format_exc())
        return []

def get_watch_providers(movie_id):
    """Fetch streaming providers for a movie (with caching)"""
    # Check cache first
    cached = get_cached_providers([movie_id])
    if movie_id in cached:
        return cached[movie_id]
    
    # Cache miss - fetch from API
    try:
        response = make_tmdb_request(f'/movie/{movie_id}/watch/providers')
        response.raise_for_status()
        data = response.json().get('results', {})
        
        # Cache the result
        cache_providers({movie_id: data})
        
        return data
    except Exception as e:
        print(f"Error fetching providers for movie {movie_id}: {e}")
        return {}

def get_cached_movie_details(movie_ids):
    """Get cached movie details (runtime) for multiple movies"""
    if not movie_ids:
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    placeholders = ','.join('?' * len(movie_ids))
    c.execute(f'''
        SELECT movie_id, runtime, cached_at FROM movie_details_cache 
        WHERE movie_id IN ({placeholders})
    ''', movie_ids)
    
    rows = c.fetchall()
    conn.close()
    
    cached_details = {}
    expired_ids = []
    
    for movie_id, runtime, cached_at in rows:
        cached_time = datetime.fromisoformat(cached_at)
        expiry_time = cached_time + timedelta(hours=PROVIDERS_CACHE_HOURS)  # Same expiry as providers
        
        if datetime.now() < expiry_time:
            cached_details[movie_id] = {'runtime': runtime}
        else:
            expired_ids.append(movie_id)
    
    if cached_details:
        print(f"✓ Using cached runtime for {len(cached_details)} movies")
    if expired_ids:
        print(f"✗ Expired runtime cache for {len(expired_ids)} movies")
    
    return cached_details

def cache_movie_details(details_data):
    """Store movie details (runtime) in cache"""
    if not details_data:
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    now = datetime.now().isoformat()
    
    for movie_id, details in details_data.items():
        runtime = details.get('runtime')
        # Upsert: delete old, insert new
        c.execute('DELETE FROM movie_details_cache WHERE movie_id = ?', (movie_id,))
        c.execute('''
            INSERT INTO movie_details_cache (movie_id, runtime, cached_at)
            VALUES (?, ?, ?)
        ''', (movie_id, runtime, now))
    
    conn.commit()
    conn.close()
    print(f"✓ Cached runtime for {len(details_data)} movies")

def fetch_movie_details_from_api(movie_id):
    """Helper function to fetch movie details (runtime) from API"""
    try:
        response = make_tmdb_request(f'/movie/{movie_id}')
        response.raise_for_status()
        data = response.json()
        return {'runtime': data.get('runtime')}
    except Exception as e:
        print(f"Error fetching details for movie {movie_id}: {e}")
        return {'runtime': None}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/watchlist')
def api_watchlist():
    """API endpoint to fetch watchlist WITHOUT providers (fast)"""
    print("=== API Watchlist endpoint called (fast mode) ===")
    movies = get_watchlist()
    print(f"Retrieved {len(movies)} movies from watchlist")
    genres_map = get_all_genres()
    print(f"Retrieved {len(genres_map)} genres")
    
    # Return movies quickly without provider information
    enriched_movies = []
    for movie in movies:
        # Add genre names
        genre_names = [genres_map.get(gid, 'Unknown') for gid in movie.get('genre_ids', [])]
        
        enriched_movies.append({
            'id': movie['id'],
            'title': movie['title'],
            'overview': movie.get('overview', ''),
            'poster_path': movie.get('poster_path'),
            'backdrop_path': movie.get('backdrop_path'),
            'release_date': movie.get('release_date', ''),
            'vote_average': movie.get('vote_average', 0),
            'genre_ids': movie.get('genre_ids', []),
            'genres': genre_names,
            'providers': {}  # Empty, will be loaded separately
        })
    
    print(f"Returning {len(enriched_movies)} movies (without providers)")
    return jsonify(enriched_movies)

@app.route('/api/providers')
def api_providers():
    """API endpoint to fetch providers for multiple movies in parallel (with caching)"""
    movie_ids = request.args.get('ids', '')
    if not movie_ids:
        return jsonify({'error': 'No movie IDs provided'}), 400
    
    try:
        ids = [int(id.strip()) for id in movie_ids.split(',') if id.strip()]
    except ValueError:
        return jsonify({'error': 'Invalid movie IDs'}), 400
    
    # Check cache for all requested IDs
    cached_providers = get_cached_providers(ids)
    
    # Find which IDs need to be fetched from API
    missing_ids = [id for id in ids if id not in cached_providers]
    
    if missing_ids:
        print(f"Fetching providers for {len(missing_ids)} movies from API (in parallel)")
        
        # Fetch missing providers in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {executor.submit(fetch_provider_from_api, movie_id): movie_id 
                          for movie_id in missing_ids}
            
            new_providers = {}
            for future in as_completed(future_to_id):
                movie_id = future_to_id[future]
                try:
                    providers = future.result()
                    new_providers[movie_id] = providers
                except Exception as e:
                    print(f"Error fetching providers for movie {movie_id}: {e}")
                    new_providers[movie_id] = {}
        
        # Cache the newly fetched providers
        if new_providers:
            cache_providers(new_providers)
        
        # Combine cached and newly fetched
        providers_data = {**cached_providers, **new_providers}
    else:
        print(f"All {len(ids)} providers served from cache!")
        providers_data = cached_providers
    
    print(f"Returning providers for {len(providers_data)} movies")
    return jsonify(providers_data)

def fetch_provider_from_api(movie_id):
    """Helper function to fetch provider from API without caching (caching handled in api_providers)"""
    try:
        response = make_tmdb_request(f'/movie/{movie_id}/watch/providers')
        response.raise_for_status()
        return response.json().get('results', {})
    except Exception as e:
        print(f"Error fetching providers for movie {movie_id}: {e}")
        return {}

@app.route('/api/genres')
def api_genres():
    """API endpoint to fetch all genres"""
    genres_map = get_all_genres()
    genres_list = [{'id': gid, 'name': name} for gid, name in genres_map.items()]
    return jsonify(genres_list)

@app.route('/api/debug')
def api_debug():
    """Debug endpoint to check configuration and API connectivity"""
    debug_info = {
        'config': {
            'tmdb_api_key_set': bool(TMDB_API_KEY),
            'tmdb_api_key_length': len(TMDB_API_KEY) if TMDB_API_KEY else 0,
            'tmdb_account_id': TMDB_ACCOUNT_ID,
            'tmdb_account_id_set': bool(TMDB_ACCOUNT_ID),
            'auth_method': TMDB_AUTH_METHOD,
        },
        'tests': {}
    }
    
    # Test 1: Check if API key works
    try:
        response = make_tmdb_request('/genre/movie/list')
        debug_info['tests']['genres_api'] = {
            'status': response.status_code,
            'success': response.status_code == 200,
            'message': 'API key is valid' if response.status_code == 200 else f'API key issue: {response.text}'
        }
    except Exception as e:
        debug_info['tests']['genres_api'] = {
            'status': 'error',
            'success': False,
            'message': str(e)
        }
    
    # Test 2: Check if account ID works
    try:
        response = make_tmdb_request(
            f'/account/{TMDB_ACCOUNT_ID}/watchlist/movies',
            params={'page': 1}
        )
        data = response.json() if response.status_code == 200 else {}
        debug_info['tests']['watchlist_api'] = {
            'status': response.status_code,
            'success': response.status_code == 200,
            'total_results': data.get('total_results', 0),
            'total_pages': data.get('total_pages', 0),
            'movies_on_first_page': len(data.get('results', [])),
            'message': 'Watchlist accessible' if response.status_code == 200 else f'Watchlist error: {response.text}'
        }
    except Exception as e:
        debug_info['tests']['watchlist_api'] = {
            'status': 'error',
            'success': False,
            'message': str(e)
        }
    
    return jsonify(debug_info)

@app.route('/api/cache/clear')
def clear_cache():
    """Clear all cached data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM watchlist_cache')
        c.execute('DELETE FROM providers_cache')
        watchlist_deleted = c.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully',
            'rows_deleted': watchlist_deleted
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cache/stats')
def cache_stats():
    """Get cache statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*), MAX(cached_at) FROM watchlist_cache')
        watchlist_count, watchlist_latest = c.fetchone()
        
        c.execute('SELECT COUNT(*), MAX(cached_at) FROM providers_cache')
        providers_count, providers_latest = c.fetchone()
        
        conn.close()
        
        return jsonify({
            'watchlist': {
                'cached_entries': watchlist_count,
                'latest_cache': watchlist_latest,
                'cache_duration_hours': WATCHLIST_CACHE_HOURS
            },
            'providers': {
                'cached_entries': providers_count,
                'latest_cache': providers_latest,
                'cache_duration_hours': PROVIDERS_CACHE_HOURS
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/streaming-services')
def api_streaming_services():
    """
    API endpoint to get available streaming services.
    Returns configured services (marked as preferred) plus auto-discovered services.
    """
    configured_services = []
    if MY_STREAMING_SERVICES:
        configured_services = [s.strip() for s in MY_STREAMING_SERVICES.split(',') if s.strip()]
        print(f"✓ Configured streaming services: {configured_services}")
    
    # Always auto-discover from cached provider data
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get all cached provider data
        c.execute('SELECT data FROM providers_cache')
        rows = c.fetchall()
        conn.close()
        
        # Extract unique streaming service names for the user's region
        services_set = set()
        for (data,) in rows:
            providers = json.loads(data)
            region_data = providers.get(USER_REGION, {})
            
            # Get flatrate (subscription) providers
            if 'flatrate' in region_data:
                for provider in region_data['flatrate']:
                    services_set.add(provider['provider_name'])
        
        discovered_services = sorted(list(services_set))
        
        # Combine: use configured services if available, otherwise use discovered
        if configured_services:
            # Add discovered services that aren't in the configured list
            all_services = configured_services.copy()
            for service in discovered_services:
                if service not in all_services:
                    all_services.append(service)
            
            print(f"✓ Returning {len(configured_services)} preferred + {len(all_services) - len(configured_services)} discovered services")
            
            return jsonify({
                'services': all_services,
                'preferred': configured_services,
                'region': USER_REGION,
                'source': 'configured'
            })
        else:
            # No configured services, return all discovered
            if discovered_services:
                print(f"✓ Auto-discovered {len(discovered_services)} streaming services from watchlist")
            else:
                print("ℹ No streaming services found yet - providers may not be cached yet")
            
            return jsonify({
                'services': discovered_services,
                'preferred': [],
                'region': USER_REGION,
                'source': 'auto-discovered'
            })
        
    except Exception as e:
        print(f"Error discovering streaming services: {e}")
        # Return configured services or fallback
        if configured_services:
            return jsonify({
                'services': configured_services,
                'preferred': configured_services,
                'region': USER_REGION,
                'source': 'configured'
            })
        else:
            return jsonify({
                'services': [
                    'Netflix', 'Amazon Prime Video', 'Disney Plus', 'Hulu',
                    'HBO Max', 'Apple TV Plus', 'Paramount Plus', 'Peacock'
                ],
                'preferred': [],
                'region': USER_REGION,
                'source': 'fallback'
            })

@app.route('/api/movie-details')
def api_movie_details():
    """API endpoint to fetch movie details (runtime) for multiple movies in parallel (with caching)"""
    movie_ids = request.args.get('ids', '')
    if not movie_ids:
        return jsonify({'error': 'No movie IDs provided'}), 400
    
    try:
        ids = [int(id.strip()) for id in movie_ids.split(',') if id.strip()]
    except ValueError:
        return jsonify({'error': 'Invalid movie IDs'}), 400
    
    # Check cache for all requested IDs
    cached_details = get_cached_movie_details(ids)
    
    # Find which IDs need to be fetched from API
    missing_ids = [id for id in ids if id not in cached_details]
    
    if missing_ids:
        print(f"Fetching runtime for {len(missing_ids)} movies from API (in parallel)")
        
        # Fetch missing details in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {executor.submit(fetch_movie_details_from_api, movie_id): movie_id 
                          for movie_id in missing_ids}
            
            new_details = {}
            for future in as_completed(future_to_id):
                movie_id = future_to_id[future]
                try:
                    details = future.result()
                    new_details[movie_id] = details
                except Exception as e:
                    print(f"Error fetching details for movie {movie_id}: {e}")
                    new_details[movie_id] = {'runtime': None}
        
        # Cache the newly fetched details
        if new_details:
            cache_movie_details(new_details)
        
        # Combine cached and newly fetched
        details_data = {**cached_details, **new_details}
    else:
        print(f"All {len(ids)} movie details served from cache!")
        details_data = cached_details
    
    print(f"Returning details for {len(details_data)} movies")
    return jsonify(details_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
