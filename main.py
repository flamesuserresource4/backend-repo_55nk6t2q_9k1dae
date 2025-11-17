import os
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI(title="Sankalp Cricket Club API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Models (request bodies)
# ----------------------
class ClubConfigIn(BaseModel):
    club_name: Optional[str] = "Sankalp"
    play_cricket_club_id: Optional[str] = None
    play_cricket_team_id: Optional[str] = None
    play_cricket_api_key: Optional[str] = None

class PlayerIn(BaseModel):
    name: str
    role: str
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None
    photo_url: Optional[str] = None
    matches: Optional[int] = 0
    runs: Optional[int] = 0
    wickets: Optional[int] = 0
    catches: Optional[int] = 0

class FounderIn(BaseModel):
    name: str
    role: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    year: Optional[int] = None

# ----------------------
# Helpers
# ----------------------

def _collection(name: str):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return db[name]


def get_club_config() -> Dict[str, Any]:
    """Get a single club config document, create default if missing."""
    col = _collection("clubconfig")
    doc = col.find_one({})
    if not doc:
        default_doc = {
            "club_name": "Sankalp",
            "play_cricket_club_id": None,
            "play_cricket_team_id": None,
            "play_cricket_api_key": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        col.insert_one(default_doc)
        doc = default_doc
    # convert ObjectId
    doc["id"] = str(doc.get("_id")) if doc.get("_id") else None
    doc.pop("_id", None)
    return doc


def save_club_config(payload: ClubConfigIn) -> Dict[str, Any]:
    col = _collection("clubconfig")
    existing = col.find_one({})
    data = {k: v for k, v in payload.model_dump().items()}
    data["updated_at"] = datetime.utcnow()
    if existing:
        col.update_one({"_id": existing["_id"]}, {"$set": data})
        existing.update(data)
        doc = existing
    else:
        data["created_at"] = datetime.utcnow()
        col.insert_one(data)
        doc = data
    doc["id"] = str(doc.get("_id")) if doc.get("_id") else None
    doc.pop("_id", None)
    return doc


# ECB Play-Cricket integration
PLAY_CRICKET_BASE = "https://api.play-cricket.com/api/v2"


def fetch_play_cricket(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    cfg = get_club_config()
    api_key = cfg.get("play_cricket_api_key") or os.getenv("PLAY_CRICKET_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Play-Cricket API key not configured. Set it via /api/club-config.")

    # Build request
    q = {"apikey": api_key, **params}
    url = f"{PLAY_CRICKET_BASE}/{endpoint}"
    try:
        r = requests.get(url, params=q, timeout=10)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Play-Cricket API error: {r.status_code} {r.text[:120]}")
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error contacting Play-Cricket API: {str(e)}")


def sample_fixtures() -> List[Dict[str, Any]]:
    today = datetime.utcnow().date()
    return [
        {
            "date": str(today + timedelta(days=2)),
            "opposition": "Greenfield CC",
            "home_away": "Home",
            "ground": "Sankalp Oval",
            "competition": "Friendly T20",
            "start_time": "18:00",
        },
        {
            "date": str(today + timedelta(days=9)),
            "opposition": "Riverside CC",
            "home_away": "Away",
            "ground": "Riverside Park",
            "competition": "League",
            "start_time": "12:30",
        },
    ]


def sample_results() -> List[Dict[str, Any]]:
    today = datetime.utcnow().date()
    return [
        {
            "date": str(today - timedelta(days=3)),
            "opposition": "Harbor CC",
            "home_away": "Away",
            "ground": "Harbor Field",
            "competition": "League",
            "result": "Sankalp won by 5 wickets",
            "score": "Harbor 148/8 (40) — Sankalp 149/5 (37.2)",
        },
        {
            "date": str(today - timedelta(days=10)),
            "opposition": "Hilltop CC",
            "home_away": "Home",
            "ground": "Sankalp Oval",
            "competition": "Friendly T20",
            "result": "Sankalp lost by 7 runs",
            "score": "Hilltop 162/6 (20) — Sankalp 155/7 (20)",
        },
    ]


# ----------------------
# Routes
# ----------------------
@app.get("/")
def root():
    return {"message": "Sankalp Cricket Club API"}


@app.get("/api/club-config")
def get_config():
    return get_club_config()


@app.post("/api/club-config")
def update_config(payload: ClubConfigIn):
    return save_club_config(payload)


@app.get("/api/fixtures")
def get_fixtures(limit: Optional[int] = 10, season: Optional[int] = None):
    cfg = get_club_config()
    club_id = cfg.get("play_cricket_club_id")
    team_id = cfg.get("play_cricket_team_id")

    # If config not complete, return sample
    if not club_id or not team_id or not (cfg.get("play_cricket_api_key") or os.getenv("PLAY_CRICKET_API_KEY")):
        data = sample_fixtures()[: limit or 10]
        return {"source": "sample", "items": data}

    season = season or datetime.utcnow().year
    payload = {
        "club_id": club_id,
        "team_id": team_id,
        "season": season,
        "match_status": "Fixture",
    }
    raw = fetch_play_cricket("matches.json", payload)
    # Normalise a subset of fields for the frontend
    items = []
    for m in raw.get("matches", raw.get("data", [])):
        items.append({
            "date": m.get("match_date") or m.get("date"),
            "opposition": m.get("opposition_club_name") or m.get("opposition_name"),
            "home_away": m.get("home_away") or ("Home" if m.get("is_home") else "Away"),
            "ground": m.get("ground_name") or m.get("ground"),
            "competition": m.get("competition_name") or m.get("competition"),
            "start_time": m.get("start_time") or m.get("start_time_formatted"),
        })
    return {"source": "play-cricket", "items": items[: limit or 10]}


@app.get("/api/results")
def get_results(limit: Optional[int] = 10, season: Optional[int] = None):
    cfg = get_club_config()
    club_id = cfg.get("play_cricket_club_id")
    team_id = cfg.get("play_cricket_team_id")

    if not club_id or not team_id or not (cfg.get("play_cricket_api_key") or os.getenv("PLAY_CRICKET_API_KEY")):
        data = sample_results()[: limit or 10]
        return {"source": "sample", "items": data}

    season = season or datetime.utcnow().year
    payload = {
        "club_id": club_id,
        "team_id": team_id,
        "season": season,
        "match_status": "Result",
    }
    raw = fetch_play_cricket("matches.json", payload)
    items = []
    for m in raw.get("matches", raw.get("data", [])):
        summary = m.get("result") or m.get("result_description")
        score = m.get("home_club_scorecard") or m.get("score_summary")
        items.append({
            "date": m.get("match_date") or m.get("date"),
            "opposition": m.get("opposition_club_name") or m.get("opposition_name"),
            "home_away": m.get("home_away") or ("Home" if m.get("is_home") else "Away"),
            "ground": m.get("ground_name") or m.get("ground"),
            "competition": m.get("competition_name") or m.get("competition"),
            "result": summary,
            "score": score,
        })
    return {"source": "play-cricket", "items": items[: limit or 10]}


@app.get("/api/players")
def list_players():
    try:
        items = get_documents("player")
        # If empty, provide sample data
        if not items:
            items = [
                {
                    "name": "Aarav Patel",
                    "role": "All-rounder",
                    "batting_style": "RHB",
                    "bowling_style": "RMF",
                    "photo_url": "https://images.unsplash.com/photo-1521417531739-9ee39be9fb0a?q=80&w=600&auto=format&fit=crop",
                    "matches": 42,
                    "runs": 1250,
                    "wickets": 58,
                    "catches": 19,
                },
                {
                    "name": "Rohan Mehta",
                    "role": "Batter",
                    "batting_style": "RHB",
                    "bowling_style": None,
                    "photo_url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=600&auto=format&fit=crop",
                    "matches": 38,
                    "runs": 980,
                    "wickets": 4,
                    "catches": 12,
                },
                {
                    "name": "Vikram Shah",
                    "role": "Bowler",
                    "batting_style": "RHB",
                    "bowling_style": "LS",
                    "photo_url": "https://images.unsplash.com/photo-1549057446-9f5c6ac91a04?q=80&w=600&auto=format&fit=crop",
                    "matches": 45,
                    "runs": 320,
                    "wickets": 72,
                    "catches": 22,
                },
            ]
        # normalise ids
        for it in items:
            if it.get("_id"):
                it["id"] = str(it.pop("_id"))
        return {"items": items}
    except Exception as e:
        # On any database issue, still return sample
        return {"items": sample_results()}


@app.post("/api/players")
def add_player(player: PlayerIn):
    try:
        pid = create_document("player", player)
        return {"id": pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/founders")
def list_founders():
    try:
        items = get_documents("founder")
        if not items:
            items = [
                {
                    "name": "S. Nair",
                    "role": "Founder",
                    "bio": "Brought the community together to form Sankalp CC.",
                    "photo_url": "https://images.unsplash.com/photo-1539683255143-73a6b838b106?q=80&w=600&auto=format&fit=crop",
                    "year": 2011,
                },
                {
                    "name": "A. Desai",
                    "role": "Co-Founder",
                    "bio": "Early captain and coach, grew the junior program.",
                    "photo_url": "https://images.unsplash.com/photo-1544717302-de2939b7ef71?q=80&w=600&auto=format&fit=crop",
                    "year": 2011,
                },
            ]
        for it in items:
            if it.get("_id"):
                it["id"] = str(it.pop("_id"))
        return {"items": items}
    except Exception:
        return {"items": []}


@app.post("/api/founders")
def add_founder(founder: FounderIn):
    try:
        fid = create_document("founder", founder)
        return {"id": fid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
