// Options Page Script for WebVideo2NAS

document.addEventListener('DOMContentLoaded', async () => {
  // Display extension version (keep in sync with manifest.json)
  const versionEl = document.getElementById('extVersion');
  if (versionEl) {
    versionEl.textContent = chrome.runtime.getManifest().version || '-';
  }

  // Load saved settings
  loadSettings();
  
  // Setup event listeners
  document.getElementById('saveBtn').addEventListener('click', saveSettings);
  document.getElementById('testBtn').addEventListener('click', testConnection);
  
  // Auto-save checkboxes
  document.getElementById('autoDetect').addEventListener('change', savePreferences);
  document.getElementById('showNotifications').addEventListener('change', savePreferences);
  document.getElementById('uiLanguage').addEventListener('change', savePreferences);
});

// Load settings from storage
async function loadSettings() {
  const settings = await chrome.storage.sync.get([
    'nasEndpoint',
    'apiKey',
    'autoDetect',
    'showNotifications',
    'uiLanguage'
  ]);
  
  document.getElementById('nasEndpoint').value = settings.nasEndpoint || '';
  document.getElementById('apiKey').value = settings.apiKey || '';
  document.getElementById('autoDetect').checked = settings.autoDetect !== false;
  document.getElementById('showNotifications').checked = settings.showNotifications !== false;
  // Backward compatibility: previous versions used "zh" (treated as zh-TW now).
  const uiLanguage = settings.uiLanguage === 'zh' ? 'zh-TW' : (settings.uiLanguage || '');
  document.getElementById('uiLanguage').value = uiLanguage;
}

// Save settings
async function saveSettings() {
  const nasEndpoint = document.getElementById('nasEndpoint').value.trim();
  const apiKey = document.getElementById('apiKey').value.trim();
  
  // Validation
  if (!nasEndpoint) {
    showStatus('Please enter NAS endpoint URL', 'error');
    return;
  }
  
  if (!apiKey) {
    showStatus('Please enter API key', 'error');
    return;
  }
  
  // Validate URL format
  try {
    const url = new URL(nasEndpoint);
    if (!url.protocol.startsWith('http')) {
      throw new Error('Invalid protocol');
    }
  } catch (error) {
    showStatus('Invalid URL format. Use http:// or https://', 'error');
    return;
  }
  
  // Remove trailing slash
  const cleanEndpoint = nasEndpoint.replace(/\/$/, '');
  
  // Save to storage
  await chrome.storage.sync.set({
    nasEndpoint: cleanEndpoint,
    apiKey: apiKey
  });
  
  showStatus('✅ Settings saved successfully!', 'success');
  
  // Automatically test connection after save
  setTimeout(testConnection, 500);
}

// Save preferences
async function savePreferences() {
  const autoDetect = document.getElementById('autoDetect').checked;
  const showNotifications = document.getElementById('showNotifications').checked;
  const uiLanguage = (document.getElementById('uiLanguage').value || '').trim();
  
  await chrome.storage.sync.set({
    autoDetect: autoDetect,
    showNotifications: showNotifications,
    uiLanguage: uiLanguage
  });
}

// Test NAS connection
async function testConnection() {
  const nasEndpoint = document.getElementById('nasEndpoint').value.trim();
  const apiKey = document.getElementById('apiKey').value.trim();
  
  if (!nasEndpoint || !apiKey) {
    showStatus('Please enter both NAS endpoint and API key', 'error');
    return;
  }
  
  showStatus('🔍 Testing connection...', 'info');
  
  try {
    // Test health endpoint
    const response = await fetch(`${nasEndpoint}/api/health`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (data.status === 'healthy') {
      showStatus('✅ Connection successful! Your NAS is reachable.', 'success');
      
      // Also test the status endpoint
      const statusResponse = await fetch(`${nasEndpoint}/api/status`, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      });
      
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        showStatus(
          `✅ Connected! Active downloads: ${statusData.active_downloads}, Queue: ${statusData.queue_length}`,
          'success'
        );
      }
    } else {
      throw new Error('Unexpected response from NAS');
    }
    
  } catch (error) {
    console.error('Connection test failed:', error);
    
    let errorMessage = '❌ Connection failed: ';
    
    if (error.message.includes('Failed to fetch')) {
      errorMessage += 'Cannot reach NAS. Check IP address and port.';
    } else if (error.message.includes('401')) {
      errorMessage += 'Invalid API key.';
    } else if (error.message.includes('404')) {
      errorMessage += 'API endpoint not found. Check NAS configuration.';
    } else {
      errorMessage += error.message;
    }
    
    showStatus(errorMessage, 'error');
  }
}

// Show status message
function showStatus(message, type) {
  const statusEl = document.getElementById('statusMessage');
  statusEl.textContent = message;
  statusEl.className = `status-message ${type}`;
  statusEl.style.display = 'block';
  
  // Auto-hide success messages after 5 seconds
  if (type === 'success') {
    setTimeout(() => {
      statusEl.style.display = 'none';
    }, 5000);
  }
}
