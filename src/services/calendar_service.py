import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    
    # Get absolute path to the project root (2 levels up)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    token_path = os.path.join(base_dir, 'token.json')
    creds_path = os.path.join(base_dir, 'credentials.json')
    
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"credentials.json not found at {creds_path}. Please place it in the project root.")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

def create_event(summary: str, description: str, start_time: datetime.datetime, duration_minutes: int = 120):
    """Create a calendar event."""
    service = get_calendar_service()
    
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC', # Or system local
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC',
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    return event.get('htmlLink')

def list_events(query: str, max_results: int = 5):
    """List upcoming events matching a query."""
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    
    events_result = service.events().list(
        calendarId='primary', 
        q=query,
        timeMin=now,
        maxResults=max_results, 
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

def list_events_in_range(start_time: datetime.datetime, end_time: datetime.datetime):
    """List events within a specific time range."""
    service = get_calendar_service()
    
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

def update_event(event_id: str, summary: str, description: str, start_time: datetime.datetime, duration_minutes: int = 120):
    """Update an existing calendar event."""
    service = get_calendar_service()
    
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC', # Or system local if preferred, but isoformat usually carries offset if aware
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC',
        },
    }
    
    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    return updated_event.get('htmlLink')

def delete_event(event_id: str):
    """Delete a calendar event."""
    service = get_calendar_service()
    service.events().delete(calendarId='primary', eventId=event_id).execute()
    return True

if __name__ == '__main__':
    # Test auth
    try:
        service = get_calendar_service()
        print("Calendar service authenticated successfully.")
    except Exception as e:
        print(f"Error: {e}")
