# Kingdom Ways — Church Visitor Register

A multi-tenant church visitor registration system. Each church gets its own
branded sign-in form and a private password-protected admin dashboard.

---

## Quick Start (local)

```bash
pip install -r requirements.txt
python server.py
```

- Visitor form: http://localhost:5000/kingdom-ways  
- Admin dashboard: http://localhost:5000/kingdom-ways/admin  
- Default password: `admin123`  
- Add new church: http://localhost:5000/setup/new-church  

---

## Deploy to Railway (recommended, ~5 mins)

1. Push this folder to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Set these environment variables in Railway:
   - `SECRET_KEY` → any long random string
   - `SETUP_KEY`  → a secret key only you know (used to create new churches)
4. Railway auto-detects the Procfile and deploys

Your live URLs will look like:
- `https://your-app.railway.app/kingdom-ways`       ← visitor form
- `https://your-app.railway.app/kingdom-ways/admin` ← admin dashboard

---

## Adding a new church

Visit `/setup/new-church` on your live server and fill in:
- Church name
- URL slug (e.g. `grace-community`)
- Admin password (church chooses their own)
- Your SETUP_KEY

The church then gets:
- A visitor form at `/<slug>`
- An admin dashboard at `/<slug>/admin`
- A QR code you can generate pointing to their form URL

---

## Environment variables

| Variable    | Default      | Description                              |
|-------------|--------------|------------------------------------------|
| SECRET_KEY  | random       | Flask session secret (set in production) |
| SETUP_KEY   | `changeme`   | Key to create new church accounts        |
| DB_FILE     | `church.db`  | SQLite database path                     |
| PORT        | `5000`       | Server port                              |

---

## File structure

```
church/
├── server.py            ← Flask app (routes, DB, auth)
├── requirements.txt
├── Procfile             ← for Railway/Render deployment
├── README.md
└── templates/
    ├── form.html        ← visitor sign-in form
    ├── login.html       ← admin login
    ├── admin.html       ← admin dashboard (stats + table + export)
    └── new_church.html  ← onboard a new church
```
