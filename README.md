# PocketSmart AI

A complete Flask + SQLite + Google Gemini budget-planning website inspired by the supplied PocketSmart screenshots/video.

## What is included

- Responsive PocketSmart landing page
- Blue/navy visual system matching the reference
- Home Interior Budget Planner
- Party Budget Planner
- Jewellery Budget Planner
- AI recommendations through Google's `google-genai` SDK
- Local fallback recommendations if no API key is configured
- Sign up / login / logout
- SQLite storage for accounts and generated plans
- Dashboard showing saved plans
- No frontend API key exposure
- Health endpoint at `/api/health`
- Model fallback logic to reduce 404 errors when a model is unavailable
- Clean 404 page
- No external database required

## Requirements

- Windows 10/11
- Python 3.14
- Internet connection for Gemini calls
- A Gemini API key from Google AI Studio

Google's current Gemini Python documentation lists Python 3.9+ for the `google-genai` SDK, so Python 3.14 is within the documented range.

## Windows PowerShell: exact commands

Open VS Code, open this project folder, then open **Terminal > New Terminal** and run:

```powershell
py -3.14 --version
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python app.py
```

Paste your real Gemini API key into:

```text
GEMINI_API_KEY=YOUR_REAL_KEY
```

Save the file, then run:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## If PowerShell blocks activation

Run this once in the same terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Windows CMD alternative

```bat
py -3.14 --version
py -3.14 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
python app.py
```

## Get the Gemini key

Use Google AI Studio to create/copy a Gemini API key. Keep the key in `.env`; never paste it into `static/js/app.js`.

The app uses:

```python
from google import genai
client = genai.Client(api_key=api_key)
```

and calls Gemini from the Flask server.

## If you get a 404 from Gemini

The app already tries:

1. `GEMINI_MODEL` from `.env` (default `gemini-3.8-flash`)
2. `gemini-3-flash-preview`
3. `gemini-2.5-flash`

A model 404 automatically moves to the next candidate.

If the API key itself is invalid, the app does not hide that problem from you in debug mode. Check the key in `.env` and make sure there are no extra quotes or spaces.

## If you get "Internal Server Error"

First run:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000/api/health
```

You should see JSON. If `gemini_configured` is false, your `.env` key is not being read.

For a local Gemini diagnostic, temporarily set:

```text
DEBUG_GEMINI=1
```

in `.env`, restart the server, and submit a planner request. The returned fallback response will contain the Gemini error detail.

Set it back to `0` afterward.

## Important

Do not commit `.env` to GitHub. `.gitignore` already excludes it.

## Main routes

- `/` Home
- `/login` Login
- `/signup` Create account
- `/dashboard` Saved plans
- `/planner/home` Home Interior planner
- `/planner/party` Party planner
- `/planner/jewelry` Jewellery planner
- `/api/recommend` AI recommendation endpoint
- `/api/health` Server health check

## Stop the server

Press:

```text
CTRL + C
```

in the terminal.
