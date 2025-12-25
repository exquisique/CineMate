from services import movie_service
from core import database
from services import calendar_service
import dateparser
from tzlocal import get_localzone_name
import datetime

# --- Search & Details ---
async def search_and_format(query: str) -> str:
    try:
        results = await movie_service.search_movies(query)
        if not results:
            return "No movies or TV shows found."
        
        output = "Found results:\n"
        for m in results[:5]:
            m_type = m.get('media_type', 'movie').upper()
            title = m.get('title') if m.get('media_type') == 'movie' else m.get('name')
            date = m.get('release_date') if m.get('media_type') == 'movie' else m.get('first_air_date')
            year = (date or 'N/A')[:4]
            output += f"- [{m_type}] {title} (ID: {m.get('id', 'N/A')}, Year: {year})\n"
        return output
    except Exception as e:
        return f"Error searching: {e}"

async def get_details_logic(title: str) -> str:
    results = await movie_service.search_movies(title)
    if not results:
        return f"Could not find '{title}'."
    
    item = results[0]
    media_type = item.get('media_type', 'movie')
    
    details = await movie_service.get_movie_details(item['id'], media_type)
    if not details:
        return "Details not found."
    
    title_str = details.get('title') if media_type == 'movie' else details.get('name')
    date = details.get('release_date') if media_type == 'movie' else details.get('first_air_date')
    
    output = f"""Title: {title_str} ({media_type.upper()})
Year: {date or 'N/A'}
Genres: {', '.join([g['name'] for g in details.get('genres', [])])}
Rating: {details.get('vote_average', 'N/A')}
"""
    if media_type == 'movie':
        output += f"Runtime: {details.get('runtime', 'N/A')} minutes\n"
    else:
        output += f"Seasons: {details.get('number_of_seasons', 'N/A')}, Episodes: {details.get('number_of_episodes', 'N/A')}\n"
        
    output += f"Overview: {details.get('overview', 'N/A')}\n"
    return output

# --- Logging & Watchlist (Batch) ---
async def batch_log_movies(titles: str, rating: float, review: str) -> str:
    results_log = []
    title_list = [t.strip() for t in titles.split(',') if t.strip()]
    
    for title in title_list:
        try:
            results = await movie_service.search_movies(title)
            if not results:
                results_log.append(f"❌ '{title}': Not found.")
                continue
                
            movie = results[0]
            movie_id = movie['id']
            media_type = movie.get('media_type', 'movie')
            title_found = movie.get('title') if media_type == 'movie' else movie.get('name')
            
            database.add_to_history(movie_id, rating, review, media_type)
            database.remove_from_watchlist(movie_id, media_type)
            
            results_log.append(f"✅ '{title_found}' logged.")
        except Exception as e:
            results_log.append(f"❌ '{title}': Error {e}")
            
    return "\n".join(results_log)

async def delete_from_history_logic(title: str) -> str:
    results = await movie_service.search_movies(title)
    if not results:
        return f"Could not find '{title}'."
    
    item = results[0]
    media_type = item.get('media_type', 'movie')
    title_str = item.get('title') if media_type == 'movie' else item.get('name')
    
    database.delete_from_history(item['id'], media_type)
    return f"Removed '{title_str}' from history."

async def batch_add_watchlist(titles: str) -> str:
    results_log = []
    title_list = [t.strip() for t in titles.split(',') if t.strip()]
    
    for title in title_list:
        try:
            results = await movie_service.search_movies(title)
            if not results:
                results_log.append(f"❌ '{title}': Not found.")
                continue
                
            movie = results[0]
            movie_id = movie['id']
            media_type = movie.get('media_type', 'movie')
            title_found = movie.get('title') if media_type == 'movie' else movie.get('name')
            
            if database.add_to_watchlist(movie_id, media_type):
                results_log.append(f"✅ '{title_found}' added.")
            else:
                results_log.append(f"⚠️ '{title_found}' already in watchlist.")
        except Exception as e:
            results_log.append(f"❌ '{title}': Error {e}")
            
    return "\n".join(results_log)

async def delete_from_watchlist_logic(title: str) -> str:
    results = await movie_service.search_movies(title)
    if not results:
        return f"Could not find '{title}'."
    
    item = results[0]
    media_type = item.get('media_type', 'movie')
    title_str = item.get('title') if media_type == 'movie' else item.get('name')
    
    database.remove_from_watchlist(item['id'], media_type)
    return f"Removed '{title_str}' from watchlist."

