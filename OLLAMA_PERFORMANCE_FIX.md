# Ollama Performance Issue and Solutions

**Date:** October 22, 2025
**Issue:** Q&A endpoint (`/api/ask`) timing out in production (504 Gateway Timeout) and extremely slow locally

---

## Root Cause Analysis

### Issue #1: Wrong Model Configuration ✅ FIXED
**Problem:** Backend was configured to use `llama3.2:1b` but Ollama only had `llama3.2:latest` (3.2B parameters) installed.

**Symptoms:**
- 404 errors in Ollama logs: `model "llama3.2:1b" not found`
- Backend errors: `Failed to generate embedding` and `Failed to answer question`

**Fix Applied:**
Updated `backend/config.py` line 55:
```python
# Before
ollama_model: str = "llama3.2:1b"

# After
ollama_model: str = "llama3.2:latest"
```

### Issue #2: Slow CPU Inference ⚠️ UNRESOLVED
**Problem:** Ollama running on CPU with a 3.2B parameter model is extremely slow.

**Symptoms:**
- Local: Q&A requests take 60+ seconds (still processing after 1.5+ minutes)
- Production: 504 Gateway Timeout (nginx default timeout ~60 seconds)
- CPU usage: 800%+ (using 8+ cores)
- Memory usage: 2.5GB

**Evidence:**
```bash
# Docker stats show heavy CPU usage
CONTAINER ID   NAME             CPU %     MEM USAGE / LIMIT     MEM %
32a0478ecfb6   mongado-ollama   828.04%   2.492GiB / 7.751GiB   32.14%

# Logs show CPU backend
mongado-ollama | load_backend: loaded CPU backend from /usr/lib/ollama/libggml-cpu.so
```

---

## Solutions (Pick One)

### Option 1: Use a Smaller, Faster Model ⭐ RECOMMENDED
Switch to a smaller 1B parameter model which will be 3x faster on CPU.

**Steps:**
1. Pull the 1B model:
   ```bash
   docker exec mongado-ollama ollama pull llama3.2:1b
   ```

2. Update config (already set to `llama3.2:latest`, no change needed):
   ```bash
   # backend/.env or docker-compose.yml
   OLLAMA_MODEL=llama3.2:1b
   ```

3. Restart backend:
   ```bash
   docker compose restart backend
   ```

**Trade-offs:**
- ✅ Faster inference (1-2 minutes → 20-40 seconds)
- ✅ Lower memory usage (~1GB instead of 2.5GB)
- ✅ Works on CPU-only machines
- ⚠️ Slightly lower quality responses (but still good for personal knowledge base)

---

### Option 2: Enable GPU Acceleration 🚀 BEST PERFORMANCE
If you have an NVIDIA GPU, enable GPU acceleration for 10-100x speedup.

**Steps:**
1. Install NVIDIA Container Toolkit on host:
   ```bash
   # Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

2. Update `docker-compose.yml` to use GPU:
   ```yaml
   ollama:
     image: ollama/ollama:latest
     container_name: mongado-ollama
     restart: unless-stopped
     volumes:
       - ./data/ollama:/root/.ollama
     networks:
       - mongado-network
     deploy:
       resources:
         reservations:
           devices:
             - driver: nvidia
               count: all
               capabilities: [gpu]
   ```

3. Restart Ollama:
   ```bash
   docker compose down
   docker compose up -d
   ```

**Trade-offs:**
- ✅ 10-100x faster inference (1-2 minutes → 1-5 seconds)
- ✅ Can use larger, higher-quality models
- ✅ Better user experience
- ❌ Requires NVIDIA GPU
- ❌ Additional setup complexity

---

### Option 3: Increase Nginx Timeout (Production Only)
If you want to keep the current setup but allow longer processing times.

**Steps:**
1. Update nginx config on production server:
   ```nginx
   server {
       server_name api.mongado.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_read_timeout 300s;  # 5 minutes
           proxy_connect_timeout 300s;
           proxy_send_timeout 300s;
       }
   }
   ```

2. Reload nginx:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

**Trade-offs:**
- ✅ Simple configuration change
- ✅ No code changes needed
- ⚠️ Users will experience 2-5 minute wait times
- ⚠️ Poor user experience
- ⚠️ Doesn't fix local development slowness

---

### Option 4: Use External AI API
Replace Ollama with a cloud AI service (OpenAI, Anthropic, etc.).

**Steps:**
1. Update `backend/config.py` to use external API
2. Modify `ollama_client.py` to call external service instead
3. Add API key to 1Password

**Trade-offs:**
- ✅ Instant responses (200-500ms)
- ✅ Higher quality responses
- ✅ No hardware requirements
- ❌ Monthly API costs ($5-50/month depending on usage)
- ❌ Requires internet connection
- ❌ Data sent to third party

---

## Recommendation

**For Local Development:**
→ **Option 1** (smaller model) for immediate improvement

**For Production:**
→ **Option 2** (GPU) if you have/can add a GPU to your server
→ **Option 4** (external API) if GPU not available and you want good performance
→ **Option 1** (smaller model) + **Option 3** (longer timeout) as temporary workaround

---

## Testing After Fix

Once you've applied a solution, test the Q&A endpoint:

```bash
# Local
curl -X POST http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "Why did the chicken cross the road?"}'

# Production
curl -X POST https://api.mongado.com/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "Why did the chicken cross the road?"}'
```

**Expected response time:**
- CPU + 1B model: 20-40 seconds
- GPU + 3.2B model: 2-5 seconds
- External API: <1 second

---

## Current Status

- ✅ **Model mismatch fixed** - Backend now uses `llama3.2:latest` correctly
- ⚠️ **Slow inference unresolved** - CPU inference with 3.2B model takes 60+ seconds
- ⚠️ **Production timeouts** - Nginx timing out after 60 seconds

**Next step:** Choose and implement one of the solutions above.
