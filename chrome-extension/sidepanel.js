// Sidepanel Script for Chrome2NAS Video Downloader

let settings = {};
let detectedUrls = [];
let jobs = [];

// Initialize sidepanel
document.addEventListener('DOMContentLoaded', async () => {
  // Load settings
  settings = await chrome.storage.sync.get(['nasEndpoint', 'apiKey']);

  // Check connection
  checkConnection();

  // Load detected URLs
  loadDetectedUrls();

  // Load recent jobs
  await loadRecentJobs();

  // Setup event listeners
  setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
  document.getElementById('settingsBtn').addEventListener('click', openSettings);
  document.getElementById('refreshBtn').addEventListener('click', loadDetectedUrls);

  // Listen for tab updates (navigation, reload, etc.)
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // When page finishes loading, refresh detected URLs
    if (changeInfo.status === 'complete') {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0] && tabs[0].id === tabId) {
          // Only refresh if it's the current active tab
          loadDetectedUrls();
        }
      });
    }
  });

  // Listen for storage changes to auto-update when new URLs are detected
  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === 'local' && changes.detectedUrls) {
      loadDetectedUrls();
    }
  });
}

// Open settings page
function openSettings() {
  chrome.runtime.openOptionsPage();
}

// Check NAS connection
async function checkConnection() {
  const statusElement = document.getElementById('connectionStatus');
  const statusText = document.getElementById('statusText');
  const statusIcon = document.getElementById('statusIcon');

  if (!settings.nasEndpoint || !settings.apiKey) {
    statusElement.className = 'connection-status disconnected';
    statusText.textContent = 'Not configured';
    statusIcon.textContent = '⚠️';
    return;
  }

  try {
    const response = await fetch(`${settings.nasEndpoint}/api/health`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${settings.apiKey}`
      }
    });

    if (response.ok) {
      statusElement.className = 'connection-status connected';
      statusText.textContent = 'Connected';
      statusIcon.textContent = '✅';
    } else {
      throw new Error('Connection failed');
    }
  } catch (error) {
    statusElement.className = 'connection-status disconnected';
    statusText.textContent = 'Disconnected';
    statusIcon.textContent = '❌';
  }
}

// Load detected URLs
function loadDetectedUrls() {
  chrome.runtime.sendMessage({ action: 'getDetectedUrls' }, (response) => {
    detectedUrls = response.urls || [];
    renderDetectedUrls();
  });
}

// Render detected URLs
function renderDetectedUrls() {
  const listElement = document.getElementById('detectedUrlsList');

  if (detectedUrls.length === 0) {
    listElement.innerHTML = `
      <div class="empty-state">
        <p>🔍 No videos detected yet</p>
        <p class="hint">Browse to a video streaming site</p>
      </div>
    `;
    return;
  }

  listElement.innerHTML = detectedUrls.map((urlInfo, index) => {
    const hasIp = containsIpAddress(urlInfo.url);
    const urlLower = urlInfo.url.toLowerCase();
    const videoType = urlLower.includes('.mp4') ? 'MP4' : 'M3U8';
    return `
    <div class="url-item">
      <div class="url-title">${videoType} #${index + 1}</div>
      <div class="url-link" title="${urlInfo.url}">${truncateUrl(urlInfo.url)}</div>
      ${hasIp ? `
        <div class="ip-warning">
          ⚠️ <strong>IP-Restricted URL Detected</strong><br>
          This URL contains an IP address, meaning the website restricts downloads to that specific IP. 
          To download successfully, your NAS and PC must use the same IP address. 
          Use Tailscale exit node or similar VPN solution to route the traffic through a same IP address.
        </div>
      ` : ''}
      <div class="url-actions">
        <button class="btn-send" data-url="${escapeHtml(urlInfo.url)}" data-page="${escapeHtml(urlInfo.pageUrl || '')}">
          📤 Send to NAS
        </button>
        <button class="btn-copy" data-url="${escapeHtml(urlInfo.url)}">
          📋
        </button>
      </div>
    </div>
  `;
  }).join('');

  // Add event listeners to buttons
  listElement.querySelectorAll('.btn-send').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const url = e.target.dataset.url;
      const pageUrl = e.target.dataset.page;
      sendToNAS(url, pageUrl);
    });
  });

  listElement.querySelectorAll('.btn-copy').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const url = e.target.dataset.url;
      copyToClipboard(url);
    });
  });
}

// Load recent jobs
async function loadRecentJobs() {
  if (!settings.nasEndpoint || !settings.apiKey) {
    return;
  }

  try {
    const response = await fetch(`${settings.nasEndpoint}/api/jobs?limit=10`, {
      headers: {
        'Authorization': `Bearer ${settings.apiKey}`
      }
    });

    if (response.ok) {
      jobs = await response.json();
      renderJobs();
    }
  } catch (error) {
    console.error('Failed to load jobs:', error);
  }
}

// Render jobs
function renderJobs() {
  const listElement = document.getElementById('recentJobsList');

  if (jobs.length === 0) {
    listElement.innerHTML = `
      <div class="empty-state">
        <p>📥 No recent downloads</p>
      </div>
    `;
    return;
  }

  listElement.innerHTML = jobs.map(job => `
    <div class="job-item">
      <div class="job-header">
        <div class="job-title" title="${escapeHtml(job.title)}">${escapeHtml(job.title)}</div>
        <div class="job-status ${job.status}">${job.status}</div>
      </div>
      ${job.status === 'downloading' || job.status === 'processing' ? `
        <div class="job-progress">
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${job.progress}%"></div>
          </div>
          <div class="progress-text">${job.progress}%</div>
        </div>
      ` : ''}
    </div>
  `).join('');
}


// Send to NAS
async function sendToNAS(url, pageUrl) {
  if (!settings.nasEndpoint || !settings.apiKey) {
    alert('Please configure NAS settings first');
    chrome.runtime.openOptionsPage();
    return;
  }

  try {
    // Get current tab title
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const title = tab.title || 'Untitled Video';

    chrome.runtime.sendMessage({
      action: 'sendToNAS',
      url: url,
      title: title,
      pageUrl: pageUrl || tab.url
    });

    // Show feedback
    showToast('📤 Sending to NAS...');

    // Refresh jobs after 2 seconds
    setTimeout(loadRecentJobs, 2000);

  } catch (error) {
    console.error('Error:', error);
    showToast('❌ Failed to send');
  }
}

// Copy to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('📋 Copied to clipboard');
  });
}

// Show toast notification
function showToast(message) {
  // Simple toast implementation
  const toast = document.createElement('div');
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 12px;
    z-index: 1000;
  `;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 2000);
}

// Utility functions
function truncateUrl(url, maxLength = 60) {
  if (url.length <= maxLength) return url;
  return url.substring(0, maxLength) + '...';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Check if URL contains an IP address
function containsIpAddress(url) {
  // IPv4 pattern in query parameters: matches ?ip=114.24.18.78 or &ip=114.24.18.78
  const ipv4QueryPattern = /[?&]ip=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/;
  
  return ipv4QueryPattern.test(url);
}

// Auto-refresh jobs every 5 seconds
setInterval(loadRecentJobs, 5000);
