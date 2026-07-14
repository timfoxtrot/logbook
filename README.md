# Logbook

web logbook for shift tracking.

## Getting Started

1.  **Clone the repo**:
    ```bash
    git clone [https://github.com/YOUR_USERNAME/logbook.git](https://github.com/YOUR_USERNAME/logbook.git)
    cd logbook
    ```

2.  **Set up (Run once)**:
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    
    pip install flask
    ```

3.  **Run the app**:
    ```bash
    python app.py
    ```

4.  **Open in browser**:
    Navigate to `http://127.0.0.1:5000`

## Features
* **Drafts**: Save log entries during your shift.
* **Commit**: End your shift and save to the Master Log.
* **Admin Tools**: Manage team accounts and purge old logs.
* **Search**: Easily filter by keyword or date range.

## How to update your repo:
Whenever you make a change, just run these three commands to save your progress:

```bash
git add .
git commit -m "Update: [Brief description of what you changed]"
git push
