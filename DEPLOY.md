# 🚀 Deploying Your Motivation Site to a Free Domain

This codebase is fully prepared for 1-click deployment to various free cloud hosting platforms. Since the backend is written in Python (FastAPI) and requires downloading capabilities (`yt-dlp`), the best platform to host this completely for free is **Render**.

Below are the step-by-step instructions to get your site online with a free `yourname.onrender.com` domain.

---

## Option 1: Deploy for Free on Render (Recommended)

Render is a free cloud platform that fully supports Python, FastAPI, and file downloads.

### Step 1: Push Code to your GitHub
1. Create a new repository on your GitHub account (e.g., `motivation-video-player`).
2. Push this project code to your repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of continuous motivation site"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Create a Free Web Service on Render
1. Go to [Render.com](https://render.com) and sign up for a free account.
2. Click **New +** in the dashboard and select **Web Service**.
3. Connect your GitHub account and select your `motivation-video-player` repository.
4. Fill in the following settings:
   - **Name:** `motivation-player` (or any name you prefer)
   - **Environment:** `Python 3`
   - **Region:** Choose the region closest to you
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt` (We have included a `requirements.txt` in the root)
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Select the **Free** instance type.
6. Click **Create Web Service**.

Render will automatically build your site and give you a free public HTTPS domain (e.g., `https://motivation-player.onrender.com`)!

---

## Option 2: Run Locally (Perfect for personal daily use)

If you just want this playing on a second monitor or tablet at home to fuel your day, running it locally is extremely easy:

1. Clone or download this folder to your machine.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the server:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 3000
   ```
4. Open your web browser and navigate to `http://127.0.0.1:3000`.

---

## 🎬 Automatic Motivational Feed (Pexels + YouTube)

The app can automatically fill your feed with motivational content on its own — no manually pasted links needed. Two sources, use either or both:

**Pexels** — royalty-free stock footage, played as direct video files.
1. Get a free API key at [pexels.com/api](https://www.pexels.com/api/) (about a minute, no card).
2. Set it as an environment variable named `PEXELS_API_KEY`.

**YouTube** — real creator content (speeches, hype videos, etc.), played through YouTube's official embedded player.
1. Go to [Google Cloud Console](https://console.cloud.google.com/), create a project (or use an existing one), enable the **YouTube Data API v3**, then create an API key under **Credentials**.
2. Set it as an environment variable named `YOUTUBE_API_KEY`.
   - Free quota is 10,000 units/day; each search costs 100 units. The app only spends ~100 units per refresh cycle by default, so this comfortably lasts all day even on frequent refreshes.

**Setting environment variables:**
- **On Render:** Dashboard → your service → **Environment** tab → **Add Environment Variable**.
- **Locally:** `export PEXELS_API_KEY=your_key` / `export YOUTUBE_API_KEY=your_key` before running `uvicorn`.

Restart/redeploy after setting either key. On startup, the server begins pulling fresh clips automatically every 45 minutes (configurable via `FEED_POLL_MINUTES`). Use the **"Get More Motivation"** button in the app to trigger an immediate refresh instead of waiting.

Without either key set, the app still works fine — it just falls back to only the default/manually-added videos.

---

## 📝 Included Project Requirements File

We have created a `requirements.txt` in your project folder containing all necessary dependencies for deployment:

```txt
fastapi==0.141.1
uvicorn==0.52.1
pydantic==2.13.4
yt-dlp==2026.07.04
requests==2.34.2
httpx==0.28.1
```
