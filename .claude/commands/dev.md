---
name: dev
description: Launch the development environment in a new terminal window
---

Please run the development environment by opening a new terminal window and executing:

```bash
cd /Users/wolfgangschoenberger/Projects/UFC-pokedex && ./launch-dev.sh
```

Or, if you prefer to run it in a new terminal tab on macOS:

```bash
osascript -e 'tell application "Terminal" to do script "cd /Users/wolfgangschoenberger/Projects/UFC-pokedex && ./launch-dev.sh"'
```

The development environment will start in that terminal window, keeping it separate from my background shell. You can monitor its output and stop it with Ctrl+C when needed.