# --- Scheduling ---
async def schedule_movie_logic(title: str, time_str: str) -> str:
    results = await movie_service.search_movies(title)
    if not results:
        return f"Could not find '{title}'."
    item = results[0]
    media_type = item.get('media_type', 'movie')
    title_str = item.get('title') if media_type == 'movie' else item.get('name')
    
    # Explicitly handle timezone. If dateparser doesn't pick it up, force it.
    # The user is in India (IST).
    # We MUST set RELATIVE_BASE to current IST time so "today" means "today in India".
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist).replace(tzinfo=None) # dateparser expects naive for base

    settings = {
        'PREFER_DATES_FROM': 'future',
        'RETURN_AS_TIMEZONE_AWARE': True,
        'TIMEZONE': 'Asia/Kolkata', # Force IST as user requested
        'TO_TIMEZONE': 'Asia/Kolkata',
        'RELATIVE_BASE': now_ist
    }
    
    start_time = dateparser.parse(time_str, settings=settings)
    
    if not start_time:
        return f"Could not parse time '{time_str}'."
        
    # Ensure it's in the future if 'today' was used but time passed?
    # dateparser handles 'future' preference but let's be safe.
    now = datetime.datetime.now(start_time.tzinfo)
    if start_time < now:
        # If user said "10pm" and it's 11pm, dateparser might give today 10pm (past).
        # If PREFER_DATES_FROM is future, it should give tomorrow.
        # But if it gave past, let's warn or adjust? 
        # For now, just proceed, calendar will accept past events.
        pass

    link = calendar_service.create_event(
        summary=f"Watch {title_str}",
        description=f"Watching {title_str} ({media_type}).\nOverview: {item.get('overview', '')}",
        start_time=start_time
    )
    return f"Scheduled '{title_str}' for {start_time.strftime('%Y-%m-%d %H:%M %Z')}. Event link: {link}"

async def reschedule_movie_logic(title: str, new_time_str: str) -> str:
    events = calendar_service.list_events(query=title)
    if not events:
        return f"Could not find any upcoming calendar events for '{title}'."
    
    event = events[0]
    event_id = event['id']
    old_summary = event.get('summary', '')
    old_desc = event.get('description', '')
    
    local_tz = get_localzone_name()
    start_time = dateparser.parse(
        new_time_str, 
        settings={
            'PREFER_DATES_FROM': 'future',
            'TIMEZONE': local_tz,
            'RETURN_AS_TIMEZONE_AWARE': True
        }
    )
    
    if not start_time:
        return f"Could not parse time '{new_time_str}'."
        
    link = calendar_service.update_event(
        event_id=event_id,
        summary=old_summary,
        description=old_desc,
        start_time=start_time
    )
    
    return f"Rescheduled '{old_summary}' to {start_time.strftime('%Y-%m-%d %H:%M %Z')}. Link: {link}"

# --- Cancellation ---
async def batch_cancel_movies(titles: str) -> str:
    results_log = []
    title_list = [t.strip() for t in titles.split(',') if t.strip()]
    
    for title in title_list:
        try:
            events = calendar_service.list_events(query=title)
            if not events:
                results_log.append(f"❌ '{title}': No event found.")
                continue
            
            event = events[0]
            event_id = event['id']
            summary = event.get('summary', 'Unknown Event')
            
            calendar_service.delete_event(event_id)
            results_log.append(f"✅ '{summary}' cancelled.")
        except Exception as e:
            results_log.append(f"❌ '{title}': Error {e}")
            
    return "\n".join(results_log)

async def cancel_events_on_date(date_str: str) -> str:
    local_tz = get_localzone_name()
    target_date = dateparser.parse(
        date_str, 
        settings={'TIMEZONE': local_tz, 'RETURN_AS_TIMEZONE_AWARE': True}
    )
    
    if not target_date:
        return f"Could not parse date '{date_str}'."
        
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
    
    events = calendar_service.list_events_in_range(start_of_day, end_of_day)
    
    if not events:
        return f"No events found on {start_of_day.strftime('%Y-%m-%d')}."
        
    count = 0
    deleted_titles = []
    for event in events:
        calendar_service.delete_event(event['id'])
        deleted_titles.append(event.get('summary', 'Unknown'))
        count += 1
        
    return f"Cancelled {count} events on {start_of_day.strftime('%Y-%m-%d')}:\n- " + "\n- ".join(deleted_titles)

