// Background Service Worker for Video Detection and Download Management

// Store detected video URLs (m3u8, mp4)
let detectedUrls = new Set();
let currentTabUrls = {};

// Store captured request headers for m3u8 URLs
let capturedHeaders = {};

// Listen for web requests to detect video URLs (m3u8, mp4)
chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    const urlLower = details.url.toLowerCase();
    
    // Check if URL contains video file extensions
    const isVideo = urlLower.includes('.m3u8') || urlLower.includes('.mp4');
    if (isVideo) {
      console.log('Detected video URL:', details.url);
      
      // Store URL with tab info (preserve original URL case)
      const urlInfo = {
        url: details.url,
        tabId: details.tabId,
        timestamp: Date.now(),
        pageUrl: details.initiator || details.documentUrl
      };
      
      // Add to detected URLs
      detectedUrls.add(JSON.stringify(urlInfo));
      
      // Store for current tab
      if (!currentTabUrls[details.tabId]) {
        currentTabUrls[details.tabId] = [];
      }
      currentTabUrls[details.tabId].push(urlInfo);
      
      // Update badge
      updateBadge(details.tabId);
      
      // Store in chrome.storage for popup access
      chrome.storage.local.set({ detectedUrls: Array.from(detectedUrls) });
    }
  },
  { urls: ["<all_urls>"] }
);

// Capture actual request headers sent by the browser for video URLs
// This includes cookies that Chrome would send to the video domain
chrome.webRequest.onSendHeaders.addListener(
  function(details) {
    const urlLower = details.url.toLowerCase();
    
    // Only capture headers for video URLs
    if (urlLower.includes('.m3u8') || urlLower.includes('.mp4')) {
      // Convert headers array to object
      const headersObj = {};
      if (details.requestHeaders) {
        for (const header of details.requestHeaders) {
          // Skip some internal headers
          if (!header.name.toLowerCase().startsWith(':')) {
            headersObj[header.name] = header.value;
          }
        }
      }
      
      // Store headers keyed by URL
      capturedHeaders[details.url] = {
        headers: headersObj,
        timestamp: Date.now(),
        initiator: details.initiator || details.documentUrl,
        tabId: details.tabId
      };
      
      console.log('Captured headers for:', details.url);
      console.log('Headers:', headersObj);
      console.log('Has Cookie header:', !!headersObj['Cookie']);
      if (headersObj['Cookie']) {
        console.log('Cookie value:', headersObj['Cookie']);
      }
      
      // Clean up old entries (keep only last 100)
      const keys = Object.keys(capturedHeaders);
      if (keys.length > 100) {
        const oldest = keys.sort((a, b) => 
          capturedHeaders[a].timestamp - capturedHeaders[b].timestamp
        ).slice(0, keys.length - 100);
        oldest.forEach(k => delete capturedHeaders[k]);
      }
    }
  },
  { urls: ["<all_urls>"] },
  ["requestHeaders", "extraHeaders"]
);

// Update badge with count of detected URLs
function updateBadge(tabId) {
  const count = currentTabUrls[tabId]?.length || 0;
  if (count > 0) {
    chrome.action.setBadgeText({ text: count.toString(), tabId: tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#4CAF50', tabId: tabId });
  }
}

// Clean up when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  delete currentTabUrls[tabId];
});

// Clear detected URLs when page navigates or reloads
chrome.webNavigation.onCommitted.addListener((details) => {
  if (details.frameId === 0) { // Only for main frame
    // Clear URLs for this tab on navigation/reload
    currentTabUrls[details.tabId] = [];
    updateBadge(details.tabId);
    chrome.storage.local.set({ detectedUrls: Array.from(detectedUrls) });
  }
});

// Create context menu
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "sendToNAS",
    title: "Send to NAS",
    contexts: ["link", "page"]
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  let url = info.linkUrl || info.pageUrl;
  
  // Check if it's a video URL (m3u8 or mp4)
  const urlLower = url ? url.toLowerCase() : '';
  const isVideoUrl = urlLower.includes('.m3u8') || urlLower.includes('.mp4');
  if (url && isVideoUrl) {
    sendToNAS(url, tab.title, tab.url);
  } else {
    // Try to find video URL in current tab
    const tabUrls = currentTabUrls[tab.id];
    if (tabUrls && tabUrls.length > 0) {
      // Send the most recent video URL
      const latest = tabUrls[tabUrls.length - 1];
      sendToNAS(latest.url, tab.title, tab.url);
    } else {
      showNotification('Error', 'No video URL found on this page');
    }
  }
});

