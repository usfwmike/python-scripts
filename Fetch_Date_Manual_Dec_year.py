import os
import uuid
import json
import requests
import isodate
import time
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define log file name
LOG_FILE = "script_log.txt"

def write_log(target_date, status):
    """Write status logs to script_log.txt."""
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Date: {target_date} - Status: {status}\n")

def fetch_youtube_videos(channel_id, target_date):
    base_url = "https://www.googleapis.com/youtube/v3/search"
    published_after = f"{target_date}T00:00:00Z"
    published_before = f"{target_date}T23:59:59Z"

    params = {
        "key": YOUTUBE_API_KEY,
        "channelId": channel_id,
        "part": "snippet",
        "order": "date",
        "type": "video",
        "maxResults": 10,
        "publishedAfter": published_after,
        "publishedBefore": published_before
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if "items" not in data:
        print(f"⚠️ Error fetching videos for {target_date}: {data}")
        return []

    return data["items"]

def fetch_video_details(video_ids):
    if not video_ids:
        return {}

    details_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "key": YOUTUBE_API_KEY,
        "id": ",".join(video_ids),
        "part": "contentDetails"
    }

    response = requests.get(details_url, params=params)
    data = response.json()

    video_details = {}
    for item in data.get("items", []):
        video_id = item["id"]
        duration = isodate.parse_duration(item["contentDetails"]["duration"]).total_seconds()
        video_details[video_id] = {"duration": int(duration)}

    return video_details

def save_to_supabase(videos, video_details, target_date):
    data = []
    
    for video in videos:
        video_id = video["id"]["videoId"]
        details = video_details.get(video_id, {})

        published_date = video["snippet"]["publishedAt"]
        year = published_date.split('-')[0]  # Extract year (YYYY)
        month_day = published_date[5:10]  # Extract MM-DD

        entry = {
            "id": str(uuid.uuid4()),
            "title": video["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "type": "youtube",
            "published_at": published_date,
            "description": video["snippet"].get("description", ""),
            "tags": video["snippet"].get("tags", []),
            "thumbnail": video["snippet"]["thumbnails"]["high"]["url"],
            "duration": details.get("duration", 0),
            "video_id": video_id,
            "year": int(year),
            "date": month_day
        }
        
        data.append(entry)

    try:
        response = supabase.table("media").upsert(data).execute()
        print("✅ Videos saved successfully.")
    except Exception as e:
        print(f"❌ Error saving to Supabase: {e}")

if __name__ == "__main__":
    min_year = 2012  # Set the minimum year limit

    # Always prompt for the start date on each run
    start_date_str = input("Enter the starting date (YYYY-MM-DD): ")
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    
    while start_date.year >= min_year:
        target_date = start_date.strftime("%Y-%m-%d")
        print(f"🔍 Fetching videos for {target_date} from Channel ID: {CHANNEL_ID}...")
        
        videos = fetch_youtube_videos(CHANNEL_ID, target_date)
        
        if not videos:
            print(f"⚠️ No videos found for {target_date}. Skipping...")
            write_log(target_date, "Failure")
        else:
            video_ids = [video["id"]["videoId"] for video in videos]
            video_details = fetch_video_details(video_ids)
            print(f"💾 Saving videos for {target_date} to Supabase...")
            save_to_supabase(videos, video_details, target_date)
        
        start_date = start_date.replace(year=start_date.year - 1)
        time.sleep(5)
    
    print("✅ Script completed. Reached the year 2012.")
