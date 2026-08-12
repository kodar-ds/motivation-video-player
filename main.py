from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import random
import datetime
import yt_dlp
import uuid
import logging
import urllib.request
import asyncio
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("motivation_site")

app = FastAPI(title="Continuous Motivation Site")

# CORS middleware for local development ease
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("static/downloads", exist_ok=True)

VIDEOS_FILE = "videos.json"
DOWNLOADS_FILE = "downloads.json"

# In-memory motivational quotes
MOTIVATIONAL_QUOTES = [
    {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"quote": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"quote": "Your time is limited, so don't waste it living someone else's life.", "author": "Steve Jobs"},
    {"quote": "The mind is everything. What you think you become.", "author": "Buddha"},
    {"quote": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"quote": "An unexamined life is not worth living.", "author": "Socrates"},
    {"quote": "Eighty percent of success is showing up.", "author": "Woody Allen"},
    {"quote": "Don't judge each day by the harvest you reap but by the seeds that you plant.", "author": "Robert Louis Stevenson"},
    {"quote": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
    {"quote": "It is during our darkest moments that we must focus to see the light.", "author": "Aristotle"},
    {"quote": "Do not go where the path may lead, go instead where there is no path and leave a trail.", "author": "Ralph Waldo Emerson"},
    {"quote": "You miss 100% of the shots you don't take.", "author": "Wayne Gretzky"},
    {"quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"quote": "Hardships often prepare ordinary people for an extraordinary destiny.", "author": "C.S. Lewis"},
    {"quote": "Keep your eyes on the stars, and your feet on the ground.", "author": "Theodore Roosevelt"},
    {"quote": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"quote": "If you can dream it, you can do it.", "author": "Walt Disney"},
    {"quote": "It always seems impossible until it's done.", "author": "Nelson Mandela"},
    {"quote": "Quality is not an act, it is a habit.", "author": "Aristotle"}
]

class VideoItem(BaseModel):
    url: str
    title: str = ""
    description: str = ""

def load_json_file(filepath: str, default_data):
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            json.dump(default_data, f, indent=4)
        return default_data
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return default_data

def save_json_file(filepath: str, data):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")

# Initial default videos
DEFAULT_VIDEOS = [
    {
        "id": "def-1",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "title": "Rise and Grind",
        "description": "Start your day with maximum energy."
    },
    {
        "id": "def-2",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "title": "Dream Big",
        "description": "Visualize your future and achieve greatness."
    },
    {
        "id": "def-3",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "title": "Unstoppable Force",
        "description": "No obstacles can stop a determined mind."
    },
    {
        "id": "def-4",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4",
        "title": "Adventure of Life",
        "description": "Embrace the journey and keep moving forward."
    }
]

# Initialize JSON databases
load_json_file(VIDEOS_FILE, DEFAULT_VIDEOS)
load_json_file(DOWNLOADS_FILE, [])

# --- Automatic motivational feed via Pexels (free, royalty-free stock video API) ---
# This replaces manually pasting in video links: the server periodically searches
# Pexels for motivational/success/workout footage and appends fresh clips straight
# into videos.json on its own.
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
PEXELS_SEARCH_TERMS = [
    "motivation",
    "success mindset",
    "workout motivation",
    "inspirational speech",
    "discipline hustle",
    "overcoming challenge",
]
PEXELS_POLL_MINUTES = int(os.environ.get("PEXELS_POLL_MINUTES", "30"))
PEXELS_PER_FETCH = int(os.environ.get("PEXELS_PER_FETCH", "4"))


def fetch_pexels_clips(query: str, per_page: int = 4):
    """Query Pexels' video search API for a batch of royalty-free clips."""
    if not PEXELS_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": per_page, "orientation": "portrait"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Pexels fetch failed for '{query}': {e}")
        return []

    results = []
    for item in data.get("videos", []):
        video_files = item.get("video_files", [])
        if not video_files:
            continue
        # Prefer a reasonable HD mp4 (avoid multi-hundred-MB 4K files)
        candidates = [f for f in video_files if f.get("file_type") == "video/mp4"]
        candidates.sort(key=lambda f: f.get("width") or 0)
        chosen = next((f for f in candidates if (f.get("width") or 0) >= 720), None)
        chosen = chosen or (candidates[-1] if candidates else None)
        if not chosen:
            continue

        creator = item.get("user", {}).get("name", "Unknown creator")
        results.append({
            "url": chosen["link"],
            "title": f"{query.title()} — by {creator}",
            "description": f"Royalty-free clip via Pexels (search: {query}).",
        })
    return results


def auto_populate_feed(per_term: int = None):
    """Pull fresh clips for each search term and merge any new ones into the feed."""
    per_term = per_term or PEXELS_PER_FETCH
    videos = load_json_file(VIDEOS_FILE, DEFAULT_VIDEOS)
    existing_urls = {v["url"] for v in videos}
    added = 0
    for term in PEXELS_SEARCH_TERMS:
        for clip in fetch_pexels_clips(term, per_page=per_term):
            if clip["url"] in existing_urls:
                continue
            videos.append({
                "id": str(uuid.uuid4()),
                "url": clip["url"],
                "title": clip["title"],
                "description": clip["description"],
            })
            existing_urls.add(clip["url"])
            added += 1
    if added:
        save_json_file(VIDEOS_FILE, videos)
        logger.info(f"Auto-added {added} new motivational clips from Pexels.")
    return added


async def pexels_background_loop():
    await asyncio.sleep(5)  # small delay so the app finishes booting first
    while True:
        try:
            auto_populate_feed()
        except Exception as e:
            logger.error(f"Background feed refresh failed: {e}")
        await asyncio.sleep(PEXELS_POLL_MINUTES * 60)


@app.on_event("startup")
async def start_background_tasks():
    if PEXELS_API_KEY:
        asyncio.create_task(pexels_background_loop())
        logger.info(f"Auto motivational feed enabled - refreshing every {PEXELS_POLL_MINUTES} min.")
    else:
        logger.warning(
            "PEXELS_API_KEY is not set. Set it as an environment variable to enable the "
            "automatic motivational video feed. Falling back to manually-added videos only."
        )


@app.post("/api/videos/refresh-feed")
def refresh_feed():
    """Manually trigger an immediate feed refresh instead of waiting for the timer."""
    if not PEXELS_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="PEXELS_API_KEY is not configured on the server. Get a free key at pexels.com/api and set it as an environment variable."
        )
    added = auto_populate_feed()
    return {"message": "Fetched fresh motivational clips from Pexels", "added": added}

