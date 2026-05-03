# 📋 L&D Certificate Sync — Setup Guide

> **Who is this guide for?**
> This is a step-by-step guide written for non-technical users. You do **not** need to understand programming to follow it. Just follow each step exactly as written and you will have the application running on your computer.

---

## 📦 What This Application Does

This tool allows the L&D (Learning & Development) admin team to:
- Connect to a **Google Sheet** containing employee certificate details
- Automatically read and extract data from certificates stored in **Google Drive**
- View all certificates in a clean dashboard — showing who has valid, expiring, or expired certificates
- Export the data to **Excel (.xlsx)** with one click

The app has two parts that need to run simultaneously:
- **Backend** (the "engine" — handles data processing)
- **Frontend** (the "screen" — the website you see in your browser)

---

## ✅ Prerequisites — What You Need Installed First

Before starting, you need to install the following software. Click each link and follow the installer instructions for your operating system (Windows/Mac/Linux).

### 1. Python (version 3.10 or higher)
- Download from: https://www.python.org/downloads/
- ⚠️ **Windows users:** During installation, check the box that says **"Add Python to PATH"**
- To verify it's installed, open a terminal/command prompt and type:
  ```
  python --version
  ```
  You should see something like `Python 3.11.x`

### 2. Node.js (version 18 or higher)
- Download from: https://nodejs.org/en/download (choose the **LTS** version)
- To verify it's installed, open a terminal and type:
  ```
  node --version
  ```
  You should see something like `v20.x.x`

### 3. Git
- Download from: https://git-scm.com/downloads
- This is needed to download the project code

---

## 📥 Step 1 — Download the Project

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) and run:

```bash
git clone <your-github-repo-url-here>
```

Then navigate into the project folder:
```bash
cd L&D_cert_v2
```

You will see two folders inside: **`backend`** and **`frontend`**.

---

## ⚙️ Step 2 — Configure the Backend (Settings File)

The backend needs a configuration file called **`.env`** to connect to your Google and Azure accounts.

> **Note:** This file contains sensitive keys and passwords. **Never share it publicly or upload it to GitHub.**

1. Navigate into the **`backend`** folder
2. Look for the file named **`.env`** (it may be hidden — enable "show hidden files" in your file explorer)
3. Open it with any text editor (Notepad, TextEdit, VS Code)
4. Fill in the values as described below:

```
# ── Azure Storage (Blob) ──────────────────────────────────────────
# Used to temporarily store certificate files for viewing
AZURE_STORAGE_CONNECTION_STRING=<paste your Azure Storage connection string here>
AZURE_STORAGE_CONTAINER=<your container name, e.g. certblobstorage>

# ── Azure Document Intelligence ────────────────────────────────────
# Used to read/extract text from PDF certificate files
AZURE_FORM_RECOGNIZER_ENDPOINT=https://<your-resource-name>.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=<your Document Intelligence key>

# ── Azure OpenAI ──────────────────────────────────────────────────
# Used to understand and parse the certificate text using AI
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com/
AZURE_OPENAI_KEY=<your Azure OpenAI key>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# ── Google OAuth (Login) ──────────────────────────────────────────
# Used so employees can log in securely with their company Google account
GOOGLE_CLIENT_ID=<your Google OAuth Client ID>
GOOGLE_CLIENT_SECRET=<your Google OAuth Client Secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# ── Access Control ────────────────────────────────────────────────
# Only emails from this domain are allowed to log in
ALLOWED_DOMAIN=sigmoidanalytics.com

# ── App Security ──────────────────────────────────────────────────
# A random secret phrase used to secure login sessions (you can change this to anything)
JWT_SECRET=supersecret
APP_ENV=dev
LOG_LEVEL=INFO
```

