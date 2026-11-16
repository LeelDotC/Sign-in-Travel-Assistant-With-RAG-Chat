# BL Travel Companion

BL Travel Companion is a Streamlit travel assistant for Bảo Lộc, Vietnam. It uses Firebase Email/Password for registration and sign-in. Signed-in visitors see their email and a protected travel chat placeholder. Chat and model requests are outside the app's current scope.

- Student name: Le Tan Loc
- Student ID: 25127406
- Class: 25C09

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

Edit only the three keys below in the project-local `.env`. Preserve unrelated settings and keep `.env.example` empty.

| Setting | Intended purpose |
| --- | --- |
| `FIREBASE_PROJECT_ID` | Identifies the Firebase project for authentication. |
| `FIREBASE_API_KEY` | Supplies the Web API key for Firebase Authentication requests. |
| `OLLAMA_BASE_URL` | Identifies the Ollama endpoint used by the service and retrieval checkers. |

Existing environment variables take precedence over `.env`, including blank shell values. The checker reports a differing shell override by variable name. If it is unintended, remove the named override in PowerShell and run the check again. For example, `Remove-Item Env:OLLAMA_BASE_URL` clears the tunnel override in the current shell.

## Firebase Authentication setup

- Open the Firebase console with the Google account intended to own the project. Choose **Create a project** and enter **BL Travel Companion**. Review the proposed project ID and account before creating it. Stay on Spark and leave optional Analytics and hosting disabled. [Firebase web setup](https://firebase.google.com/docs/web/setup) · [Firebase pricing plans](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans)
- In **Project Overview**, use the **Web** icon or **Add app > Web**. Register the app as **BL Travel Companion**. Under **Project settings > General > Your apps**, find the registered web app and its SDK configuration. Copy `projectId` to `FIREBASE_PROJECT_ID` and `apiKey` to `FIREBASE_API_KEY` in `.env`.
- In the console sidebar, open **Security > Authentication**. Select **Get started** if needed. Open **Sign-in method > Email/Password**, enable Email/Password and save. Confirm the provider shows **Enabled** and the web app appears under **Your apps**. [Firebase password authentication](https://firebase.google.com/docs/auth/web/password-auth)

The service checker reports whether the two Firebase settings are present. Use the Streamlit forms to test account creation and sign-in. Firebase authentication uses these two settings independently of Ollama.

## Test authentication locally

Open the local Streamlit URL. Select **Create an account**, enter an email you control, and type the same separate app password into **Password** and **Re-enter password**. Select **Create account**. Expect **Account created. Please sign in** above the sign-in form and an empty password field.

Enter the same email and try a blank or incorrect password. Expect an error, the email you typed, and an empty password field. Registration errors also preserve the email and clear both password fields. Enter the correct credentials and confirm the page shows your email, **Sign out**, and **Travel chat is coming soon**. Open the same local URL in a private browser window and confirm it shows **Sign in** without the protected placeholder. Select **Sign out** in the original window and confirm it returns to **Sign in**.

To submit with the keyboard, Tab to the submit button and press Enter or Space. Pressing Enter inside an input no longer submits the form.

The app checks session expiry while the protected page is open and clears the session on expiry or sign-out. When either Firebase setting is missing, the app shows setup guidance. To check that locally without changing `.env`, run the app from a disposable PowerShell shell with a whitespace-only `FIREBASE_API_KEY` override, then close that shell after testing.

## Ollama and Pinggy

- In [Google Colab](https://colab.research.google.com/), choose **File > Upload notebook** and open `notebooks/ollama_pinggy_server.ipynb`. Under **Runtime > Change runtime type**, choose an available free GPU and connect. Run the cells in order. The notebook installs Ollama, starts or reuses its local server, pulls `embeddinggemma` and `qwen3:4b`, and checks both APIs on the runtime. Free GPUs are subject to availability and quota. If the free runtime is denied or interrupted, retry when available or agree on another runtime before moving the exercise. [Colab FAQ](https://research.google.com/colaboratory/faq.html)
- Once the local checks pass, run the Pinggy cell. It uses the lab's SSH forward and verifies the published Pinggy host fingerprint. Right-click the **Copy the private HTTPS tunnel address** link, select **Copy link address**, and paste it directly into `OLLAMA_BASE_URL` in `.env`. Keep the interactive Colab session connected during verification. The URL grants access to the forwarded Ollama API, so keep it private. [Pinggy HTTP tunnels](https://pinggy.io/docs/http_tunnels/) · [Pinggy SSH host key and free tunnel limits](https://pinggy.io/help/)

Run the checker from the project folder in PowerShell.

```powershell
.\.venv\Scripts\python.exe check_services.py
```

The checker lists the required models, requests one embedding, and verifies that generation returns final text. A failed required check returns a nonzero exit code.

- **Missing configuration**. Confirm the three keys in the project-local `.env` and check any shell overrides reported by name.
- **Missing models**. Rerun the pull cell and confirm both local checks complete on the current runtime.
- **Expired tunnel or unexpected HTTP/JSON response**. Confirm Colab is still connected, then run the tunnel cell again if the tunnel has stopped. Use the new HTTPS tunnel link in `OLLAMA_BASE_URL`, clear any stale shell override, restart local processes such as Streamlit, and rerun the checker.
- **Timeout**. Confirm Colab is still connected and both local requests work. Retry with the warm models and an active tunnel.

After use, run the notebook's shutdown cell to stop Pinggy, clear notebook outputs before saving or sharing copies, and select **Runtime > Disconnect and delete runtime** to stop Ollama and release the GPU. Press **Ctrl+C** in PowerShell to stop Streamlit.

## Check guide retrieval

`knowledge_base.json` contains 15 Bảo Lộc entries checked against their sources on November 16, 2026. Each entry has a stable ID, source link, category, and tags. Student review remains pending. The flowering and rainfall entries describe observations and historical averages.

With Ollama and Pinggy running and `OLLAMA_BASE_URL` set in the project `.env`, run this command from the project folder in PowerShell.

```powershell
.\.venv\Scripts\python.exe check_retrieval.py
```

The checker asks about Dambri Waterfall, Hồ Đồng Nai, and silkworm farming, then repeats the waterfall question in different words. It prints each expected ID and the three actual IDs with descending cosine scores. A missing expected entry produces a nonzero exit code. In the November 16, 2026 live check, all four expected entries ranked first. See `ROADMAP.md` for the scores.

Retrieval uses `embeddinggemma` for the guide and the questions. Within one process, the index is reused until the guide titles or text, Ollama origin, or model changes. Metadata-only edits appear in results without rebuilding the index. Scores measure similarity. Whether an entry supports an answer requires a separate check. If the tunnel has expired, follow the restart steps above.

## AI assistance

OpenAI Codex assisted with planning, implementation, and local verification.
