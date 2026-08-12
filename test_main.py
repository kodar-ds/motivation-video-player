import pytest
from fastapi.testclient import TestClient
import os
import json
import main

@pytest.fixture
def client():
    # Make sure we clean up database files for clean test runs
    if os.path.exists("videos.json"):
        os.remove("videos.json")
    if os.path.exists("downloads.json"):
        os.remove("downloads.json")
    
    # Reload/Re-initialize application database structures
    main.load_json_file(main.VIDEOS_FILE, main.DEFAULT_VIDEOS)
    main.load_json_file(main.DOWNLOADS_FILE, [])
    
    with TestClient(main.app) as c:
        yield c

def test_get_daily_quote(client):
    response = client.get("/api/quote")
    assert response.status_code == 200
    data = response.json()
    assert "quote" in data
    assert "author" in data
    assert len(data["quote"]) > 0

def test_get_videos(client):
    response = client.get("/api/videos")
    assert response.status_code == 200
    videos = response.json()
    assert isinstance(videos, list)
    assert len(videos) > 0
    assert any(v["id"] == "def-1" for v in videos)

def test_add_video_success(client):
    new_video_payload = {
        "url": "https://example.com/motivation.mp4",
        "title": "Rise of Champions",
        "description": "Unbelievable motivational speech."
    }
    response = client.post("/api/videos", json=new_video_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Video added successfully"
    assert data["video"]["title"] == "Rise of Champions"
    assert data["video"]["url"] == "https://example.com/motivation.mp4"

    # Verify it is returned in list
    list_response = client.get("/api/videos")
    assert any(v["url"] == "https://example.com/motivation.mp4" for v in list_response.json())

def test_add_video_duplicate(client):
    payload = {
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "title": "Duplicate title"
    }
    # It already exists in default videos, so it should fail
    response = client.post("/api/videos", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_add_video_empty_url(client):
    payload = {
        "url": ""
    }
    response = client.post("/api/videos", json=payload)
    assert response.status_code == 400 # FastAPI validation or our manual check

def test_get_downloads_empty(client):
    response = client.get("/api/downloads")
    assert response.status_code == 200
    assert response.json() == []

def test_download_endpoint_flow(client):
    url = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/classroom.mp4"
    response = client.post("/api/download", json={"url": url, "title": "Classroom test"})
    assert response.status_code == 200
    assert response.json()["status"] == "started"

    # Query immediately to check downloading status
    downloads_response = client.get("/api/downloads")
    assert len(downloads_response.json()) == 1
    assert downloads_response.json()[0]["url"] == url
