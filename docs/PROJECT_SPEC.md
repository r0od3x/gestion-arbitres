# Gestion des Arbitres — Project Spec & Architecture

> Working spec for a referee management platform. Intended as the source of truth for Claude Code.
> Scope: **MVP skeleton** — accounts, tournaments, referee assignment, WhatsApp notifications.

---

## 1. Overview

A web platform where:

- **Referees** each have an account with their personal and refereeing info (including a WhatsApp number).
- **Admins** create and publish tournaments, then select which referees must attend.
- Selected referees are **notified automatically by WhatsApp** and can see their convocations in their dashboard.

### Roles

| Role | Can do |
|------|--------|
| `admin` | Manage referees (invite, activate/deactivate, edit), create/edit/publish/cancel tournaments, assign referees, resend notifications, see notification status |
| `referee` | Log in, edit own profile (within allowed fields), see tournaments they're convoked to, confirm/decline a convocation |

### Core user flows

1. **Onboarding**: Admin invites a referee by email → referee sets password → completes profile (phone, grade, etc.) and gives WhatsApp consent.
   *(Alternative later: self-signup with admin approval.)*
2. **Tournament creation**: Admin creates a tournament as `draft` (title, dates, location, description, needed referees).
3. **Assignment**: Admin filters referees (grade, city, active) and selects who must attend.
4. **Convocation**: Admin clicks "Send convocations" → an assignment row is created per referee → a WhatsApp notification job is queued for each.
5. **Delivery tracking**: A background worker sends the WhatsApp message; provider webhooks update status (`sent` / `delivered` / `read` / `failed`).
6. **Response**: Referee confirms or declines from the web dashboard (phase 2: directly via WhatsApp quick-reply buttons).

---

## 2. Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend API | **FastAPI** (Python 3.12) | Async, typed, auto OpenAPI docs |
| ORM / migrations | **SQLAlchemy 2.0** (async) + **Alembic** | Mature, explicit, good migrations |
| Validation | **Pydantic v2** | Native with FastAPI |
| Database | **PostgreSQL 16** | Relational data, constraints, enums |
| Background jobs | **ARQ** + **Redis** | Lightweight async job queue for WhatsApp sends + retries |
| Auth | JWT access token (short) + refresh token (httpOnly cookie), passwords hashed with **argon2** | Stateless API, secure cookies |
| Frontend | **React + Vite + TypeScript** | SPA dashboard |
| UI | **Tailwind CSS** + **shadcn/ui** | Fast, consistent admin UI |
| Data fetching | **TanStack Query** + typed API client generated from OpenAPI | No hand-written fetch boilerplate |
| Forms | **React Hook Form** + **Zod** | Typed forms |
| Routing | **React Router** | Role-based route guards |
| WhatsApp | **Meta WhatsApp Cloud API** (behind a provider interface; Twilio as alternative) | Official, template messages, delivery webhooks |
| Dev env | **Docker Compose** (api, worker, db, redis, web) | One-command setup |
| Tests | **pytest** + httpx (backend), **Vitest** (frontend) | |
| Lint/format | **ruff** + **mypy** (backend), **ESLint** + **Prettier** (frontend) | |

**Defaults:** UI language French (i18n-ready), timezone `Africa/Casablanca`, phone numbers stored in **E.164** (`+2126XXXXXXXX`).

---

## 3. Architecture

```
┌──────────────┐     HTTPS/JSON     ┌──────────────────┐        ┌──────────────┐
│ React SPA    │ ─────────────────▶ │ FastAPI (api)    │ ─────▶ │ PostgreSQL   │
│ admin/referee│ ◀───────────────── │  routers         │        └──────────────┘
└──────────────┘                    │  services        │
                                    │  repositories    │ enqueue ┌──────────┐
                                    └────────┬─────────┘ ──────▶ │  Redis   │
                                             │                   └────┬─────┘
                                             │ webhook (status)       │ jobs
┌──────────────────┐                         │                   ┌────▼─────────┐
│ WhatsApp Cloud   │ ────────────────────────┘                   │ ARQ worker   │
│ API (Meta)       │ ◀────────────────────────────────────────── │ send_whatsapp│
└──────────────────┘          send template message              └──────────────┘
```

### Key principles

