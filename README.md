# AriaOSAgent

Welcome to AriaOSAgent! This project consists of a desktop application built with Tauri, a React+Vite frontend, and a Python backend.

## Requirements

- [Node.js](https://nodejs.org/) (v16+)
- [Rust](https://www.rust-lang.org/tools/install)
- [Python 3.10+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/makekush7-netizen/AriaOSAgent.git
cd AriaOSAgent
```

### 2. Python Backend Setup

Navigate to the backend directory, install requirements and run the backend server.

```bash
cd backend
pip install -r requirements.txt
python run.py # or python main.py
```

### 3. Frontend & Tauri Setup

Open a new terminal in the root directory. Navigate to the frontend directory to install dependencies.

```bash
cd frontend
npm install
```

To run the application in development mode (which starts the Vite dev server and the Tauri app):

```bash
npm run tauri dev
```
*(Make sure Tauri CLI is installed globally or use `npx tauri dev`)*

## Contributing

Feel free to open issues or submit pull requests.