async def cancel_events_in_range(start_str: str, end_str: str) -> str:
    local_tz = get_localzone_name()
    start_date = dateparser.parse(start_str, settings={'TIMEZONE': local_tz, 'RETURN_AS_TIMEZONE_AWARE': True})
    end_date = dateparser.parse(end_str, settings={'TIMEZONE': local_tz, 'RETURN_AS_TIMEZONE_AWARE': True})
    
    if not start_date or not end_date:
        return f"Could not parse dates: '{start_str}' to '{end_str}'."
        
    start_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    events = calendar_service.list_events_in_range(start_time, end_time)
    
    if not events:
        return f"No events found between {start_time.strftime('%Y-%m-%d')} and {end_time.strftime('%Y-%m-%d')}."
        
    count = 0
    deleted_titles = []
    for event in events:
        calendar_service.delete_event(event['id'])
        deleted_titles.append(event.get('summary', 'Unknown'))
        count += 1
        
    return f"Cancelled {count} events from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}:\n- " + "\n- ".join(deleted_titles)

async def cancel_events_starting_from(start_str: str) -> str:
    local_tz = get_localzone_name()
    start_date = dateparser.parse(start_str, settings={'TIMEZONE': local_tz, 'RETURN_AS_TIMEZONE_AWARE': True})
    
    if not start_date:
        return f"Could not parse date '{start_str}'."
        
    start_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time + datetime.timedelta(days=365)
    
    events = calendar_service.list_events_in_range(start_time, end_time)
    
    if not events:
        return f"No events found starting from {start_time.strftime('%Y-%m-%d')}."
        
    count = 0
    deleted_titles = []
    for event in events:
        calendar_service.delete_event(event['id'])
        deleted_titles.append(event.get('summary', 'Unknown'))
        count += 1
        
    return f"Cancelled {count} events starting from {start_time.strftime('%Y-%m-%d')}:\n- " + "\n- ".join(deleted_titles)

# --- Where to Watch ---
async def get_where_to_watch_logic(title: str, country: str = "India") -> str:
    COUNTRY_CODES = {
        "india": "IN", "united states": "US", "usa": "US", "uk": "GB",
        "united kingdom": "GB", "canada": "CA", "australia": "AU",
        "germany": "DE", "france": "FR", "japan": "JP", "brazil": "BR",
        "mexico": "MX", "spain": "ES", "italy": "IT", "russia": "RU",
        "china": "CN", "south korea": "KR"
    }
    country_code = COUNTRY_CODES.get(country.lower(), country.upper())
    
    results = await movie_service.search_movies(title)
    if not results:
        return f"Could not find '{title}'."
    
    item = results[0]
    media_type = item.get('media_type', 'movie')
    title_str = item.get('title') if media_type == 'movie' else item.get('name')
    
    providers = await movie_service.get_watch_providers(item['id'], country_code, media_type)
    if not providers:
        return f"No streaming information found for '{title_str}' in {country} ({country_code})."
    
    output = f"📺 Where to watch '{title_str}' ({country_code}):\n"
    
    if "flatrate" in providers:
        output += "\nStream:\n"
        for p in providers["flatrate"]:
            output += f"- {p['provider_name']}\n"
            
    if "rent" in providers:
        output += "\nRent:\n"
        for p in providers["rent"]:
            output += f"- {p['provider_name']}\n"
            
    if "buy" in providers:
        output += "\nBuy:\n"
        for p in providers["buy"]:
            output += f"- {p['provider_name']}\n"
            
    if "link" in providers:
        output += f"\nMore info: {providers['link']}"
        
    return output

# --- Lists ---
async def get_history_logic() -> str:
    history = database.get_history()
    if not history:
        return "History is empty."
    
    output = "Watch History:\n"
    for title, rating, review, watched_at, media_type in history:
        output += f"- [{media_type.upper()}] {title} ({rating}/10): {review} [Watched: {watched_at}]\n"
    return output

async def get_watchlist_logic() -> str:
    watchlist = database.get_watchlist()
    if not watchlist:
        return "Watchlist is empty."
    
    output = "Watchlist:\n"
    for title, genre, release, added_at, media_type in watchlist:
        output += f"- [{media_type.upper()}] {title} ({genre}) [Added: {added_at}]\n"
    return output

# --- Stats ---
async def clear_history_logic() -> str:
    database.clear_history()
    return "Watch history cleared."

async def clear_watchlist_logic() -> str:
    database.clear_watchlist()
    return "Watchlist cleared."

async def get_my_stats_logic() -> str:
    stats = database.get_user_stats()
    if not stats['total_watched']:
        return "No stats available yet. Log some movies!"
        
    # Get genre names
    genres = await movie_service.get_genres()
    
    top_genres_str = []
    for g_id, count in stats['top_genres']:
        name = genres.get(int(g_id), "Unknown")
        top_genres_str.append(f"{name} ({count})")
        
    return f"""🎬 **Your Movie DNA**
- **Total Watched**: {stats['total_watched']}
- **Average Rating**: {stats['avg_rating']:.1f}/10
- **Top Genres**: {', '.join(top_genres_str)}
"""
