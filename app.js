document.addEventListener('DOMContentLoaded', () => {
    // State management
    let playlist = [];
    let currentVideoIndex = -1;
    let isPlaying = false;
    let downloads = [];

    // DOM Elements
    const videoPlayer = document.getElementById('motivational-video');
    const embedContainer = document.getElementById('embed-container');
    const quoteText = document.getElementById('quote-text');
    const quoteAuthor = document.getElementById('quote-author');
    const videoTitle = document.getElementById('video-title');
    const videoDesc = document.getElementById('video-desc');

    const prevBtn = document.getElementById('prev-btn');
    const playPauseBtn = document.getElementById('play-pause-btn');
    const nextBtn = document.getElementById('next-btn');
    const saveDlBtn = document.getElementById('save-dl-btn');

    const addVideoForm = document.getElementById('add-video-form');
    const newVideoUrl = document.getElementById('new-video-url');
    const newVideoTitle = document.getElementById('new-video-title');

    const refreshDownloadsBtn = document.getElementById('refresh-downloads');
    const clearFailedBtn = document.getElementById('clear-failed-btn');
    const refreshFeedBtn = document.getElementById('refresh-feed-btn');
    const downloadsList = document.getElementById('downloads-list');
    const playlistList = document.getElementById('playlist-list');
    const toastContainer = document.getElementById('toast-container');

    // Init App
    init();

    // --- Auto-download helpers ---
    // Instagram (and most non-.mp4 sources) can't reliably be embedded in an iframe -
    // Instagram blocks embedding on most posts. So instead of making the user click
    // "Save & Download" by hand, we kick off the download automatically in the
    // background as soon as a video is added or comes up in rotation, and swap the
    // player over to the local file the moment it's ready.

    function findCompletedDownload(url) {
        return downloads.find(dl => dl.url === url && dl.status === 'completed');
    }

    function isAlreadyTrackedDownload(url) {
        return downloads.some(dl => dl.url === url && (dl.status === 'completed' || dl.status === 'downloading'));
    }

    async function ensureDownloaded(url, title) {
        if (isAlreadyTrackedDownload(url)) return;
        try {
            await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, title })
            });
            fetchDownloads();
        } catch (err) {
            console.error('Auto-download trigger failed', err);
        }
    }

    // Proactively start downloading every non-direct video in the playlist so the
    // library fills in on its own and playback doesn't stall waiting on one at a time.
    function prefetchPlaylistDownloads() {
        playlist.forEach(video => {
            if (isDirectVideoUrl(video.url)) return;
            ensureDownloaded(video.url, video.title);
        });
    }

    function isDirectVideoUrl(url) {
        return url.endsWith('.mp4') || url.includes('.mp4?') || url.includes('googleapis.com') || url.includes('raw.githubusercontent');
    }

    // If the currently-showing video was being embedded (or waiting on a download)
    // and its local copy just finished downloading, swap the player over to it live
    // so playback continues seamlessly instead of sitting on a broken/blocked embed.
    function maybeSwapInLocalCopy() {
        if (currentVideoIndex === -1) return;
        const video = playlist[currentVideoIndex];
        if (!video || isDirectVideoUrl(video.url)) return;
        if (!videoPlayer.classList.contains('hidden')) return; // already on a playable video

        const localCopy = findCompletedDownload(video.url);
        if (localCopy) {
            embedContainer.classList.add('hidden');
            embedContainer.innerHTML = '';
            videoPlayer.classList.remove('hidden');
            videoPlayer.src = localCopy.local_path;
            videoPlayer.load();
            videoPlayer.play().catch(e => console.log(e));
            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
            isPlaying = true;
            showToast(`Now playing: ${video.title}`, 'success');
        }
    }

    function init() {
        fetchQuote();
        fetchPlaylist();
        fetchDownloads();

        // Start checking downloads in background every 5 seconds
        setInterval(fetchDownloads, 5000);
        // Periodically re-scan the playlist for anything still missing a local copy
        // (covers videos added by others / added while the tab was open)
        setInterval(prefetchPlaylistDownloads, 15000);
        // Pick up new clips the server auto-fetches from Pexels in the background
        setInterval(fetchPlaylist, 60000);

        refreshFeedBtn.addEventListener('click', triggerFeedRefresh);

        // Event Listeners
        prevBtn.addEventListener('click', playPrevious);
        playPauseBtn.addEventListener('click', togglePlay);
        nextBtn.addEventListener('click', playNext);
        saveDlBtn.addEventListener('click', triggerDownload);

        addVideoForm.addEventListener('submit', handleAddVideo);
        refreshDownloadsBtn.addEventListener('click', fetchDownloads);
        clearFailedBtn.addEventListener('click', clearFailedDownloads);

        // End of video autoplay trigger
        videoPlayer.addEventListener('ended', playNext);
    }

    // Toast Notifications
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerText = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 4000);
    }

    // Daily Quotes API fetch
    async function fetchQuote() {
        try {
            const res = await fetch('/api/quote');
            if (res.ok) {
                const data = await res.json();
                quoteText.innerText = `"${data.quote}"`;
                quoteAuthor.innerText = `— ${data.author}`;
            }
        } catch (err) {
            console.error('Failed to fetch quote', err);
        }
    }

    // Fetch Feed Playlist
    async function fetchPlaylist() {
        try {
            const res = await fetch('/api/videos');
            if (res.ok) {
                playlist = await res.json();
                renderPlaylist();
                prefetchPlaylistDownloads();
                if (playlist.length > 0 && currentVideoIndex === -1) {
                    // Play random or first video to start
                    currentVideoIndex = Math.floor(Math.random() * playlist.length);
                    loadVideo(currentVideoIndex);
                }
            }
        } catch (err) {
            showToast('Failed to load playlist feed', 'error');
        }
    }

    // Load selected Video index
    function loadVideo(index) {
        if (index < 0 || index >= playlist.length) return;
        currentVideoIndex = index;
        const video = playlist[index];

        videoTitle.innerText = video.title || 'Untitled Motivation';
        videoDesc.innerText = video.description || 'Continuous flow...';

        // Check source and display type (Direct MP4 vs Embedded Platforms)
        const url = video.url;
        const isDirectVideo = isDirectVideoUrl(url);
        const localCopy = findCompletedDownload(url);

        if (isDirectVideo || localCopy) {
            embedContainer.classList.add('hidden');
            embedContainer.innerHTML = '';
            videoPlayer.classList.remove('hidden');
            videoPlayer.src = localCopy ? localCopy.local_path : url;
            videoPlayer.load();
            if (isPlaying) {
                videoPlayer.play().catch(e => console.log('Autoplay blocked initially', e));
            }
        } else {
            // No direct file and no local copy yet - kick off a background download so
            // the app can automatically swap to a playable local copy the moment it's
            // ready (Instagram in particular blocks most iframe embeds, so this is what
            // actually gets it to play without you clicking "Save & Download" yourself).
            ensureDownloaded(url, video.title);

            // Embed or IFrame option (shown while the local copy downloads)
            videoPlayer.classList.add('hidden');
            videoPlayer.pause();
            embedContainer.classList.remove('hidden');

            let embedHtml = '';
            if (url.includes('youtube.com') || url.includes('youtu.be')) {
                let videoId = '';
                if (url.includes('v=')) {
                    videoId = url.split('v=')[1].split('&')[0];
                } else if (url.includes('youtu.be/')) {
                    videoId = url.split('youtu.be/')[1].split('?')[0];
                }
                embedHtml = `<iframe src="https://www.youtube.com/embed/${videoId}?autoplay=1&mute=0&enablejsapi=1" allow="autoplay; encrypted-media" allowfullscreen></iframe>`;
            } else if (url.includes('instagram.com')) {
                // Strip query parameters to get clean base reel or post path
                const cleanUrl = url.split('?')[0].replace(/\/+$/, '');
                embedHtml = `<iframe src="${cleanUrl}/embed" width="100%" height="100%" frameborder="0" scrolling="no" allowtransparency="true"></iframe>`;
            } else {
                // Catch all standard iframe embedding
                embedHtml = `<iframe src="${url}" width="100%" height="100%" allow="autoplay"></iframe>`;
            }
            embedContainer.innerHTML = embedHtml;
        }

        // Update active class in playlist DOM list
        document.querySelectorAll('.playlist-item').forEach((el, i) => {
            if (i === index) el.classList.add('active');
            else el.classList.remove('active');
        });
    }

    // Controls Action Handlers
    function togglePlay() {
        if (videoPlayer.classList.contains('hidden')) {
            showToast('Playback controlled by embed player above', 'info');
            return;
        }
        if (isPlaying) {
            videoPlayer.pause();
            playPauseBtn.innerHTML = '<i class="fas fa-play"></i> Play';
            isPlaying = false;
        } else {
            videoPlayer.play().catch(err => console.log(err));
            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
            isPlaying = true;
        }
    }

    function playNext() {
        if (playlist.length === 0) return;
        // Loop around or pick a random index
        let nextIndex = (currentVideoIndex + 1) % playlist.length;
        loadVideo(nextIndex);
        if (!videoPlayer.classList.contains('hidden')) {
            videoPlayer.play().catch(err => console.log(err));
            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
            isPlaying = true;
        }
    }

    function playPrevious() {
        if (playlist.length === 0) return;
        let prevIndex = currentVideoIndex - 1;
        if (prevIndex < 0) prevIndex = playlist.length - 1;
        loadVideo(prevIndex);
        if (!videoPlayer.classList.contains('hidden')) {
            videoPlayer.play().catch(err => console.log(err));
            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
            isPlaying = true;
        }
    }

    // Save & Download Action
    async function triggerDownload() {
        if (currentVideoIndex === -1) return;
        const video = playlist[currentVideoIndex];
        
        showToast(`Download initiated for: ${video.title}`, 'info');

        try {
            const res = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: video.url, title: video.title })
            });
            const data = await res.json();
            showToast(data.message, 'success');
            fetchDownloads();
        } catch (err) {
            showToast('Failed to start download task', 'error');
        }
    }

    // Add Video Form handler
    async function handleAddVideo(e) {
        e.preventDefault();
        const url = newVideoUrl.value.trim();
        const title = newVideoTitle.value.trim();

        if (!url) return;

        try {
            const res = await fetch('/api/videos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, title })
            });

            if (res.ok) {
                showToast('Video added to feed!', 'success');
                newVideoUrl.value = '';
                newVideoTitle.value = '';
                fetchPlaylist();
            } else {
                const errData = await res.json();
                showToast(errData.detail || 'Error adding video', 'error');
            }
        } catch (err) {
            showToast('Server connection error', 'error');
        }
    }

    // Manually trigger the server to pull a fresh batch of motivational clips now
    async function triggerFeedRefresh() {
        showToast('Fetching fresh motivational clips...', 'info');
        try {
            const res = await fetch('/api/videos/refresh-feed', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                showToast(`${data.message} (+${data.added} new)`, 'success');
                fetchPlaylist();
            } else {
                showToast(data.detail || 'Could not refresh feed', 'error');
            }
        } catch (err) {
            showToast('Server connection error', 'error');
        }
    }

    // Fetch downloaded items
    async function fetchDownloads() {
        try {
            const res = await fetch('/api/downloads');
            if (res.ok) {
                downloads = await res.json();
                renderDownloads();
                maybeSwapInLocalCopy();
            }
        } catch (err) {
            console.error('Failed to load downloads', err);
        }
    }

    // Clean failed downloads
    async function clearFailedDownloads() {
        try {
            const res = await fetch('/api/downloads/clean');
            if (res.ok) {
                showToast('Cleared failed downloads', 'success');
                fetchDownloads();
            }
        } catch (err) {
            showToast('Failed to clear list', 'error');
        }
    }

    // Render HTML Views
    function renderPlaylist() {
        playlistList.innerHTML = '';
        if (playlist.length === 0) {
            playlistList.innerHTML = '<p class="empty-msg">No playlist feeds available.</p>';
            return;
        }

        playlist.forEach((video, index) => {
            const item = document.createElement('div');
            item.className = `playlist-item ${index === currentVideoIndex ? 'active' : ''}`;
            item.innerHTML = `
                <div class="playlist-item-title">${video.title || 'Untitled video'}</div>
                <div class="playlist-item-url">${video.url}</div>
            `;
            item.addEventListener('click', () => loadVideo(index));
            playlistList.appendChild(item);
        });
    }

    function renderDownloads() {
        downloadsList.innerHTML = '';
        if (downloads.length === 0) {
            downloadsList.innerHTML = '<p class="empty-msg">No saved downloads yet.</p>';
            return;
        }

        downloads.forEach((dl) => {
            const item = document.createElement('div');
            item.className = 'download-item';
            
            let statusClass = `status-${dl.status}`;
            let actionsHtml = '';

            if (dl.status === 'completed') {
                actionsHtml = `
                    <button class="download-btn-play" title="Play Local File">
                        <i class="fas fa-play-circle"></i>
                    </button>
                    <a href="${dl.local_path}" download class="btn btn-sm" title="Save file locally">
                        <i class="fas fa-save"></i>
                    </a>
                `;
            } else if (dl.status === 'downloading') {
                actionsHtml = '<i class="fas fa-spinner fa-spin status-downloading"></i>';
            } else {
                actionsHtml = '<i class="fas fa-exclamation-circle status-failed" title="Failed"></i>';
            }

            item.innerHTML = `
                <div class="download-info">
                    <div class="download-title" title="${dl.title}">${dl.title}</div>
                    <div class="download-status ${statusClass}">${dl.status}</div>
                </div>
                <div class="download-actions">
                    ${actionsHtml}
                </div>
            `;

            // If playable local, add listener to feed player
            const playBtn = item.querySelector('.download-btn-play');
            if (playBtn) {
                playBtn.addEventListener('click', () => {
                    // Inject this downloaded file into current player directly
                    videoTitle.innerText = `[Local] ${dl.title}`;
                    videoDesc.innerText = 'Playing saved offline download';
                    embedContainer.classList.add('hidden');
                    videoPlayer.classList.remove('hidden');
                    videoPlayer.src = dl.local_path;
                    videoPlayer.load();
                    videoPlayer.play().catch(e => console.log(e));
                    playPauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
                    isPlaying = true;
                    showToast(`Playing offline: ${dl.title}`, 'success');
                });
            }

            downloadsList.appendChild(item);
        });
    }
});