> 💡 **Where do I get these values?**
> - **Azure keys**: Go to [portal.azure.com](https://portal.azure.com), open the respective service, and find the "Keys and Endpoints" section
> - **Google OAuth credentials**: Go to [console.cloud.google.com](https://console.cloud.google.com), open your project → APIs & Services → Credentials

---

## ⚙️ Step 3 — Configure the Frontend (Settings File)

1. Navigate into the **`frontend`** folder
2. Create a new file called **`.env`** (exactly that name, with the dot)
3. Add the following single line:

```
VITE_API_URL=http://localhost:8000
```

> This tells the dashboard where to find the backend. Leave it exactly as shown when running locally.

---

## 🐍 Step 4 — Set Up the Backend

Open a **new terminal window**, navigate to the `backend` folder, and run these commands one by one:

**On Mac/Linux:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**On Windows:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> What this does:
> - Creates an isolated Python environment (so it doesn't interfere with other software)
> - Installs all the required Python packages

You should see output like `Successfully installed fastapi uvicorn openai ...`

---

## 🚀 Step 5 — Start the Backend

In the **same terminal** (with the venv activated), run:

```bash
uvicorn main:app --reload
```

✅ You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

> **Keep this terminal window open.** The backend must stay running while you use the app.

---

## 🌐 Step 6 — Set Up and Start the Frontend

Open a **second, separate terminal window**, navigate to the `frontend` folder, and run:

```bash
cd frontend
npm install
npm run dev
```

> `npm install` downloads all website dependencies (only needed the first time).

✅ You should see:
```
  VITE ready in 400ms

  ➜  Local:   http://localhost:5173/
```

> **Keep this terminal window open too.**

---

## 🖥️ Step 7 — Open the Application

Open your web browser (Chrome recommended) and go to:

```
http://localhost:5173
```

You will see the login screen. Click **"Sign in with Google"** and log in with your company email (`@sigmoidanalytics.com`).

> ⚠️ Only email addresses from the allowed domain can log in. Contact the administrator if you get an "Unauthorized domain" error.

---

## 🔄 How to Use the Dashboard

Once logged in, you'll see the **L&D Admin Dashboard**.

### Running a Sync
1. Paste the **Google Sheet URL** — this is the spreadsheet containing employee names, emails, and links to their certificates
2. Paste the **Google Drive Folder URL** — the folder where certificate files are stored
3. Click **"🔄 Run AI Sync"**
4. A progress bar will appear showing `1/5`, `2/5`, etc. as each new certificate is processed
5. Already-processed certificates are loaded instantly from the sheet

### Reading the Table
| Status | Meaning |
|---|---|
| ✅ Valid | Certificate is valid and not expiring soon |
| ⚠️ Expiring | Certificate expires within the next 30 days |
| ❌ Expired | Certificate has already expired |
| ➖ No Expiry | Certificate has no expiration date (e.g. Udemy completions) |

### Filtering
Use the filter buttons above the table to show only certificates of a specific status.

### Downloading to Excel
Click **"📥 Download EXCEL (.xlsx)"** to download the full data as an Excel file.

---

## 🛑 How to Stop the Application

To stop the application, go to each terminal window and press:
```
Ctrl + C
```

---

## 🔁 How to Restart After Closing

Every time you want to use the application again, you need to:

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate      # Mac/Linux
# OR: venv\Scripts\activate   # Windows
uvicorn main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open `http://localhost:5173` in your browser.

> ⚠️ Since the app uses **tab-scoped login sessions**, you will need to log in again each time you open a new browser tab. This is a security feature to protect access.

---

## ❓ Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| `python: command not found` | Python not installed or not in PATH | Re-install Python and check "Add to PATH" |
| `npm: command not found` | Node.js not installed | Install Node.js from nodejs.org |
| `Application startup complete` not shown | Missing or incorrect `.env` file | Double-check Step 2 |
| "Unauthorized domain" on login | Email not from allowed domain | Contact your administrator |
| Progress bar stuck | Network issue or Azure key expired | Check Azure portal for key validity |
| Page shows "Sync Failed" | Google Sheet URL is wrong or not shared | Ensure the sheet is shared with your Google account |
| Blank page or white screen | Frontend not started | Make sure `npm run dev` is running |

---

## 📁 Project Structure (For Reference)

```
L&D_cert_v2/
├── backend/
│   ├── .env                  ← Your secret configuration (never share this)
│   ├── main.py               ← Backend entry point
│   ├── requirements.txt      ← Python dependencies
│   ├── routers/
│   │   ├── auth.py           ← Google login handling
│   │   └── sync.py           ← Certificate sync logic
│   └── utils/
│       ├── extractor.py      ← Azure AI extraction
│       ├── google_sdk.py     ← Google Sheets & Drive integration
│       └── security.py       ← Login session security
└── frontend/
    ├── .env                  ← Frontend configuration
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.jsx ← Main dashboard screen
    │   │   └── Login.jsx     ← Login screen
    │   └── services/
    │       ├── api.js        ← API communication
    │       └── auth.js       ← Login/logout logic
    └── package.json          ← Frontend dependencies list
```

---

## 📞 Support

If you encounter any issues not covered above, please reach out to the development team with:
1. A screenshot of the error
2. Which step you were on
3. What operating system you are using (Windows/Mac/Linux)
