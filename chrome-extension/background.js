// Background Service Worker for M3U8 Detection and Download Management

// Store detected m3u8 URLs
let detectedUrls = new Set();
let currentTabUrls = {};

// Listen for web requests to detect m3u8 URLs
chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    const url = details.url;
    
    // Check if URL contains .m3u8
    if (url.includes('.m3u8')) {
      console.log('Detected m3u8 URL:', url);
      
      // Store URL with tab info
      const urlInfo = {
        url: url,
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
  
  // Check if it's an m3u8 URL
  if (url && url.includes('.m3u8')) {
    sendToNAS(url, tab.title, tab.url);
  } else {
    // Try to find m3u8 URL in current tab
    const tabUrls = currentTabUrls[tab.id];
    if (tabUrls && tabUrls.length > 0) {
      // Send the most recent m3u8 URL
      const latest = tabUrls[tabUrls.length - 1];
      sendToNAS(latest.url, tab.title, tab.url);
    } else {
      showNotification('Error', 'No m3u8 URL found on this page');
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
    
    // Prepare request
    const requestBody = {
      url: url,
      title: title,
      source_page: pageUrl,
      referer: pageUrl
    };
    
    console.log('Sending to NAS:', requestBody);
    
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

console.log('Chrome2NAS M3U8 Downloader background service worker loaded');
