# Profiling & Performance Guide

## Backend Profiling (Python)

### Available Tools

#### 1. py-spy (Recommended for Production-like Profiling)
**Low overhead, can attach to running processes**

```bash
# Profile a running server
make profile

# Or manually:
py-spy top --pid $(pgrep -f "python main.py")

# Record and generate flame graph
py-spy record -o profile.svg -- python main.py

# Profile specific endpoint
py-spy record -o profile.svg --duration 30 -- python main.py
```

**When to use**: Always-on profiling, production debugging, finding hot spots

#### 2. VizTracer (Interactive Profiling)
**Visual timeline, great for understanding flow**

```bash
make profile-viz

# Then view in browser
vizviewer profiling_result.json
```

**When to use**: Understanding code flow, finding synchronization issues, detailed timing

#### 3. line_profiler (Line-by-line Profiling)
**See which lines are slow**

```python
# Add @profile decorator to functions you want to profile
@profile
def slow_function():
    # code here
```

```bash
kernprof -l -v main.py
```

**When to use**: Optimizing specific functions, finding bottlenecks in algorithms

#### 4. memray (Memory Profiling)
**Find memory leaks and allocations**

```bash
make memory

# Generate flame graph
memray flamegraph memray-*.bin

# Generate table
memray table memray-*.bin
```

**When to use**: Memory leaks, high memory usage, allocation hot spots

#### 5. memory_profiler (Line-by-line Memory)
**Memory usage per line**

```python
from memory_profiler import profile

@profile
def memory_heavy_function():
    # code here
```

```bash
python -m memory_profiler main.py
```

**When to use**: Finding which lines allocate memory

### Benchmarking

```bash
# Run API benchmarks
make benchmark

# With pytest-benchmark
pytest tests/ --benchmark-only
```

### Quick Reference

| Tool | Overhead | Use Case | Command |
|------|----------|----------|---------|
| py-spy | Very Low | Production profiling | `make profile` |
| VizTracer | High | Understanding flow | `make profile-viz` |
| line_profiler | Medium | Line-by-line timing | `kernprof -l -v` |
| memray | Medium | Memory profiling | `make memory` |
| benchmark | N/A | Performance testing | `make benchmark` |

## Frontend Profiling (Next.js/React)

### Available Tools

#### 1. React DevTools Profiler
**Built-in React profiling**

1. Install React DevTools browser extension
2. Open DevTools → Profiler tab
3. Click record, interact with app, stop recording
4. Analyze component render times

**When to use**: Finding slow renders, unnecessary re-renders

#### 2. Next.js Bundle Analyzer
**Analyze bundle size**

```bash
npm run build:analyze
```

Opens interactive treemap showing bundle composition.

**When to use**: Reducing bundle size, finding large dependencies

#### 3. Chrome DevTools Performance
**Full application profiling**

1. Open DevTools → Performance tab
2. Click record
3. Interact with app
4. Stop recording and analyze

**When to use**: Finding JavaScript bottlenecks, layout thrashing, long tasks

#### 4. Why Did You Render (WDYR)
**Catch unnecessary re-renders**

```typescript
// Add to _app.tsx in development
if (process.env.NODE_ENV === 'development') {
  const whyDidYouRender = require('why-did-you-render');
  whyDidYouRender(React, {
    trackAllPureComponents: true,
  });
}
```

**When to use**: Optimizing React performance, finding render causes

#### 5. Lighthouse
**Overall performance audit**

```bash
# Built into Chrome DevTools
# Or run from CLI
npm install -g lighthouse
lighthouse http://localhost:3000 --view
```

**When to use**: Production performance audit, accessibility, SEO

### Performance Optimization Checklist

#### Backend
- [ ] Profile hot paths with py-spy
- [ ] Add caching where appropriate
- [ ] Use async/await for I/O operations
- [ ] Batch database queries
- [ ] Use connection pooling
- [ ] Enable gzip compression
- [ ] Optimize database indexes

#### Frontend
- [ ] Code splitting with dynamic imports
- [ ] Lazy load components
- [ ] Memoize expensive calculations
- [ ] Use React.memo for pure components
- [ ] Optimize images (use Next.js Image)
- [ ] Minimize bundle size
- [ ] Use CDN for static assets
- [ ] Implement virtual scrolling for long lists

## Profiling Workflow

### 1. Identify the Problem
```bash
# Backend: Run benchmarks
make benchmark

# Frontend: Run Lighthouse
lighthouse http://localhost:3000
```

### 2. Profile to Find Bottleneck
```bash
# Backend: Profile with py-spy
make profile

# Frontend: Use React DevTools Profiler
```

### 3. Optimize
- Make targeted changes
- Add tests for critical paths
- Profile again to verify improvement

### 4. Verify
```bash
# Backend: Re-run benchmarks
make benchmark

# Frontend: Compare Lighthouse scores
```

## Production Monitoring

### Recommended Tools

1. **Sentry**: Error tracking
2. **DataDog/New Relic**: APM
3. **Prometheus**: Metrics collection
4. **Grafana**: Metrics visualization

### Adding to Production

Uncomment in `requirements-prod.txt`:
```python
sentry-sdk[fastapi]==2.21.0
prometheus-fastapi-instrumentator==7.0.0
```

## Performance Tips

### Backend
1. **Use FastAPI's dependency injection for caching**
2. **Profile in production mode** (dev mode has overhead)
3. **Use uvloop** (enabled in production Dockerfile)
4. **Enable HTTP/2** for better performance
5. **Use Pydantic v2** (already using) for fast validation

### Frontend
1. **Use Next.js Image component** for automatic optimization
2. **Implement ISR** (Incremental Static Regeneration) for semi-static pages
3. **Use SWR/React Query** for data fetching with caching
4. **Minimize client-side JavaScript**
5. **Use font-display: swap** for custom fonts

## Debugging Performance Issues

### Backend is Slow

```bash
# 1. Profile the application
make profile

# 2. Check for:
# - Synchronous I/O operations
# - N+1 queries
# - Missing database indexes
# - Large memory allocations

# 3. Memory issues?
make memory
```

### Frontend is Slow

```bash
# 1. Analyze bundle
npm run build:analyze

# 2. Check for:
# - Large dependencies
# - Unnecessary re-renders
# - Missing code splitting
# - Unoptimized images

# 3. Profile in React DevTools
```

## Resources

- [py-spy documentation](https://github.com/benfred/py-spy)
- [VizTracer documentation](https://viztracer.readthedocs.io/)
- [memray documentation](https://bloomberg.github.io/memray/)
- [React DevTools Profiler](https://react.dev/reference/react/Profiler)
- [Next.js Performance](https://nextjs.org/docs/pages/building-your-application/optimizing)
- [Web.dev Performance](https://web.dev/performance/)
