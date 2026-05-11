# Rhichbel SPA — Aesthetics Centre Backend & Frontend

A Flask-based backend serving a static luxury spa/aesthetics website with appointment booking features.

## Project Structure

```
RichbelSPA-AestheticsCentre/
├── app.py                      # Main Flask app entry point
├── config.py                   # Configuration (dev/prod/test)
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (DO NOT COMMIT)
├── .env.example                # Template for .env
├── .gitignore                  # Git ignore rules
│
├── static/                     # Served public assets (CSS, JS, images)
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/                 # Place your spa images here
│
├── templates/                  # Jinja2 HTML templates
│   └── index.html
│
├── assets/                     # Raw media (before optimization)
│                               # Paste your original images here
│
├── routes/                     # API route blueprints (future)
│   └── __init__.py
│
├── models/                     # Database models (future)
│   └── __init__.py
│
└── utils/                      # Helper functions (future: email, validation)
    └── __init__.py
```

## Quick Start

### 1. Setup Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```bash
cp .env.example .env
```

Then edit `.env`:
```
FLASK_ENV=development
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
```

### 3. Run Flask Locally

```bash
python app.py
# or
flask run
```

Open browser: `http://localhost:5000`

### 4. Test API Endpoint

```bash
curl http://localhost:5000/api/services
```

## Adding Images

1. **Raw branding/originals**: Drop into `assets/` folder (large, unoptimized).
2. **Web-ready images**: Optimize and place in `static/images/`.
3. **Update index.html**: Reference images in `templates/index.html` as needed.

## Deployment (Render)

1. Push repo to GitHub.
2. Connect Render → GitHub → new Web Service.
3. Environment: Python 3.11+
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Add Supabase secrets in Render Environment.
7. Deploy.

## API Endpoints

| Route | Method | Description |
|-------|--------|------------|
| `/` | GET | Homepage (static) |
| `/health` | GET | Health check |
| `/api/services` | GET | List bookable services (from Supabase) |

Query params for `/api/services`:
- `bookable=true` (default) — Only return priced services
- `bookable=false` — Return all services including unpriced

## Next Steps

- [ ] Add booking form to frontend
- [ ] Create `/api/appointments` POST endpoint
- [ ] Add admin dashboard + appointment management
- [ ] Email notifications for confirmations
- [ ] Stripe/payment integration (optional)

## Notes

- Never commit `.env` (use `.env.example` as template).
- Service Role Key stays server-side only.
- ANON_KEY used only for RLS policies on direct client calls.
- Flask uses CORS for cross-origin requests (configured in `config.py`).