# Profiling & Performance Guide

Performance profiling tools and commands for backend and frontend.

## Backend Profiling (Python)

### Tools

| Tool | Overhead | Use Case | Command |
|------|----------|----------|---------|
| **[py-spy](https://github.com/benfred/py-spy)** | Very Low | Production profiling, hot spots | `make profile` |
| **[VizTracer](https://viztracer.readthedocs.io/)** | High | Understanding code flow, timing | `make profile-viz` |
| **line_profiler** | Medium | Line-by-line timing | `kernprof -l -v` |
| **[memray](https://bloomberg.github.io/memray/)** | Medium | Memory profiling, leaks | `make memory` |
| **memory_profiler** | High | Memory usage per line | `python -m memory_profiler` |

### Quick Commands

```bash
cd backend

# CPU Profiling
make profile          # py-spy (recommended)
make profile-viz      # VizTracer with interactive viewer

# Memory Profiling
make memory           # memray

# Benchmarking
make benchmark        # API benchmarks
```

### Manual Usage

```bash
# py-spy: Low overhead, production-safe
py-spy top --pid $(pgrep -f "python main.py")
py-spy record -o profile.svg -- python main.py

# VizTracer: Detailed flow analysis
viztracer main.py
vizviewer profiling_result.json

# memray: Memory profiling
memray run main.py
memray flamegraph memray-*.bin
memray table memray-*.bin
```

## Frontend Profiling (Next.js/React)

### Tools

- **React DevTools Profiler**: Built-in React profiling, find slow renders
- **[Next.js Bundle Analyzer](https://www.npmjs.com/package/@next/bundle-analyzer)**: Analyze bundle size (`npm run build:analyze`)
- **Chrome DevTools Performance**: Full application profiling
- **Why Did You Render**: Catch unnecessary re-renders
- **[Lighthouse](https://developer.chrome.com/docs/lighthouse/)**: Overall performance audit

### Quick Commands

```bash
cd frontend

# Bundle analysis
npm run build:analyze

# Lighthouse audit
lighthouse http://localhost:3000 --view
```

## Performance Optimization Checklist

### Backend
- [ ] Profile hot paths with py-spy
- [ ] Add caching where appropriate
- [ ] Use async/await for I/O operations
- [ ] Batch database queries
- [ ] Use connection pooling
- [ ] Enable gzip compression
- [ ] Optimize database indexes

### Frontend
- [ ] Code splitting with dynamic imports
- [ ] Lazy load components
- [ ] Memoize expensive calculations with React.memo
- [ ] Optimize images (use Next.js Image)
- [ ] Minimize bundle size
- [ ] Virtual scrolling for long lists

## Profiling Workflow

1. **Identify**: Run benchmarks or Lighthouse
2. **Profile**: Use appropriate tool to find bottleneck
3. **Optimize**: Make targeted changes with tests
4. **Verify**: Profile again to confirm improvement

## Production Monitoring

Recommended tools (add to `requirements-prod.txt`):
- **[Sentry](https://docs.sentry.io/)**: Error tracking
- **DataDog/New Relic**: APM
- **[Prometheus](https://prometheus.io/)**: Metrics collection
- **[Grafana](https://grafana.com/)**: Metrics visualization

## Resources

- [py-spy documentation](https://github.com/benfred/py-spy)
- [VizTracer documentation](https://viztracer.readthedocs.io/)
- [memray documentation](https://bloomberg.github.io/memray/)
- [React DevTools Profiler](https://react.dev/reference/react/Profiler)
- [Next.js Performance](https://nextjs.org/docs/pages/building-your-application/optimizing)
- [Web.dev Performance](https://web.dev/performance/)
