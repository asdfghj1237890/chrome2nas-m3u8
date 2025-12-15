// Options Page Script for WebVideo2NAS

document.addEventListener('DOMContentLoaded', async () => {
  const i18n = (typeof window !== 'undefined' && window.WV2N_I18N) ? window.WV2N_I18N : null;
  const t = (key, vars) => (i18n ? i18n.t(key, vars) : key);
  const tHtml = (key, vars) => (i18n ? i18n.tHtml(key, vars) : t(key, vars));

  function applyUiLanguage(uiLanguageRaw) {
    if (!i18n) return;
    const uiLanguage = uiLanguageRaw === 'zh' ? 'zh-TW' : (uiLanguageRaw || '');
    i18n.setLanguage((uiLanguage || '').trim());
    localizeStaticText();
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function localizeStaticText() {
    document.title = t('options.pageTitle');
    setText('optionsSubtitle', t('options.subtitle'));

    setText('nasConfigTitle', t('options.nasConfig.title'));
    setText('nasEndpointLabel', t('options.nasEndpoint.label'));
    setHtml('nasEndpointHelp', t('options.nasEndpoint.helpHtml'));

    setText('apiKeyLabel', t('options.apiKey.label'));
    setHtml('apiKeyHelp', t('options.apiKey.helpHtml'));

    setText('testBtnText', t('options.btn.test'));
    setText('saveBtnText', t('options.btn.save'));

    setText('downloadPreferencesTitle', t('options.downloadPreferences.title'));
    setText('uiLanguageLabel', t('options.uiLanguage.label'));
    setText('uiLanguageHelp', t('options.uiLanguage.help'));

    const autoOption = document.querySelector('#uiLanguage option[value=""]');
    if (autoOption) autoOption.textContent = t('options.uiLanguage.auto');

    setText('autoDetectLabel', t('options.autoDetect.label'));
    setText('autoDetectHelp', t('options.autoDetect.help'));
    setText('showNotificationsLabel', t('options.showNotifications.label'));
    setText('showNotificationsHelp', t('options.showNotifications.help'));

    setText('aboutTitle', t('options.about.title'));
    setText('aboutVersionLabel', t('options.about.version'));
    setText('aboutAuthorLabel', t('options.about.author'));
    setText('aboutAuthorValue', t('options.about.authorValue'));
    setText('aboutDescription', t('options.about.description'));

    setText('howToUseTitle', t('options.howToUse.title'));
    setText('howToUseStep1', t('options.howToUse.step1'));
    setText('howToUseStep2', t('options.howToUse.step2'));
    setText('howToUseStep3', t('options.howToUse.step3'));
    setText('howToUseStep4', t('options.howToUse.step4'));
    setText('howToUseStep5', t('options.howToUse.step5'));

    setText('needHelpTitle', t('options.needHelp.title'));
    setHtml('needHelpBody', t('options.needHelp.bodyHtml'));

    setText('footerText', t('options.footer'));
  }

  // Display extension version (keep in sync with manifest.json)
  const versionEl = document.getElementById('extVersion');
  if (versionEl) {
    versionEl.textContent = chrome.runtime.getManifest().version || '-';
  }

  // Load saved settings (includes uiLanguage)
  const settings = await chrome.storage.sync.get([
    'nasEndpoint',
    'apiKey',
    'autoDetect',
    'showNotifications',
    'uiLanguage'
  ]);

  // Apply language first, then render page copy.
  applyUiLanguage(settings.uiLanguage);

  // Populate inputs
  document.getElementById('nasEndpoint').value = settings.nasEndpoint || '';
  document.getElementById('apiKey').value = settings.apiKey || '';
  document.getElementById('autoDetect').checked = settings.autoDetect !== false;
  document.getElementById('showNotifications').checked = settings.showNotifications !== false;
  const uiLanguage = settings.uiLanguage === 'zh' ? 'zh-TW' : (settings.uiLanguage || '');
  document.getElementById('uiLanguage').value = uiLanguage;
  
  // Setup event listeners
  document.getElementById('saveBtn').addEventListener('click', saveSettings);
  document.getElementById('testBtn').addEventListener('click', testConnection);
  
  // Auto-save checkboxes
  document.getElementById('autoDetect').addEventListener('change', savePreferences);
  document.getElementById('showNotifications').addEventListener('change', savePreferences);
  document.getElementById('uiLanguage').addEventListener('change', async () => {
    await savePreferences();
    applyUiLanguage((document.getElementById('uiLanguage').value || '').trim());
  });

  // Keep these helpers accessible to functions below
  window.__WV2N_OPTIONS_I18N__ = { t, tHtml, applyUiLanguage };
});

// Save settings
async function saveSettings() {
  const t = (window.__WV2N_OPTIONS_I18N__ && window.__WV2N_OPTIONS_I18N__.t) ? window.__WV2N_OPTIONS_I18N__.t : (k => k);
  const nasEndpoint = document.getElementById('nasEndpoint').value.trim();
  const apiKey = document.getElementById('apiKey').value.trim();
  
  // Validation
  if (!nasEndpoint) {
    showStatus(t('options.status.enterNasEndpoint'), 'error');
    return;
  }
  
  if (!apiKey) {
    showStatus(t('options.status.enterApiKey'), 'error');
    return;
  }
  
  // Validate URL format
  try {
    const url = new URL(nasEndpoint);
    if (!url.protocol.startsWith('http')) {
      throw new Error('Invalid protocol');
    }
  } catch (error) {
    showStatus(t('options.status.invalidUrl'), 'error');
    return;
  }
  
  // Remove trailing slash
  const cleanEndpoint = nasEndpoint.replace(/\/$/, '');
  
  // Save to storage
  await chrome.storage.sync.set({
    nasEndpoint: cleanEndpoint,
    apiKey: apiKey
  });
  
  showStatus(t('options.status.saved'), 'success');
  
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
  const t = (window.__WV2N_OPTIONS_I18N__ && window.__WV2N_OPTIONS_I18N__.t) ? window.__WV2N_OPTIONS_I18N__.t : (k => k);
  const nasEndpoint = document.getElementById('nasEndpoint').value.trim();
  const apiKey = document.getElementById('apiKey').value.trim();
  
  if (!nasEndpoint || !apiKey) {
    showStatus(t('options.status.enterBoth'), 'error');
    return;
  }
  
  showStatus(t('options.status.testing'), 'info');
  
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
      showStatus(t('options.status.connectionOk'), 'success');
      
      // Also test the status endpoint
      const statusResponse = await fetch(`${nasEndpoint}/api/status`, {
        headers: {
          'Authorization': `Bearer ${apiKey}`
        }
      });
      
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        showStatus(
          t('options.status.connectedWithStats', { active: statusData.active_downloads, queue: statusData.queue_length }),
          'success'
        );
      }
    } else {
      throw new Error(t('options.status.unexpectedResponse'));
    }
    
  } catch (error) {
    console.error('Connection test failed:', error);
    
    let errorMessage = t('options.status.connectionFailedPrefix');
    
    if (error.message.includes('Failed to fetch')) {
      errorMessage += t('options.status.cannotReach');
    } else if (error.message.includes('401')) {
      errorMessage += t('options.status.invalidApiKey');
    } else if (error.message.includes('404')) {
      errorMessage += t('options.status.apiNotFound');
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