@app.get("/api/quote")
def get_daily_quote():
    # Return a deterministic quote daily based on current date, or a randomized one
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    seed = sum(ord(c) for c in today_str)
    random.seed(seed)
    quote = random.choice(MOTIVATIONAL_QUOTES)
    # Reset seed to preserve randomness elsewhere
    random.seed()
    return quote

@app.get("/api/videos")
def get_videos():
    videos = load_json_file(VIDEOS_FILE, DEFAULT_VIDEOS)
    return videos

@app.post("/api/videos")
def add_video(video: VideoItem):
    url = video.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    
    videos = load_json_file(VIDEOS_FILE, DEFAULT_VIDEOS)
    
    # Check duplicate
    if any(v["url"] == url for v in videos):
        raise HTTPException(status_code=400, detail="Video already exists in your feed")
    
    new_video = {
        "id": str(uuid.uuid4()),
        "url": url,
        "title": video.title.strip() or f"Inspirational Clip {len(videos) + 1}",
        "description": video.description.strip() or "Custom added video"
    }
    
    videos.append(new_video)
    save_json_file(VIDEOS_FILE, videos)
    return {"message": "Video added successfully", "video": new_video}

class DownloadRequest(BaseModel):
    url: str
    title: str = ""

def download_video_task(url: str, custom_title: str):
    logger.info(f"Starting download for: {url}")
    
    downloads = load_json_file(DOWNLOADS_FILE, [])
    
    # Check if already downloaded
    for dl in downloads:
        if dl["url"] == url and dl["status"] == "completed":
            logger.info("Video already successfully downloaded.")
            return

    # Prepare temp item with status 'downloading'
    download_id = str(uuid.uuid4())
    temp_item = {
        "id": download_id,
        "url": url,
        "title": custom_title or f"Downloading {datetime.date.today()}",
        "filename": "",
        "local_path": "",
        "status": "downloading",
        "timestamp": datetime.datetime.now().isoformat(),
        "error": None
    }
    downloads.append(temp_item)
    save_json_file(DOWNLOADS_FILE, downloads)

    # If it is a direct MP4 link, we can use a simpler request mechanism as a fallback/primary
    is_direct = url.lower().endswith(".mp4") or "googleapis.com" in url or "raw.githubusercontent" in url
    
    if is_direct:
        try:
            logger.info("Direct MP4 URL detected, initiating direct HTTP download.")
            base_filename = f"{download_id}.mp4"
            local_file_path = os.path.join("static", "downloads", base_filename)
            
            # Use urllib with user-agent to bypass basic 403 blocks
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req) as response, open(local_file_path, 'wb') as out_file:
                out_file.write(response.read())
            
            local_path = f"/static/downloads/{base_filename}"
            title = custom_title or f"Direct Video {len(downloads)}"
            
            # Update downloads list
            downloads = load_json_file(DOWNLOADS_FILE, [])
            for dl in downloads:
                if dl["id"] == download_id:
                    dl["status"] = "completed"
                    dl["filename"] = base_filename
                    dl["local_path"] = local_path
                    dl["title"] = title
                    break
            save_json_file(DOWNLOADS_FILE, downloads)
            logger.info(f"Successfully directly downloaded: {url} -> {local_path}")
            return
        except Exception as direct_err:
            logger.warning(f"Direct download failed: {direct_err}. Falling back to yt-dlp.")

    # Standard fallback via yt-dlp
    outtmpl = os.path.join("static", "downloads", f"{download_id}.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Find actual relative filename
            base_filename = os.path.basename(filename)
            local_path = f"/static/downloads/{base_filename}"
            title = custom_title or info.get("title") or f"Downloaded Video {len(downloads)}"
            
            # Update downloads list
            downloads = load_json_file(DOWNLOADS_FILE, [])
            for dl in downloads:
                if dl["id"] == download_id:
                    dl["status"] = "completed"
                    dl["filename"] = base_filename
                    dl["local_path"] = local_path
                    dl["title"] = title
                    break
            save_json_file(DOWNLOADS_FILE, downloads)
            logger.info(f"Successfully downloaded: {url} -> {local_path}")
            
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        downloads = load_json_file(DOWNLOADS_FILE, [])
        for dl in downloads:
            if dl["id"] == download_id:
                dl["status"] = "failed"
                dl["error"] = str(e)
                break
        save_json_file(DOWNLOADS_FILE, downloads)

@app.post("/api/download")
def download_video(req: DownloadRequest, background_tasks: BackgroundTasks):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    
    # Check if already downloading or completed
    downloads = load_json_file(DOWNLOADS_FILE, [])
    for dl in downloads:
        if dl["url"] == url:
            if dl["status"] == "completed":
                return {"message": "Video is already downloaded", "status": "completed", "video": dl}
            elif dl["status"] == "downloading":
                return {"message": "Video download is in progress", "status": "downloading"}
    
    background_tasks.add_task(download_video_task, url, req.title)
    return {"message": "Download task started in background", "status": "started"}

@app.get("/api/downloads")
def get_downloads():
    downloads = load_json_file(DOWNLOADS_FILE, [])
    return downloads

@app.get("/api/downloads/clean")
def clean_failed_downloads():
    downloads = load_json_file(DOWNLOADS_FILE, [])
    cleaned = [dl for dl in downloads if dl["status"] != "failed"]
    save_json_file(DOWNLOADS_FILE, cleaned)
    return {"message": "Cleared failed download tasks", "count": len(downloads) - len(cleaned)}

# Catch-all to serve index.html or fallback to SPA/static files
@app.get("/")
def get_index():
    return FileResponse("static/index.html")

# Serve the static files
app.mount("/static", StaticFiles(directory="static"), name="static")