// Send URL to NAS
async function sendToNAS(url, pageTitle, pageUrl) {
  try {
    // Get settings
    const settings = await chrome.storage.sync.get(['nasEndpoint', 'apiKey']);
    
    if (!settings.nasEndpoint || !settings.apiKey) {
      showNotification('Configuration Required', 'Please configure NAS settings in extension options');
      chrome.runtime.openOptionsPage();
      return;
    }
    
    // Extract title from page title or URL
    let title = pageTitle || 'Untitled Video';
    // Clean up title
    title = title.replace(/[<>:"/\\|?*]/g, '').substring(0, 100);
    
    // First, try to use captured headers for this exact URL
    let finalHeaders = {};
    const captured = capturedHeaders[url];
    
    if (captured && captured.headers) {
      console.log('Using captured browser headers for:', url);
      finalHeaders = { ...captured.headers };
      
      // Remove headers that shouldn't be forwarded
      delete finalHeaders['Host'];
      delete finalHeaders['Connection'];
      delete finalHeaders['Content-Length'];
      delete finalHeaders['Accept-Encoding']; // Let the worker handle compression
    }
    
    // Also get cookies for the source page domain (fallback)
    try {
      const pageUrlObj = new URL(pageUrl);
      const pageCookies = await chrome.cookies.getAll({ url: pageUrl });
      
      console.log(`Getting cookies for source page: ${pageUrl}`);
      console.log(`Found ${pageCookies.length} cookies`);
      
      // If we don't have captured cookies, use page cookies
      if (!finalHeaders['Cookie'] && pageCookies.length > 0) {
        finalHeaders['Cookie'] = pageCookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ');
        console.log('Using source page cookies as fallback');
      }
    } catch (error) {
      console.error('Failed to get page cookies:', error);
    }
    
    // Also get cookies for the m3u8 URL domain
    try {
      const m3u8UrlObj = new URL(url);
      const m3u8Cookies = await chrome.cookies.getAll({ url: url });
      
      console.log(`Getting cookies for m3u8 URL: ${url}`);
      console.log(`Found ${m3u8Cookies.length} cookies for m3u8 domain`);
      
      if (m3u8Cookies.length > 0) {
        const m3u8CookieStr = m3u8Cookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ');
        // Merge with existing cookies if any
        if (finalHeaders['Cookie']) {
          // Combine both, avoiding duplicates
          const existingCookies = new Set(finalHeaders['Cookie'].split('; '));
          m3u8CookieStr.split('; ').forEach(c => existingCookies.add(c));
          finalHeaders['Cookie'] = Array.from(existingCookies).join('; ');
        } else {
          finalHeaders['Cookie'] = m3u8CookieStr;
        }
        console.log('Added m3u8 domain cookies');
      }
    } catch (error) {
      console.error('Failed to get m3u8 domain cookies:', error);
    }
    
    // Prepare request body
    const requestBody = {
      url: url,
      title: title,
      source_page: pageUrl,
      referer: pageUrl,
      headers: finalHeaders
    };
    
    console.log('Sending to NAS:');
    console.log('  URL:', requestBody.url);
    console.log('  Title:', requestBody.title);
    console.log('  Referer:', requestBody.referer);
    console.log('  Headers keys:', Object.keys(requestBody.headers));
    console.log('  Has Cookie:', !!requestBody.headers.Cookie);
    if (requestBody.headers.Cookie) {
      console.log('  Cookie preview:', requestBody.headers.Cookie.substring(0, 200));
    }
    
    // Send to NAS API
    const response = await fetch(`${settings.nasEndpoint}/api/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${settings.apiKey}`
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit download');
    }
    
    const result = await response.json();
    console.log('Download submitted:', result);
    
    // Show success notification
    showNotification(
      'Download Submitted',
      `"${title}" has been sent to NAS\nJob ID: ${result.id.substring(0, 8)}...`
    );
    
    // Store job info
    storeJob(result);
    
  } catch (error) {
    console.error('Error sending to NAS:', error);
    showNotification('Error', error.message);
  }
}

// Show notification
function showNotification(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: title,
    message: message
  });
}

// Store job information
async function storeJob(job) {
  const jobs = await chrome.storage.local.get(['jobs']);
  const jobList = jobs.jobs || [];
  
  jobList.unshift({
    id: job.id,
    title: job.title,
    url: job.url,
    status: job.status,
    progress: job.progress,
    created_at: new Date().toISOString()
  });
  
  // Keep only last 50 jobs
  if (jobList.length > 50) {
    jobList.pop();
  }
  
  await chrome.storage.local.set({ jobs: jobList });
}

// Listen for action clicks to open sidepanel
chrome.action.onClicked.addListener(async (tab) => {
  // Open sidepanel when extension icon is clicked
  await chrome.sidePanel.open({ tabId: tab.id });
});

// Listen for messages from sidepanel
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getDetectedUrls') {
    // Return URLs for current active tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        const urls = currentTabUrls[tabs[0].id] || [];
        sendResponse({ urls: urls });
      } else {
        sendResponse({ urls: [] });
      }
    });
    return true; // Keep channel open for async response
  }

  if (request.action === 'sendToNAS') {
    sendToNAS(request.url, request.title, request.pageUrl);
    sendResponse({ success: true });
  }

  if (request.action === 'clearDetected') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        currentTabUrls[tabs[0].id] = [];
        updateBadge(tabs[0].id);
      }
    });
    sendResponse({ success: true });
  }

});

console.log('Chrome2NAS Video Downloader background service worker loaded');
