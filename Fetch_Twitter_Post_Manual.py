import os
import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from supabase import create_client

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def extract_tweet_data(tweet_url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Debugging mode
            page = browser.new_page()
            page.goto(tweet_url, wait_until="load")

            # Extract tweet content
            try:
                page.wait_for_selector("div[data-testid='tweetText']", timeout=5000)
                tweet_content_element = page.query_selector("div[data-testid='tweetText']")
                tweet_content = tweet_content_element.inner_text() if tweet_content_element else "Tweet content not found"
            except:
                tweet_content = "Tweet content not found"

            # Extract tweet date
            try:
                page.wait_for_selector("time", timeout=5000)
                timestamp_element = page.query_selector("time")
                tweet_date = timestamp_element.get_attribute("datetime") if timestamp_element else None
            except:
                tweet_date = None

            # Format date
            if tweet_date:
                dt = datetime.datetime.fromisoformat(tweet_date.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%m-%d")
                formatted_year = dt.year
                formatted_day = dt.strftime("%A")
            else:
                formatted_date, formatted_year, formatted_day, dt = "Unknown", None, "Unknown", None

            browser.close()

            return {
                "content": tweet_content,
                "url": tweet_url,
                "date": formatted_date,
                "year": formatted_year,
                "day": formatted_day,
                "published_at": dt
            }
    except Exception as e:
        print(f"Error extracting tweet data: {e}")
        return None

def save_to_supabase(tweet_data):
    try:
        response = supabase.table("media").insert({
            "title": tweet_data["content"],
            "url": tweet_data["url"],
            "type": "Tweet",
            "published_at": tweet_data["published_at"].isoformat() if tweet_data["published_at"] else None,
            "description": None,
            "tags": None,
            "thumbnail": None,
            "duration": None,
            "video_id": None,
            "date": tweet_data["date"],
            "year": tweet_data["year"]
        }).execute()
        
        print("Tweet successfully saved to Supabase!")
    except Exception as e:
        print(f"Error saving tweet: {e}")

if __name__ == "__main__":
    tweet_url = input("Enter the tweet URL: ")
    
    tweet_data = extract_tweet_data(tweet_url)

    if tweet_data:
        print("\nExtracted Tweet Data Preview:")
        print(f"Tweet Content: {tweet_data['content']}")
        print(f"Tweet URL: {tweet_data['url']}")
        print(f"Tweet Date: {tweet_data['date']}")
        print(f"Tweet Year: {tweet_data['year']}")
        print(f"Tweet Day: {tweet_data['day']}\n")

        save_to_db = input("Do you want to save this tweet to Supabase? (yes/no): ").strip().lower()
        if save_to_db == "yes":
            save_to_supabase(tweet_data)
        else:
            print("Tweet not saved.")
