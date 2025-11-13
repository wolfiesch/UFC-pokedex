# UFC Fight Graph 3D Prototypes

This directory contains 5 different 3D fight graph visualization prototypes for side-by-side comparison.

## Quick Start

1. **Start the backend API:**
   ```bash
   # From project root
   make ensure-docker  # or your preferred method to start the backend
   ```

2. **Serve the prototypes:**
   ```bash
   cd docs/prototypes
   python3 -m http.server 8877
   ```

3. **Open in browser:**
   - Index page with comparison: http://localhost:8877/index.html
   - Individual prototypes: http://localhost:8877/pr90-custom-force-2d3d.html (etc.)

## CORS Configuration

**Important:** The backend needs to allow CORS requests from `localhost:8877` (or your chosen port).

### Quick Fix (Development Only)

Add to your backend CORS configuration:

```python
# backend/app/main.py or similar
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8877",  # Add this for prototypes
        # ... other origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Alternative: Use API Query Parameter

Some prototypes support specifying a custom API URL:
```
http://localhost:8877/pr90-custom-force-2d3d.html?apiBase=http://localhost:8000
```

## Prototypes Overview

| File | PR | Lines | Description | Best For |
|------|-----|-------|-------------|----------|
| **pr90-custom-force-2d3d.html** | 90 | 1,119 | Custom physics with 2D⟷3D interpolation | Maximum control, unique features |
| **pr91-d3-force-scripts.html** | 91 | 872 | D3-Force-3D (legacy script tags) | Legacy browser support |
| **pr92-d3-force-clean.html** | 92 | 627 | D3-Force-3D (ES modules) - Cleanest | Production use, maintainability |
| **pr93-force-graph-lib.html** | 93 | 757 | High-level force-graph libraries | Rapid prototyping, 2D+3D views |
| **pr94-d3-force-refined.html** | 94 | 804 | D3-Force-3D (refined controls) | Polished experience |

## Feature Comparison

### PR 90: Custom Force + 2D⟷3D Toggle ⭐
- ✅ Smooth interpolation between 2D and 3D layouts
- ✅ 4 physics control sliders (link distance, repulsion, depth, iterations)
- ✅ Custom force-directed layout algorithms
- ✅ Real-time parameter adjustment
- **Best for:** Understanding physics, fine-grained control

### PR 91: D3-Force-3D (Script Tags)
- ✅ Proven d3-force-3d physics
- ✅ Legacy script tag approach (non-ES modules)
- ✅ Good documentation and interaction cheatsheet
- **Best for:** Older browser compatibility

### PR 92: D3-Force-3D (Clean) 🎯
- ✅ Most concise (627 lines)
- ✅ Modern ES module approach
- ✅ Proven physics library
- ✅ Easy to understand and maintain
- **Best for:** Production deployment, clean codebase

### PR 93: Force-Graph Libraries 🚀
- ✅ Both 2D and 3D views with toggle
- ✅ Minimal custom code (high-level libraries)
- ✅ Import maps for dependency management
- ✅ Auto-rotating 3D view
- **Best for:** Quick experiments, rapid iteration

### PR 94: D3-Force-3D (Refined)
- ✅ Modern ES modules with refined settings
- ✅ Polished OrbitControls
- ✅ Production/local API support
- ✅ Beautiful lighting setup
- **Best for:** Polished user experience

## Technical Notes

### Module Loading
All prototypes use ES modules with either:
- **Import maps** (PR 90, 93) - Modern, declarative dependency management
- **Full CDN URLs** (PR 92, 94) - Direct imports from jsdelivr/unpkg
- **Script tags** (PR 91) - Legacy non-module approach

### Dependencies
- **Three.js** (0.160.0 - 0.162.0) - 3D rendering engine
- **d3-force-3d** (3.0.0+) - Physics simulation (PRs 91, 92, 94)
- **force-graph** / **3d-force-graph** (PR 93) - High-level graph libraries
- **OrbitControls** - Camera controls for all prototypes

### Browser Compatibility
- Modern browsers with ES module support (Chrome 61+, Firefox 60+, Safari 11+, Edge 16+)
- PR 91 supports older browsers via script tags

## "Frankenstein" Recommendation

For the ultimate version, combine:
1. **Base:** PR 92's clean ES module structure (627 lines)
2. **Add:** PR 90's 2D⟷3D interpolation and control sliders
3. **Add:** PR 93's import maps for cleaner dependency management
4. **Polish:** PR 94's refined OrbitControls settings and lighting

Estimated result: ~850-900 lines with all the best features.

## Troubleshooting

### "Failed to fetch" Error
- **Cause:** CORS issue - backend not allowing requests from prototype server
- **Fix:** Add `http://localhost:8877` to backend CORS allowed origins

### Module Import Errors
- **Cause:** Browser doesn't support import maps or CDN is unreachable
- **Fix:** Use PR 91 (script tags) or check internet connection

### Blank Canvas
- **Cause:** No API data loaded (CORS or backend not running)
- **Check:** Browser console for errors, verify backend is running at localhost:8000

### Performance Issues
- **Cause:** Too many nodes/edges in the graph
- **Fix:** Use `?limit=100` query parameter to reduce graph size

## Development

To modify a prototype:
1. Edit the HTML file directly
2. Refresh browser (no build step needed)
3. Check browser console for errors
4. Use browser DevTools to inspect Three.js scene

All prototypes are self-contained single-file HTML documents with inline CSS and JavaScript.

---

Generated as part of UFC Pokedex 3D graph exploration.
