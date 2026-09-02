## Overview

Bridges a fully static, publicly hosted Three.js app to a local Python script in real time, using the Chrome DevTools Protocol (CDP). The hosting stays 100% static — the bridge only talks to the already-running tab, it never changes how the page is deployed.

## What it does

- **Reads live state** — the robot's `x`, `z`, and `rotationY` — streamed continuously from the browser to Python as they change, not by polling or screenshotting.
- **Writes into the page** — Python drives the robot by dispatching real `keyDown`/`keyUp` events (`ArrowUp`, `ArrowLeft`, `ArrowRight`), so the app reacts exactly as if a person were holding the arrow keys.

## Files

- `index.html` - Static Three.js robot webpage.
- `bridge_script.py` - Python script (bridge) that connects to Chrome, sends commands, and reads robot state.

## Requirements

- **Python 3** - Required to run the bridge script
- **Google Chrome** - with remote debugging enabled on port 9222
- **websocket-client Python package** - to create the WebSocket connection to Chrome's DevTools Protocol.

## How to Run

### 1. Install Python

After installation, open Command Prompt and check:

```bash
python --version
```

You should see the installed Python version.

### 2. Install the required Python package

Open Command Prompt in the project folder and run:

```bash
pip install websocket-client
```

Verify the package is installed:

```bash
pip show websocket-client
```

### 3. Host the static webpage

- Create a new GitHub repository for the project
- Add your project files: `index.html`
- Open your GitHub repository
- Go to: **Settings → Pages**
- Under **Build and deployment**:
  - Source: `Deploy from a branch`
  - Branch: `main`
  - Folder: `/root`
- Then click **Save**.

GitHub Pages will generate a URL similar to:

```
https://<your-username>.github.io/<repo_name>/
```

Open that URL and confirm that the robot webpage loads correctly.

### 4. Start Chrome with remote debugging

Close all Chrome windows and start Chrome with remote debugging enabled on port 9222:

```powershell
& "<PATH_TO_CHROME.EXE>" `
  --remote-debugging-port=9222 `
  --user-data-dir="<USER_DATA_DIRECTORY>" `
  "<WEBPAGE_URL>"
```

Where:
- `<PATH_TO_CHROME.EXE>` = path to your Chrome executable
- `9222` = remote debugging port used by the Python script
- `<USER_DATA_DIRECTORY>` = separate Chrome profile directory for CDP
- `<ROBOT_WEBPAGE_URL>` = URL of the robot webpage

### 5. Open the hosted webpage

In that new Chrome window, open your GitHub Pages URL and keep that tab open.

### 6. Run the Python bridge from VS Code

Open VS Code: **Terminal → New Terminal**

Make sure the terminal is in the project folder, then run:

```bash
python bridge_script.py
```

## Why I chose Chrome DevTools Protocol (CDP)

I chose CDP because it provides a direct, low-latency interface between local Python and a running Chrome tab, without requiring a backend server or browser extension.

Using CDP, I implemented a two-way real-time bridge:

- **Python → Robot**: `Input.dispatchKeyEvent` sends keyboard commands.
- **Robot → Python**: An injected JavaScript listener captures `window.postMessage()` state updates and forwards them through `Runtime.addBinding`.

This keeps the robot application static and publicly hosted while Python handles browser control and state monitoring locally. The main trade-off is that Chrome must run with remote debugging enabled, so the CDP endpoint should only be used in a controlled environment.
