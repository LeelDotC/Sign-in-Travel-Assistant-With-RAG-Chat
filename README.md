# BL Travel Companion

BL Travel Companion is a Streamlit travel assistant for Bảo Lộc, Vietnam. The current app displays its destination, reports whether the required settings are present, and provides setup guidance when settings are missing. It opens without credentials. Live authentication, chat, and model connections are not implemented yet.

- Student name: [Enter student name]
- Student ID: [Enter student ID]
- Class: [Enter class]

## Local setup on Windows

From the project folder in PowerShell, create and activate the virtual environment with Python 3.15.2. Adjust the executable path if Python is installed elsewhere.

```powershell
& 'C:\Users\letan\AppData\Local\Python\pythoncore-3.15-64\python.exe' -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

To launch without activating the environment, run the following command.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Configuration

The app can run without a `.env` file. To supply settings, copy the example from the project folder if you do not already have a `.env` file.

```powershell
Copy-Item .env.example .env
```

Fill in the settings in `.env` and restart the app.

| Setting | Intended purpose |
| --- | --- |
| `FIREBASE_PROJECT_ID` | Identifies the Firebase project for future authentication. |
| `FIREBASE_API_KEY` | Supplies the API key for future Firebase Authentication requests. |
| `OLLAMA_BASE_URL` | Identifies the Ollama server endpoint for future model requests. |

Existing environment variables take precedence over `.env`. Blank values count as missing. The app checks whether settings are present locally and never displays their values.

## AI assistance

OpenAI Codex assisted with planning, implementation, and local verification.
