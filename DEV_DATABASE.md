# Development Database (dev.db)

This SQLite database contains pre-populated test data for local development without requiring TMDb API credentials.

## Contents

### Movies (5 total)
- **12 Angry Men** (1957) - Drama
- **The Godfather** (1972) - Drama, Crime
- **The Godfather Part II** (1974) - Drama, Crime
- **Schindler's List** (1993) - Drama, History, War
- **The Shawshank Redemption** (1994) - Drama, Crime

### Streaming Providers
- Netflix: The Shawshank Redemption, Schindler's List
- Amazon Prime Video: The Shawshank Redemption, 12 Angry Men
- Paramount Plus: The Godfather, The Godfather Part II

### Database Schema

#### watchlist_cache
- `id`: Primary key
- `account_id`: TMDb account identifier (use "dev_account" for test data)
- `data`: JSON array of movie objects
- `cached_at`: Timestamp of cache entry

#### providers_cache
- `movie_id`: Primary key (TMDb movie ID)
- `data`: JSON object with provider information by region
- `cached_at`: Timestamp of cache entry

#### movie_details_cache
- `movie_id`: Primary key (TMDb movie ID)
- `runtime`: Movie runtime in minutes
- `cached_at`: Timestamp of cache entry

## Usage

### Starting the App with Test Database

```bash
# Set environment variables
export DB_PATH=./dev.db
export TMDB_ACCOUNT_ID=dev_account

# Run the app
uv run python app.py
```

Or use the helper script:
```bash
./dev-server.sh
```

### Resetting the Database

If you need to reset the database to its initial state:

```bash
python3 init_dev_db.py
```

### Inspecting the Database

```bash
# View all tables
sqlite3 dev.db ".tables"

# View movie titles
sqlite3 dev.db "SELECT json_extract(value, '$.title') FROM watchlist_cache, json_each(json(data));"

# View provider cache
sqlite3 dev.db "SELECT movie_id, json_extract(data, '$.US.flatrate[0].provider_name') FROM providers_cache;"

# View runtimes
sqlite3 dev.db "SELECT movie_id, runtime FROM movie_details_cache;"
```

## Adding More Test Data

Edit `init_dev_db.py` and add more movies to the `test_movies`, `providers_data`, and `runtime_data` dictionaries, then run:

```bash
python3 init_dev_db.py
```

## Production vs Development

- **Production**: Uses `/app/flickstream_cache.db` inside Docker container
- **Development**: Uses `./dev.db` when `DB_PATH` environment variable is set
- The production database is excluded from git (see `.gitignore`)
- The dev database (`dev.db`) is committed to the repository for easy local development

## Notes

- Movie IDs are real TMDb movie IDs for consistency
- Poster paths are real TMDb paths that will work with the TMDb image API
- All movies use the US region for streaming providers
- Cache timestamps are set to the time when `init_dev_db.py` is run
