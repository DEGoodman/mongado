# Local Development Performance Optimization

## Problem

Local development machines often have resource contention (IDEs, browsers, Slack, etc.) and Ollama AI features can max out CPU and memory.

## Quick Wins (Already Applied)

### 1. Neo4j Memory Tuning ✅

Reduced Neo4j memory from ~2.5GB to ~1GB:

```yaml
# docker-compose.yml (already configured)
environment:
  - NEO4J_dbms_memory_heap_initial__size=256m
  - NEO4J_dbms_memory_heap_max__size=512m
  - NEO4J_dbms_memory_pagecache_size=256m
```

**Impact**: Frees ~1.5GB RAM for Ollama and other apps.

### 2. Ollama Smart Model Caching ✅

Keeps models loaded for 5 minutes during development:

```yaml
# docker-compose.yml (already configured)
environment:
  - OLLAMA_MAX_LOADED_MODELS=1  # Only 1 model in memory
  - OLLAMA_NUM_PARALLEL=1        # No concurrent requests
  - OLLAMA_KEEP_ALIVE=5m         # Cache for 5min (vs 0 in prod)
```

**Impact**:
- ✅ Faster iteration (no model reload on each request)
- ✅ Limits memory to 1 model at a time
- ⚠️ Model unloads after 5min idle

---

## Optional: Further Optimizations

### 3. Reduce Context Window (CPU Savings)

If CPU is still maxing out, reduce the context window:

```bash
# In backend/.env or export in shell
export OLLAMA_NUM_CTX=1024  # Down from 2048 (saves CPU)
```

**Trade-off**:
- ✅ Faster inference (less tokens to process)
- ⚠️ Can't process very long articles (will truncate)

### 4. Enable Swap Space (Memory Safety Net)

If you're running out of RAM:

```bash
# macOS (not recommended - use Activity Monitor to check first)
# macOS handles swap automatically, don't configure manually

# Linux
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

**Note**: Only needed if you see OOM errors. Check available RAM first:
```bash
# macOS
vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+([^:]+)[^\d]+(\d+)/ and printf("%-16s % 16.2f Mi\n", "$1:", $2 * $size / 1048576);'

# Linux
free -h
```

---

## Monitoring Resource Usage

### Check Docker Container Memory

```bash
# See which containers are using the most resources
docker stats --no-stream

# Watch continuously
docker stats
```

### Expected Resource Profile (After Optimizations)

```
CONTAINER           MEM USAGE       MEM %
mongado-neo4j       ~500MB-800MB    (tuned from ~2GB)
mongado-ollama      ~1.5GB          (when model loaded)
mongado-backend     ~200MB-300MB
mongado-frontend    ~100MB-200MB
```

### Monitor CPU Usage

```bash
# macOS
top -o cpu

# Linux
htop  # Install: sudo apt-get install htop
```

**When Ollama is generating**:
- CPU spike to 80-100% for 5-15s is normal
- Should drop after generation completes
- If stays high, check for background processes

---

## Troubleshooting

### Problem: Still maxing out CPU during requests

**Diagnosis**:
```bash
# Check which process is using CPU
docker stats
```

**Solutions**:
1. Reduce context window (see #3 above)
2. Ensure only 1 request at a time (already configured)
3. Check if browser dev tools are open (high overhead)
4. Close other resource-intensive apps during testing

### Problem: Out of memory errors

**Diagnosis**:
```bash
docker compose logs ollama | grep -i "memory"
```

**Solutions**:
1. Restart Docker to clear memory: `docker compose restart`
2. Verify Neo4j tuning is active: `docker compose logs neo4j | grep heap`
3. Enable swap space (see #4 above)
4. Reduce other running containers

### Problem: Slow first request after 5min idle

**Expected behavior**: Model reloads after 5min idle (intentional).

**Options**:
1. Accept 2-3s delay on first request
2. Increase keep-alive: `OLLAMA_KEEP_ALIVE=15m` in docker-compose.yml
3. Keep a request every 4 minutes to prevent unload (not recommended)

---

## Recommended Development Workflow

### For Iterative Testing (Multiple Q&A Requests)
```bash
# Start services
docker compose up -d

# Make requests within 5min of each other
# Model stays loaded, fast responses

# After >5min idle, first request will reload model (2-3s delay)
```

### For Code Changes (Hot Reload)
```bash
# Backend code changes auto-reload (no restart needed)
# Frontend code changes auto-reload (Next.js fast refresh)

# Only restart if changing:
# - docker-compose.yml
# - Dockerfile
# - Environment variables
```

### For Resource-Intensive Work
```bash
# Temporarily stop services you're not using
docker compose stop frontend  # If only testing backend
docker compose stop ollama     # If not testing AI features
docker compose stop neo4j      # If only testing articles (not notes)
```

---

## Comparison: Dev vs Production

| Setting | Local Dev | Production |
|---------|-----------|------------|
| Neo4j Heap Max | 512m | 512m |
| Ollama Keep Alive | 5m | 0 (immediate) |
| Model Reload Frequency | Every 5min idle | Every request |
| First Request Time | 2-3s (if model unloaded) | 2-3s |
| Subsequent Requests | <1s (model cached) | 2-3s (model reloads) |
| Memory Usage | ~2-3GB total | ~2-3GB total |

**Why Different?**
- **Dev**: Optimize for iteration speed (keep model loaded)
- **Prod**: Optimize for memory (unload immediately to serve other requests)

---

## Apply Changes

After modifying docker-compose.yml:

```bash
# Restart services to apply new configs
docker compose down
docker compose up -d

# Verify configs applied
docker compose logs neo4j | grep heap
docker compose logs ollama | grep OLLAMA
```

---

## Next Steps

If performance is still an issue after these optimizations:

1. **Profile the slow requests** - See which step takes longest
2. **Consider smaller models** - Could use even smaller models for dev
3. **Hardware upgrade** - More RAM helps (16GB+ recommended)
4. **Selective feature testing** - Disable AI features when not needed

For production-level optimizations, see issue #59, #60, #61 on GitHub.
