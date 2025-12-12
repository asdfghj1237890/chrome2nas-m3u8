// Sidepanel Script for Chrome2NAS Video Downloader

let settings = {};
let detectedUrls = [];
let jobs = [];
let expandedErrorIds = new Set(); // Track which error details are expanded

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
          <strong>IP-Restricted URL Detected</strong><br>
          This URL contains an IP address, meaning the website restricts downloads to that specific IP. 
          To download successfully, your NAS and PC must use the same IP address. 
          Use Tailscale exit node or similar VPN solution to route the traffic through a same IP address.
        </div>
      ` : ''}
      <div class="url-actions">
        <button class="btn-send" data-url="${escapeHtml(urlInfo.url)}" data-page="${escapeHtml(urlInfo.pageUrl || '')}">
          Send to NAS
        </button>
        <button class="btn-copy" data-url="${escapeHtml(urlInfo.url)}">
          Copy
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

// Render jobs with smart update to avoid flickering
function renderJobs() {
  const listElement = document.getElementById('recentJobsList');
  const currentJobIds = new Set(jobs.map(j => j.id));

  // 1. Handle Empty State
  if (jobs.length === 0) {
    if (!listElement.querySelector('.empty-state')) {
      listElement.innerHTML = `
        <div class="empty-state">
          <p>No recent downloads</p>
        </div>
      `;
    }
    return;
  }

  // Remove empty state if present
  const emptyState = listElement.querySelector('.empty-state');
  if (emptyState) emptyState.remove();

  // 2. Update/Create items
  jobs.forEach((job, index) => {
    let itemEl = document.getElementById(`job-${job.id}`);

    // Create if not exists
    if (!itemEl) {
      itemEl = document.createElement('div');
      itemEl.className = 'job-item';
      itemEl.id = `job-${job.id}`;
      
      // Insert at correct position
      const nextSibling = listElement.children[index];
      if (nextSibling) {
        listElement.insertBefore(itemEl, nextSibling);
      } else {
        listElement.appendChild(itemEl);
      }
      
      // Initial Render
      itemEl.innerHTML = getJobInnerHtml(job);
      bindJobEvents(itemEl, job.id);
    } else {
      // Update existing
      const oldStatus = itemEl.dataset.status;
      const oldProgress = itemEl.dataset.progress;

      // Update data attributes
      itemEl.dataset.status = job.status;
      itemEl.dataset.progress = job.progress;
      
      // Check if full re-render is needed (structure change)
      if (shouldFullRender(oldStatus, job.status)) {
         itemEl.innerHTML = getJobInnerHtml(job);
         bindJobEvents(itemEl, job.id);
      } else {
         // Minimal update (progress bar, text only)
         updateJobElement(itemEl, job);
      }
      
      // Ensure element is in correct position (if list order changed)
      const currentIdx = Array.from(listElement.children).indexOf(itemEl);
      if (currentIdx !== index) {
         const nextSibling = listElement.children[index];
         if (nextSibling) {
            listElement.insertBefore(itemEl, nextSibling);
         } else {
            listElement.appendChild(itemEl);
         }
      }
    }
  });

  // 3. Remove old items
  Array.from(listElement.children).forEach(child => {
    if (child.id.startsWith('job-') && !currentJobIds.has(child.id.replace('job-', ''))) {
      child.remove();
    }
  });
}

// Generate inner HTML for a job item
function getJobInnerHtml(job) {
  const canCancel = ['pending', 'downloading', 'processing'].includes(job.status);
  const showProgress = job.status === 'downloading' || job.status === 'processing';
  const isFailed = job.status === 'failed';
  const errorInfo = isFailed ? getErrorInfo(job.error_message) : null;
  const statusTooltip = (job.status === 'completed' && typeof job.duration === 'number')
    ? `Duration: ${formatDuration(job.duration)}`
    : '';

  return `
    <div class="job-header">
      <div class="job-title" title="${escapeHtml(job.title)}">${escapeHtml(job.title)}</div>
      <div class="job-status ${job.status}" ${statusTooltip ? `title="${escapeHtml(statusTooltip)}"` : ''}>${getStatusLabel(job.status)}</div>
    </div>
    ${showProgress || canCancel ? `
      <div class="job-progress">
        ${showProgress ? `
          <div class="progress-container">
            <div class="progress-fill" style="width: ${job.progress}%"></div>
          </div>
          <div class="progress-text">${job.progress}%</div>
        ` : ''}
        ${canCancel ? `
          <button class="btn-cancel" data-job-id="${job.id}" title="Cancel download">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="m15 9-6 6M9 9l6 6"/>
            </svg>
            <span>Cancel</span>
          </button>
        ` : ''}
      </div>
    ` : ''}
    ${isFailed && errorInfo ? `
      <details class="error-details" data-job-id="${job.id}" ${expandedErrorIds.has(job.id) ? 'open' : ''}>
        <summary class="error-summary">
          <div class="error-icon">!</div>
          <span class="error-type">${escapeHtml(errorInfo.type)}</span>
          <span class="error-expand-icon">▶</span>
        </summary>
        <div class="error-content">
          <div class="error-message">${escapeHtml(errorInfo.message)}</div>
          <div class="error-solution">
            <div class="error-solution-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2a6 6 0 0 1 6 6c0 7-3 9-3 9h-6s-3-2-3-9a6 6 0 0 1 6-6Z"/>
                <path d="M9 18h6"/>
                <path d="M10 22h4"/>
              </svg>
              Suggested Solution
            </div>
            <div class="error-solution-text">${errorInfo.solution}</div>
          </div>
        </div>
      </details>
    ` : ''}
  `;
}

// Check if full re-render is needed
function shouldFullRender(oldStatus, newStatus) {
  // If status changed to/from 'downloading'/'processing' (progress bar visibility changes)
  const hasProgress = s => ['downloading', 'processing'].includes(s);
  const isFailed = s => s === 'failed';
  
  if (oldStatus !== newStatus) {
    if (hasProgress(oldStatus) !== hasProgress(newStatus)) return true;
    if (isFailed(oldStatus) !== isFailed(newStatus)) return true;
    if (['pending', 'completed', 'cancelled'].includes(newStatus)) return true;
  }
  
  return false;
}

// Update existing element without re-rendering HTML
function updateJobElement(el, job) {
  // Update status label
  const statusEl = el.querySelector('.job-status');
  if (statusEl) {
    statusEl.className = `job-status ${job.status}`;
    statusEl.textContent = getStatusLabel(job.status);
    const statusTooltip = (job.status === 'completed' && typeof job.duration === 'number')
      ? `Duration: ${formatDuration(job.duration)}`
      : '';
    if (statusTooltip) {
      statusEl.setAttribute('title', statusTooltip);
    } else {
      statusEl.removeAttribute('title');
    }
  }
  
  // Update progress bar
  const fillEl = el.querySelector('.progress-fill');
  const textEl = el.querySelector('.progress-text');
  if (fillEl) fillEl.style.width = `${job.progress}%`;
  if (textEl) textEl.textContent = `${job.progress}%`;
}

// Bind events to job item elements
function bindJobEvents(el, jobId) {
  const cancelBtn = el.querySelector('.btn-cancel');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => cancelJob(jobId));
  }
  
  const details = el.querySelector('.error-details');
  if (details) {
    details.addEventListener('toggle', (e) => {
      if (e.target.open) {
        expandedErrorIds.add(jobId);
      } else {
        expandedErrorIds.delete(jobId);
      }
    });
  }
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
    showToast('Sending to NAS...');

    // Refresh jobs after 2 seconds
    setTimeout(loadRecentJobs, 2000);

  } catch (error) {
    console.error('Error:', error);
    showToast('Failed to send');
  }
}

// Cancel job on NAS
async function cancelJob(jobId) {
  if (!settings.nasEndpoint || !settings.apiKey) {
    showToast('❌ NAS not configured');
    return;
  }

  try {
    const response = await fetch(`${settings.nasEndpoint}/api/jobs/${jobId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${settings.apiKey}`
      }
    });

    if (response.ok) {
      showToast('Job cancelled');
      // Refresh jobs list
      await loadRecentJobs();
    } else {
      const error = await response.json();
      showToast(`${error.detail || 'Failed to cancel'}`);
    }
  } catch (error) {
    console.error('Error cancelling job:', error);
    showToast('Failed to cancel job');
  }
}

// Copy to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard');
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

function getStatusLabel(status) {
  const labels = {
    'pending': 'Pending',
    'downloading': 'Downloading',
    'processing': 'Processing',
    'completed': 'Completed',
    'failed': 'Failed',
    'cancelled': 'Cancelled'
  };
  return labels[status] || status;
}

// Parse error message and return type, message, and solution
function getErrorInfo(errorMessage) {
  if (!errorMessage) {
    return {
      type: 'Unknown Error',
      message: 'No error details available',
      solution: 'Try again or check the NAS logs for more information.'
    };
  }

  const msg = errorMessage.toLowerCase();

  // 403 Forbidden - IP restriction or authentication issue
  if (msg.includes('403') || msg.includes('forbidden')) {
    return {
      type: 'Access Denied (403)',
      message: errorMessage,
      solution: `This website likely uses <strong>IP-based authentication</strong>. The video URL was generated for your PC's IP address, but your NAS has a different IP.
        <ul>
          <li>Use <strong>Tailscate Exit Node</strong> to route NAS traffic through your PC</li>
          <li>Run the downloader on your local PC instead of NAS</li>
          <li>Use a VPN to give both devices the same public IP</li>
        </ul>`
    };
  }

  // 404 Not Found
  if (msg.includes('404') || msg.includes('not found')) {
    return {
      type: 'Not Found (404)',
      message: errorMessage,
      solution: `The video URL is no longer valid.
        <ul>
          <li>The URL has expired</li>
          <li>The video was removed</li>
          <li>The link is temporary and needs to be refreshed</li>
        </ul>
        Try refreshing the video page and sending a new download request.`
    };
  }

  // Timeout errors
  if (msg.includes('timeout') || msg.includes('timed out')) {
    return {
      type: 'Connection Timeout',
      message: errorMessage,
      solution: `The connection to the video server timed out.
        <ul>
          <li>Check your NAS network connection</li>
          <li>The video server might be slow or overloaded</li>
          <li>Try again later</li>
        </ul>`
    };
  }

  // SSL/TLS errors
  if (msg.includes('ssl') || msg.includes('certificate') || msg.includes('tls')) {
    return {
      type: 'SSL/TLS Error',
      message: errorMessage,
      solution: `There was a problem with the secure connection.
        <ul>
          <li>Check if your NAS system time is correct</li>
          <li>The website might have an invalid certificate</li>
          <li>Try updating the downloader to the latest version</li>
        </ul>`
    };
  }

  // Connection errors
  if (msg.includes('connection') || msg.includes('network') || msg.includes('unreachable')) {
    return {
      type: 'Connection Error',
      message: errorMessage,
      solution: `Could not connect to the video server.
        <ul>
          <li>Check your NAS internet connection</li>
          <li>The video server might be down</li>
          <li>Check if your NAS can access external websites</li>
        </ul>`
    };
  }

  // No segments found
  if (msg.includes('no segments') || msg.includes('empty playlist')) {
    return {
      type: 'Invalid Playlist',
      message: errorMessage,
      solution: `The m3u8 playlist is empty or invalid.
        <ul>
          <li>The video requires authentication</li>
          <li>The playlist URL is incomplete</li>
          <li>The video format is not supported</li>
        </ul>`
    };
  }

  // Generic error
  return {
    type: 'Download Failed',
    message: errorMessage,
    solution: `An error occurred during download.
      <ul>
        <li>Check NAS logs for more details</li>
        <li>Try refreshing the video page and resending</li>
        <li>Some websites have download protection that cannot be bypassed</li>
      </ul>`
  };
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const seconds = s % 60;
  const mm = String(minutes).padStart(2, '0');
  const ss = String(seconds).padStart(2, '0');
  if (hours > 0) {
    const hh = String(hours).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  }
  return `${mm}:${ss}`;
}

// Check if URL contains an IP address
function containsIpAddress(url) {
  // IPv4 pattern in query parameters: matches ?ip=114.24.18.78 or &ip=114.24.18.78
  const ipv4QueryPattern = /[?&]ip=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/;
  
  return ipv4QueryPattern.test(url);
}

// Auto-refresh jobs every 5 seconds
setInterval(loadRecentJobs, 5000);