- **Layered backend**: `router` (HTTP only) → `service` (business rules) → `repository` (DB access). Routers never touch the ORM directly.
- **Notifications are never sent inside the HTTP request.** The API writes a `notification` row (status `queued`) and enqueues a job; the worker sends it. This keeps the API fast and allows retries.
- **Provider abstraction**: `NotificationProvider` interface with implementations `WhatsAppCloudProvider`, `TwilioProvider`, and `ConsoleProvider` (logs only, used in dev/tests). Selected via env var.
- **Idempotency**: one notification per (assignment, type); resending creates a new attempt, not a duplicate assignment.
- **Authorization in one place**: FastAPI dependencies `get_current_user`, `require_admin`, `require_referee`.

---

## 4. Data Model

```
users
  id (uuid, pk)
  email (unique)
  password_hash
  role (enum: admin, referee)
  is_active (bool)
  created_at, updated_at

referee_profiles
  id (uuid, pk)
  user_id (fk users, unique)
  first_name, last_name
  phone_e164 (unique)
  whatsapp_opt_in (bool)          -- explicit consent
  whatsapp_opt_in_at (timestamp)
  grade (enum: regional, national, continental, international)
  license_number (nullable, unique)
  city
  club / league (nullable)
  photo_url (nullable)
  notes_admin (nullable, admin-only)

tournaments
  id (uuid, pk)
  title
  description (text)
  location / venue
  city
  start_date, end_date
  convocation_time (nullable)      -- when referees must be present
  referees_needed (int, nullable)
  status (enum: draft, published, cancelled, completed)
  created_by (fk users)
  created_at, updated_at

tournament_assignments
  id (uuid, pk)
  tournament_id (fk)
  referee_id (fk referee_profiles)
  role_in_tournament (nullable, e.g. referee / table official)
  status (enum: pending, confirmed, declined, cancelled)
  responded_at (nullable)
  assigned_by (fk users)
  created_at
  UNIQUE (tournament_id, referee_id)

notifications
  id (uuid, pk)
  assignment_id (fk, nullable)     -- nullable to allow generic messages later
  recipient_phone_e164
  channel (enum: whatsapp)
  type (enum: convocation, update, cancellation, reminder)
  template_name
  payload (jsonb)                  -- template variables
  status (enum: queued, sent, delivered, read, failed)
  provider_message_id (nullable, indexed)
  error (nullable)
  attempts (int)
  created_at, sent_at, updated_at

audit_logs (phase 2)
  id, actor_id, action, entity, entity_id, data (jsonb), created_at
```

---

## 5. API (v1)

All routes prefixed with `/api/v1`.

**Auth**
- `POST /auth/login` → access token + refresh cookie
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/accept-invite` (token + password)
- `POST /auth/forgot-password`, `POST /auth/reset-password` (phase 2)

**Me (referee)**
- `GET /me` · `PATCH /me/profile`
- `GET /me/assignments` (upcoming + past)
- `POST /me/assignments/{id}/confirm` · `POST /me/assignments/{id}/decline`

**Referees (admin)**
- `GET /referees?grade=&city=&active=&q=` (paginated)
- `POST /referees/invite`
- `GET /referees/{id}` · `PATCH /referees/{id}` · `POST /referees/{id}/deactivate`

**Tournaments**
- `GET /tournaments` (admin: all; referee: published ones they're assigned to)
- `POST /tournaments` · `GET /tournaments/{id}` · `PATCH /tournaments/{id}`
- `POST /tournaments/{id}/publish` · `POST /tournaments/{id}/cancel`

**Assignments (admin)**
- `GET /tournaments/{id}/assignments`
- `PUT /tournaments/{id}/assignments` — body: list of referee IDs (diff-based: adds new, cancels removed)
- `POST /tournaments/{id}/convocations/send` — queues WhatsApp for all pending, not-yet-notified assignments
- `POST /assignments/{id}/notifications/resend`

**Webhooks**
- `GET /webhooks/whatsapp` — Meta verification challenge
- `POST /webhooks/whatsapp` — delivery status updates (verify `X-Hub-Signature-256`)

---

## 6. WhatsApp Notifications

- Use **Meta WhatsApp Cloud API**. Business-initiated messages **must use pre-approved message templates** (free text only works within 24h after the user messages you).
- Create a template, e.g. `convocation_tournoi` (French), with variables:
  `{{1}}` referee first name, `{{2}}` tournament title, `{{3}}` date, `{{4}}` location, `{{5}}` convocation time.
- Additional templates later: `tournoi_modifie`, `tournoi_annule`, `rappel_tournoi` (reminder 24–48h before).
- Only send to referees with `whatsapp_opt_in = true` and a valid E.164 number; otherwise mark notification `failed` with a clear error and surface it in the admin UI.
- Worker retries with exponential backoff (e.g. 3 attempts) on network/5xx errors; no retry on 4xx validation errors.
- Webhook updates `notifications.status` by `provider_message_id`.
- **Phase 2:** template with quick-reply buttons ("Je confirme" / "Je ne peux pas") → webhook maps the reply to the assignment and updates its status.
- Development: use Meta's test phone number, or set `NOTIFICATION_PROVIDER=console`.

---

## 7. Project Structure

```
gestion-arbitres/
├── CLAUDE.md                  # short instructions for Claude Code, points to this spec
├── docs/PROJECT_SPEC.md       # this file
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── app/
│   │   ├── main.py            # FastAPI app factory, routers, CORS
│   │   ├── core/              # config (pydantic-settings), security, logging
│   │   ├── db/                # engine, session, base model
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── repositories/
│   │   ├── services/          # auth, referees, tournaments, assignments, notifications
│   │   ├── notifications/     # provider interface + whatsapp_cloud, twilio, console
│   │   ├── api/
│   │   │   ├── deps.py        # get_db, get_current_user, require_admin
│   │   │   └── v1/            # routers per resource + webhooks
│   │   └── worker/            # ARQ settings + tasks (send_whatsapp)
│   ├── scripts/seed.py        # create first admin + demo data
│   └── tests/
└── frontend/
    ├── package.json
    ├── src/
    │   ├── api/               # generated client + TanStack Query hooks
    │   ├── auth/              # auth context, route guards
    │   ├── components/        # shared UI (shadcn)
    │   ├── features/
    │   │   ├── referees/
    │   │   ├── tournaments/
    │   │   ├── assignments/
    │   │   └── profile/
    │   ├── pages/
    │   │   ├── admin/         # dashboard, referees, tournaments, tournament detail
    │   │   └── referee/       # my convocations, profile
    │   ├── i18n/              # fr (default)
    │   └── main.tsx
    └── tests/
