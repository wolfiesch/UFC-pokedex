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

| File | PR | Lines | Status | Description | Best For |
|------|-----|-------|--------|-------------|----------|
| **🎯 fight-graph-3d-combined.html** | - | ~850 | ✅ **Recommended** | Best of all: 2D/3D toggle + refined rendering + keyboard shortcuts | **Production ready - use this!** |
| **pr90-custom-force-2d3d.html** | 90 | 1,119 | ✅ **Working** | Custom physics with 2D⟷3D interpolation | Maximum control, unique features |
| **pr91-d3-force-scripts.html** | 91 | 872 | ❌ Broken | D3-Force-3D (legacy script tags) | Legacy browser support |
| **pr92-d3-force-clean.html** | 92 | 627 | ✅ **Working** | D3-Force-3D (ES modules) - Cleanest | Production use, maintainability |
| **pr93-force-graph-lib.html** | 93 | 757 | ❌ Broken | High-level force-graph libraries | Rapid prototyping, 2D+3D views |
| **pr94-d3-force-refined.html** | 94 | 804 | ✅ **Working** | D3-Force-3D (refined controls) | Polished experience |

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

## 🎯 Combined "Frankenstein" Prototype

**File:** `fight-graph-3d-combined.html` (~850 lines)

This is the **recommended production-ready version** that combines the best aspects of all working prototypes:

### What's Included:
✅ **From PR 94:** Battle-tested d3-force-3d physics, refined scene (lighting, fog), form-based controls
✅ **From PR 90:** 2D ⟷ 3D toggle with smooth z-coordinate interpolation, keyboard shortcuts (Spacebar, R, H), auto-orbit animation
✅ **From PR 92:** Clean sidebar design with interaction tips, simplified messaging

### Key Features:
- **2D/3D Toggle Button** - Smooth animated transition between flat 2D and full 3D layouts
- **Keyboard Shortcuts:**
  - `Spacebar`: Toggle auto-orbit animation
  - `R`: Reset camera to default position
  - `H`: Toggle hover tooltips on/off
- **Production-Ready Physics** - Uses d3-force-3d (not custom physics)
- **Refined Visuals** - Professional lighting, fog, and OrbitControls from PR 94
- **Clean Interface** - Form-based controls with clear tips sidebar
- **Degree Centrality Node Sizing** - Larger nodes = more connections
- **Hover Tooltips** - Fighter details on hover with toggle option

### Why This Version?
- ✅ Maintains PR 94's refinement (lighting, fog, controls)
- ✅ Adds PR 90's unique 2D/3D toggle feature
- ✅ Includes power-user keyboard shortcuts
- ✅ Uses battle-tested d3-force-3d library
- ✅ More maintainable than PR 90's custom physics (~850 lines vs 1,119)
- ✅ Production-ready with clean code structure

**Use this version for production deployment!**

## Test Results (as of 12/11/2025)

### ✅ Working Prototypes (4 of 6)
- **🎯 Combined Frankenstein:** Loads 200 fighters, 623 bouts. Perfect blend of all best features with 2D/3D toggle, keyboard shortcuts, and refined rendering. **RECOMMENDED FOR PRODUCTION.**
- **PR 90 (Custom Force):** Loads 200 fighters, 623 bouts with colored spheres. Custom physics and 2D/3D toggle work perfectly. Import map added for Three.js modules.
- **PR 92 (D3-Force Clean):** Loads 200 fighters, 623 bouts. Cleanest codebase, uses Skypack CDN for d3-force-3d. Import map + Skypack fix applied.
- **PR 94 (D3-Force Refined):** Loads 200 fighters, 623 bouts with labels and refined controls. Fixed node ID mapping (fighter_id → id) for d3-force compatibility.

### ❌ Unfixable Issues (2 of 5)
- **PR 91:** Missing d3-timer + d3-dispatch dependencies. The legacy script tag approach requires multiple d3 dependencies that aren't properly bundled for browser use via CDN.
- **PR 93:** High-level force-graph/3d-force-graph libraries not available as ES modules. Tried jsdelivr, unpkg, skypack - none provide working ES module exports for these libraries.

## Troubleshooting

### "Failed to fetch" Error
- **Cause:** CORS issue - backend not allowing requests from prototype server
- **Fix:** Add `http://localhost:8877` to backend CORS allowed origins (already done in `backend/main.py`)

### Module Import Errors
- **Cause:** Browser doesn't support import maps or CDN is unreachable
- **Fix:** Check internet connection, use working prototypes (PR 90, PR 92)

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
