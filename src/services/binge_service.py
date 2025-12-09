import math
import datetime
from services import movie_service
from services import calendar_service
import dateparser
from tzlocal import get_localzone_name

async def plan_and_schedule_binge(title: str, episodes_per_day: int, start_time_str: str) -> str:
    """
    Core logic for calculating and scheduling a binge plan.
    """
    # 1. Find the show
    results = await movie_service.search_movies(title)
    tv_results = [r for r in results if r.get('media_type') == 'tv']
    
    if not tv_results:
        if results:
            return f"Found '{results[0].get('title')}' but it seems to be a movie. Binge calculator is for TV shows."
        return f"Could not find TV show '{title}'."
        
    show = tv_results[0]
    show_id = show['id']
    show_name = show['name']
    
    # 2. Get details
    details = await movie_service.get_movie_details(show_id, "tv")
    total_episodes = details.get('number_of_episodes', 0)
    runtimes = details.get('episode_run_time', [])
    avg_runtime = runtimes[0] if runtimes else 45
    
    if total_episodes == 0:
        return f"Could not determine episode count for '{show_name}'."
        
    # 3. Calculate Plan
    days_needed = math.ceil(total_episodes / episodes_per_day)
    daily_duration = avg_runtime * episodes_per_day
    
    # 4. Parse Start Time
    local_tz = get_localzone_name()
    start_time = dateparser.parse(
        start_time_str, 
        settings={'PREFER_DATES_FROM': 'future', 'TIMEZONE': local_tz, 'RETURN_AS_TIMEZONE_AWARE': True}
    )
    
    if not start_time:
        return f"Could not parse start time '{start_time_str}'."
        
    # 5. Schedule Events
    max_sessions = 14
    sessions_to_schedule = min(days_needed, max_sessions)
    
    current_time = start_time
    ep_counter = 1
    
    for day in range(sessions_to_schedule):
        end_ep = min(ep_counter + episodes_per_day - 1, total_episodes)
        
        summary = f"Binge {show_name} (Day {day+1}/{days_needed})"
        description = f"Watching episodes {ep_counter}-{end_ep}.\nTotal progress: {end_ep}/{total_episodes} episodes."
        
        calendar_service.create_event(
            summary=summary,
            description=description,
            start_time=current_time,
            duration_minutes=daily_duration
        )
        
        current_time += datetime.timedelta(days=1)
        ep_counter += episodes_per_day
        
    response = f"🎬 **Binge Plan for {show_name}**\n"
    response += f"- Total Episodes: {total_episodes}\n"
    response += f"- Estimated Time: {days_needed} days (@ {episodes_per_day} eps/day)\n"
    response += f"- Scheduled: First {sessions_to_schedule} sessions starting {start_time.strftime('%Y-%m-%d %H:%M')}.\n"
    if days_needed > max_sessions:
        response += f"*(Note: Only scheduled first {max_sessions} days to avoid calendar spam)*"
        
    return response

async def cancel_binge_plan(title: str) -> str:
    """
    Cancel (delete) all binge-watching sessions for a TV show.
    """
    # 1. Find the show to get exact name
    results = await movie_service.search_movies(title)
    tv_results = [r for r in results if r.get('media_type') == 'tv']
    
    if not tv_results:
        # Try searching for events directly with the query if show not found
        show_name = title
    else:
        show_name = tv_results[0]['name']
        
    # 2. Find events
    # Binge events are named "Binge {ShowName} (Day X/Y)"
    query = f"Binge {show_name}"
    events = calendar_service.list_events(query=query, max_results=50)
    
    if not events:
        return f"Could not find any binge sessions for '{show_name}'."
        
    # 3. Delete all
    count = 0
    for event in events:
        if show_name.lower() in event.get('summary', '').lower():
            calendar_service.delete_event(event['id'])
            count += 1
            
    return f"Cancelled (deleted) {count} binge sessions for '{show_name}'."
