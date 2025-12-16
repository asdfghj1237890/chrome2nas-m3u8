# WebVideo2NAS（繁體中文）

**English**: `README.md`

> 透過 Chrome 擷取網頁影片（M3U8 / MP4）URL，一鍵送到 NAS，由 NAS 自動下載並轉成 MP4 保存。

> [!IMPORTANT]
> 本專案**不保證**所有影片都能下載。部分網站可能有 DRM、URL 失效、防盜連、IP 限制或隨時調整傳輸邏輯。

> [!CAUTION]
> **不建議**把服務直接暴露在公網。建議只在 **LAN** 使用或透過 **VPN**（例如 Tailscale）存取 NAS。

## 快速連結
- **安裝（Installation）**：見下方（含 Synology 與非 Synology 分流）
- **完整文件（英文）**：請看 `README.md` 與 `docs/`

## 📦 安裝（Installation）

你會做 3 件事：
1. **部署後端到 NAS/Server**（Synology 或 非 Synology 擇一）
2. **安裝 + 設定 Chrome Extension**
3. **驗證是否正常**

### Step 1：部署後端（請選其中一條）

<details>
<summary><strong>Synology NAS（DSM / Container Manager）— UI 方式</strong></summary>

#### 1. 安裝 Container Manager
1. 開啟 **Package Center**
2. 安裝 **Container Manager**

#### 2. 準備資料夾（DSM UI）
1. 開啟 **File Station**
2. 專案資料夾（例）：`/volume1/docker/video-downloader/`
3. 下載資料夾（例）：`/volume1/<你的共享資料夾名稱>/downloads/completed`
4. 確認你在 Container Manager 執行 Project 使用的帳號，對這兩個資料夾都有 **讀/寫** 權限
   - 如果之後出現權限錯誤（寫不進 `/downloads`），回來檢查 DSM 資料夾權限，並先嘗試在下載資料夾手動建立一個測試檔案確認可寫入

#### 3. 下載並解壓縮 release（DSM UI）
1. 從 GitHub Releases 下載 `WebVideo2NAS-downloader-docker.zip`
2. 用 File Station 上傳到 `/volume1/docker/` 並解壓縮
3. 解壓後應該會有：`/volume1/docker/video-downloader/docker/`

#### 4. 建立 `.env`（新手只要改 2 個值）
在 `/volume1/docker/video-downloader/docker/.env` 建立檔案（DSM 文字編輯器，或在 PC 編輯後上傳）：

```bash
DB_PASSWORD=your_secure_password_here
API_KEY=your_api_key_minimum_32_chars
MAX_DOWNLOAD_WORKERS=20
MAX_RETRY_ATTEMPTS=3
FFMPEG_THREADS=2
LOG_LEVEL=INFO
ALLOWED_ORIGINS=chrome-extension://*
CORS_ALLOW_CREDENTIALS=false

# Security
RATE_LIMIT_PER_MINUTE=10
ALLOWED_CLIENT_CIDRS=
SSRF_GUARD=false

# Optional
# INSECURE_SKIP_TLS_VERIFY=0
# SSL_VERIFY=1
```

#### 5. 用 Projects 部署（DSM UI）
1. 到 `/volume1/docker/video-downloader/docker/`
2. 把 `docker-compose.synology.yml` 改名成 `docker-compose.yml`
3. 開啟 **Container Manager → Projects → Create**
4. 專案資料夾選：`/volume1/docker/video-downloader/docker`
5. 完成精靈並啟動 Project

#### 6. 驗證
開啟 `http://YOUR_SYNOLOGY_IP:52052/api/health`，應回傳 `{"status":"healthy"}`

</details>

<details>
<summary><strong>非 Synology / 標準 Docker（Linux / Server）— 指令方式</strong></summary>

#### 1. 下載並解壓縮 release
```bash
wget https://github.com/asdfghj1237890/WebVideo2NAS/releases/latest/download/WebVideo2NAS-downloader-docker.zip
mkdir -p docker
cd docker
unzip ../WebVideo2NAS-downloader-docker.zip
cd video-downloader/docker
mkdir -p ../logs ../downloads/completed
```

#### 2. 建立 `.env`（新手只要改 2 個值）
```bash
API_KEY=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 24)

# 如果你的環境沒有 openssl，也可以自己手動填入 API_KEY/DB_PASSWORD（用夠長、夠隨機的字串即可）
cat > .env << EOF
DB_PASSWORD=${DB_PASSWORD}
API_KEY=${API_KEY}
MAX_DOWNLOAD_WORKERS=20
MAX_RETRY_ATTEMPTS=3
FFMPEG_THREADS=2
LOG_LEVEL=INFO
ALLOWED_ORIGINS=chrome-extension://*
CORS_ALLOW_CREDENTIALS=false
RATE_LIMIT_PER_MINUTE=10
ALLOWED_CLIENT_CIDRS=
SSRF_GUARD=false
EOF

echo "你的 API Key：${API_KEY}"
```

#### 3. 部署與驗證
```bash
docker-compose up -d
curl http://localhost:52052/api/health
```

（其他 Linux 發行版細節請看 `README.md`）

</details>

### Step 2：安裝 + 設定 Chrome Extension
1. 打開 `chrome://extensions/`
2. 開啟 **Developer mode**
3. **Load unpacked**，選擇 `chrome-extension` 資料夾
4. 設定：
   - **NAS Endpoint**：`http://YOUR_NAS_IP:52052`（請填 NAS/Server 的區網 IP；不要填 `localhost`）
   - **API Key**：填入 `.env` 的 `API_KEY`

### Step 3：如果不會用／出錯
- 使用方式：看 `README.md` 的 **Usage**
- 疑難排解：看 `README.md` 的 **Troubleshooting**
- 參數設定：看 `README.md` 的 **Configuration**

## 需要更完整的內容？
- 詳細安裝、設定、疑難排解與安全建議：請看 `README.md`

