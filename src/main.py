from fastmcp import FastMCP
from core import database
from services import cine_service
from services import binge_service

# Initialize database
database.init_db()

mcp = FastMCP("CineMate")

@mcp.tool()
async def search_movies(query: str) -> str:
    """Search for movies and TV shows by title. Returns a formatted list of results."""
    return await cine_service.search_and_format(query)

@mcp.tool()
async def get_movie_details(title: str) -> str:
    """Get details for a specific movie or TV show by title."""
    try:
        return await cine_service.get_details_logic(title)
    except Exception as e:
        return f"Error getting details: {e}"

@mcp.tool()
async def log_movie(titles: str, rating: float, review: str) -> str:
    """Log one or more watched movies/shows (comma-separated). Updates history and removes from watchlist."""
    return await cine_service.batch_log_movies(titles, rating, review)

@mcp.tool()
async def delete_from_history(title: str) -> str:
    """Delete a movie/TV show from your watch history by title."""
    try:
        return await cine_service.delete_from_history_logic(title)
    except Exception as e:
        return f"Error deleting from history: {e}"

@mcp.tool()
async def add_to_watchlist(titles: str) -> str:
    """Add one or more movies/shows to watchlist (comma-separated)."""
    return await cine_service.batch_add_watchlist(titles)

@mcp.tool()
async def delete_from_watchlist(title: str) -> str:
    """Delete a movie/TV show from your watchlist by title."""
    try:
        return await cine_service.delete_from_watchlist_logic(title)
    except Exception as e:
        return f"Error deleting from watchlist: {e}"

@mcp.tool()
async def schedule_movie(title: str, time_str: str) -> str:
    """Schedule a movie/TV show on Google Calendar. time_str can be natural language like 'tomorrow at 8pm'."""
    try:
        return await cine_service.schedule_movie_logic(title, time_str)
    except Exception as e:
        return f"Failed to schedule event: {e}"

@mcp.tool()
async def reschedule_movie(title: str, new_time_str: str) -> str:
    """Reschedule an existing movie/TV show event on Google Calendar."""
    try:
        return await cine_service.reschedule_movie_logic(title, new_time_str)
    except Exception as e:
        return f"Error rescheduling: {e}"

@mcp.tool()
async def schedule_binge(title: str, episodes_per_day: int, start_time_str: str) -> str:
    """
    Schedule a binge-watching plan for a TV show.
    Calculates how long it will take and creates calendar events.
    """
    try:
        return await binge_service.plan_and_schedule_binge(title, episodes_per_day, start_time_str)
    except Exception as e:
        return f"Error scheduling binge: {e}"

@mcp.tool()
async def cancel_movie(titles: str) -> str:
    """Cancel (delete) one or more scheduled events (comma-separated)."""
    return await cine_service.batch_cancel_movies(titles)

@mcp.tool()
async def cancel_binge(title: str) -> str:
    """Cancel (delete) all binge-watching sessions for a TV show."""
    try:
        return await binge_service.cancel_binge_plan(title)
    except Exception as e:
        return f"Error cancelling binge: {e}"

@mcp.tool()
async def cancel_on_date(date_str: str) -> str:
    """Cancel (delete) ALL events on a specific date (e.g., 'today', '2025-12-25')."""
    return await cine_service.cancel_events_on_date(date_str)

@mcp.tool()
async def cancel_period(start_date: str, end_date: str = None) -> str:
    """
    Cancel events in a period.
    - Range: provide both start and end (e.g., "monday", "friday").
    - Starting From: provide only start_date and use "forever" or "onwards" as end_date.
    """
    if not end_date:
        return await cine_service.cancel_events_on_date(start_date)
        
    if end_date.lower() in ["forever", "onwards", "end of time", "all"]:
        return await cine_service.cancel_events_starting_from(start_date)
        
    return await cine_service.cancel_events_in_range(start_date, end_date)

@mcp.resource("cinemate://history")
def get_history_resource() -> str:
    """Get the user's watch history."""
    history = database.get_history()
    if not history:
        return "History is empty."
    
    output = "Watch History:\n"
    for title, rating, review, watched_at, media_type in history:
        output += f"- [{media_type.upper()}] {title} ({rating}/10): {review} [Watched: {watched_at}]\n"
    return output

@mcp.resource("cinemate://watchlist")
def get_watchlist_resource() -> str:
    """Get the user's watchlist."""
    watchlist = database.get_watchlist()
    if not watchlist:
        return "Watchlist is empty."
    
    output = "Watchlist:\n"
    for title, genre, release, added_at, media_type in watchlist:
        output += f"- [{media_type.upper()}] {title} ({genre}) [Added: {added_at}]\n"
    return output

@mcp.tool()
async def get_watch_history() -> str:
    """List all movies and TV shows in your watch history."""
    return await cine_service.get_history_logic()

@mcp.tool()
async def get_watchlist() -> str:
    """List all movies and TV shows in your watchlist."""
    return await cine_service.get_watchlist_logic()

@mcp.tool()
async def clear_watch_history() -> str:
    """Clear ALL entries from your watch history. Irreversible."""
    return await cine_service.clear_history_logic()

@mcp.tool()
async def clear_watchlist() -> str:
    """Clear ALL entries from your watchlist. Irreversible."""
    return await cine_service.clear_watchlist_logic()

@mcp.tool()
async def get_where_to_watch(title: str, country: str = "India") -> str:
    """Find where a movie or TV show is streaming. Default country is India."""
    try:
        return await cine_service.get_where_to_watch_logic(title, country)
    except Exception as e:
        return f"Error getting watch providers: {e}"

@mcp.tool()
async def get_my_stats() -> str:
    """Get analytics about your movie watching habits."""
    try:
        return await cine_service.get_my_stats_logic()
    except Exception as e:
        return f"Error calculating stats: {e}"

if __name__ == "__main__":
    mcp.run()