```

---

## 8. Environment Variables

```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://redis:6379/0
JWT_SECRET=
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=7
FRONTEND_URL=http://localhost:5173
NOTIFICATION_PROVIDER=console        # console | whatsapp_cloud | twilio
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_APP_SECRET=                 # for webhook signature verification
WHATSAPP_VERIFY_TOKEN=               # for webhook GET challenge
DEFAULT_TIMEZONE=Africa/Casablanca
```

---

## 9. Security & Data Protection

- Passwords hashed with argon2; refresh token in httpOnly, Secure, SameSite cookie.
- Role checks enforced server-side on every route (never trust the frontend).
- Referees can only read/edit their own profile and assignments.
- Phone numbers and personal data are sensitive: collect explicit WhatsApp consent, restrict admin-only fields, and follow Moroccan personal data law (Loi 09-08 / CNDP).
- Verify WhatsApp webhook signatures; rate-limit auth endpoints.
- Never log full access tokens or WhatsApp API tokens.

---

## 10. Build Plan (Milestones)

**M1 — Foundation**
- Docker Compose (api, worker, db, redis, web), backend skeleton, config, Alembic, health check.
- User + referee profile models, seed script for first admin.
- Auth (login/refresh/logout), role dependencies, tests.

**M2 — Referees**
- Admin: invite, list/filter/search, edit, deactivate.
- Referee: accept invite, complete profile, WhatsApp consent, phone validation (E.164).
- Frontend: login, admin referees pages, referee profile page.

**M3 — Tournaments & Assignments**
- Tournament CRUD + status transitions (draft → published → completed / cancelled).
- Assignment selection UI (filterable referee picker), diff-based assignment update.
- Referee "My convocations" page + confirm/decline.

**M4 — WhatsApp Notifications**
- Provider interface + console provider + WhatsApp Cloud provider.
- `send convocations` endpoint → notification rows → ARQ jobs with retries.
- Webhook for delivery status; admin view of per-referee notification status + resend.

**M5 — Polish (phase 2)**
- Quick-reply confirm/decline via WhatsApp, reminders before tournament, cancellation/update messages.
- Audit log, CSV export of convocations, password reset, referee availability calendar.

---

## 11. Conventions for Claude Code

- Work milestone by milestone; don't start a milestone before the previous one's tests pass.
- Every new endpoint: Pydantic schemas, service function, repository function, tests (happy path + auth failure).
- Every model change goes through an Alembic migration — never edit the DB by hand.
- Use the `console` notification provider in tests; never call the real WhatsApp API in tests.
- Keep business rules in services (e.g. "can't assign to a cancelled tournament", "can't confirm a past tournament").
- Regenerate the frontend API client after changing backend schemas.
- UI text in French via i18n keys, not hardcoded strings.
