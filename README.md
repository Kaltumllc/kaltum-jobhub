# Kaltum — AI Job Search & Resume Builder

## Project Structure
```
kaltum/
├── frontend/
│   └── index.html        ← The entire web app (one file)
└── backend/
    ├── main.py           ← FastAPI backend (job search + AI)
    └── requirements.txt  ← Python dependencies
```

---

## 🚀 Deploy in 15 Minutes

### Step 1 — Push to GitHub
1. Go to https://github.com/new and create a repo called `kaltum`
2. Upload ALL files from this folder to the repo

### Step 2 — Deploy Frontend on Vercel (FREE)
1. Go to https://vercel.com and sign in with GitHub
2. Click **"Add New Project"**
3. Select your `kaltum` repo
4. Set **Root Directory** to `frontend`
5. Click **Deploy**
6. ✅ Your app is live at `kaltum.vercel.app`

Want a custom domain like `kaltum.app`?
- Buy domain at Namecheap/GoDaddy
- In Vercel → Settings → Domains → Add your domain

### Step 3 — Deploy Backend on Render (FREE)
1. Go to https://render.com and sign in with GitHub
2. Click **"New Web Service"**
3. Select your `kaltum` repo
4. Configure:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variable:
   - Key: `ANTHROPIC_API_KEY`
   - Value: your Anthropic API key (get at https://console.anthropic.com)
6. Click **Deploy**
7. ✅ Your API is live at `https://kaltum-api.onrender.com`

### Step 4 — Connect Frontend to Backend (Optional)
The frontend calls Claude AI directly by default.
If you want to route through your backend instead, update the fetch URLs in index.html:
```
https://api.anthropic.com/v1/messages
→ https://kaltum-api.onrender.com/ai/cover-letter
```

---

## 🔑 API Keys Needed
| Key | Where to get | Cost |
|-----|-------------|------|
| Anthropic API | https://console.anthropic.com | ~$5/mo |
| RemoteOK Jobs | No key needed | Free |

---

## Features
- 🔍 Real job search (RemoteOK API)
- 📄 AI resume builder + enhancer
- ✍️ AI cover letter generator
- 📊 Application tracker (localStorage)
- 🌐 Deployable in 15 minutes
