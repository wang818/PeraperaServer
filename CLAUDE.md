# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PeraperaServer is a FastAPI backend for a language-learning companion app (PeraPera). It provides JWT authentication via email captcha, multi-language i18n (18 languages), YouTube audio/video downloading through RapidAPI, and user settings management. The app uses async PostgreSQL with SQLAlchemy and runs behind Nginx in production.

## Commands

```bash
# Run dev server
python3 run.py
# Or directly:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Install dependencies (in venv)
pip3 install -r requirements.txt

# Run tests
pytest

# Alembic migrations
alembic revision --autogenerate -m "description"   # create migration
alembic upgrade head                                 # apply migrations

# Production deployment
bash deploy/deploy.sh                               # automated deploy script
sudo systemctl restart perapera.service             # restart after code changes
sudo journalctl -u perapera.service -f              # tail app logs
```

## Architecture

```
app/
├── main.py                   # FastAPI app, CORS, lifespan (init_db on startup)
├── api/v1/
│   ├── router.py             # Aggregates auth, users, common routers under /api/v1
│   └── endpoints/
│       ├── auth.py           # POST /auth/login (captcha), GET /auth/sendCaptcha
│       ├── users.py          # GET /users/me, GET|PUT /users/users_setting
│       └── common.py         # GET /common/support_lang, /common/yt_audio, /common/yt_video
├── core/
│   ├── config.py             # Pydantic BaseSettings, reads .env
│   ├── database.py           # Async SQLAlchemy engine, session factory, get_db dep
│   ├── security.py           # Password hash (SHA256 pre-hash + bcrypt), JWT create/decode
│   ├── dependencies.py       # FastAPI Depends for Accept-Language header
│   ├── email.py              # aiosmtplib email sending with STARTTLS→SSL fallback
│   ├── i18n.py               # In-code TRANSLATIONS dict (18 languages), get_translation()
│   └── support_lang.py       # Supported language list for the API
├── models/
│   ├── user.py               # User table (id, uuid, email, username, hashed_password, is_active)
│   ├── user_setting.py       # UserSetting table (subtitle prefs, echo mode, theme, font size, etc.)
│   └── captcha.py            # CaptchaRecord table (email, captcha code, send_count, expires_at)
├── schemas/
│   ├── user.py               # Pydantic: UserCreate, UserResponse, Token, CaptchaLogin
│   └── user_setting.py       # Pydantic: UserSettingCreate/Update/Response
└── services/
    └── cos_service.py        # Tencent Cloud COS upload (singleton), hash_filename helper
```

## Key Design Decisions

**Captcha-based auth with auto-registration.** There is no traditional password signup. `POST /auth/login` with `{email, captcha}` verifies the 6-digit code against `captcha_records`. If the user doesn't exist, an account is auto-created with a random 32-char password. `GET /auth/sendCaptcha` has tiered rate limiting: unlimited under 3/day, 15-min cooldown at 3–4/day, 1-hour cooldown at 5+/day.

**Password pre-hashing.** `security.py` SHA256-hashes passwords before bcrypt to handle bcrypt's 72-byte limit. Always use `get_password_hash()` and `verify_password()` — never call bcrypt directly.

**i18n is entirely in-code.** All translations live in `app/core/i18n.py` as a nested dict (`TRANSLATIONS[key][lang]`). Language is extracted from the `Accept-Language` header via `get_language` dependency. Add new keys to the dict; pass format kwargs via `get_translation(key, lang, **kwargs)`.

**YouTube downloading with cascading fallbacks.** Both `yt_audio` and `yt_video` endpoints try multiple RapidAPI services in sequence, catching exceptions silently and moving to the next. Audio is uploaded to Tencent Cloud COS (MD5-hashed filename); video is returned directly as `FileResponse`. All RapidAPI keys come from the `RAPIDAPI_KEY` env var.

**Tables auto-created on startup.** `main.py`'s lifespan calls `init_db()` which runs `Base.metadata.create_all`. Alembic exists for migrations but base tables are created automatically in dev.

**UserSetting is keyed by `user_uuid` (UUID), not `user.id` (integer).** When creating a user, also create their `UserSetting` row. The `users_setting` table stores subtitle language preferences, echo/repeat mode toggles, font size, theme, and JP-specific features (romaji, furigana, speech part analysis).

## Environment Variables

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL` — `postgresql+asyncpg://user:pass@host:5432/perapera_db`
- `SECRET_KEY` — JWT signing key (must change in production)
- `RAPIDAPI_KEY` — YouTube download API key
- `COS_SECRET_ID`, `COS_SECRET_KEY`, `COS_BUCKET`, `COS_REGION` — Tencent Cloud Object Storage
- `SMTP_*` — Email sending via Gmail (app-specific password required)
- `ALLOWED_ORIGINS` — Comma-separated CORS origins

## API Docs

When `DEBUG=True`, Swagger UI at `/docs` and ReDoc at `/redoc`. When `DEBUG=False`, all docs endpoints are disabled (return `None`).
