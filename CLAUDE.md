# Gestion des Arbitres — instructions

Spécification complète : **`docs/PROJECT_SPEC.md`** (source de vérité).
État d'avancement et décisions d'architecture : **`docs/ARCHITECTURE.md`**.

## Structure

- `backend/` — FastAPI + SQLAlchemy 2.0 async + Alembic + ARQ
- `frontend/` — React + Vite + TypeScript + Tailwind v4
- `docker-compose.yml` — api, worker, db (Postgres 16), redis, web

## Commandes

```bash
# Backend (depuis backend/, venv déjà créé dans .venv)
./.venv/Scripts/python.exe -m pytest tests/ -q        # tests
./.venv/Scripts/python.exe -m ruff check app tests    # lint
./.venv/Scripts/python.exe -m ruff format app tests   # format
./.venv/Scripts/python.exe -m mypy app scripts        # types (strict)
./.venv/Scripts/python.exe -m alembic upgrade head    # migrations
./.venv/Scripts/python.exe -m alembic check           # dérive modèles/migrations
./.venv/Scripts/python.exe -m scripts.seed --demo     # amorçage

# Frontend (depuis frontend/)
npm test && npm run typecheck && npm run lint && npm run build
```

Sous Linux/macOS, remplacer `./.venv/Scripts/python.exe` par `.venv/bin/python`.

## Règles de travail

- **Un jalon à la fois.** Ne pas démarrer un jalon tant que les tests du précédent
  ne passent pas. Jalons dans `docs/PROJECT_SPEC.md` §10.
- **Couches strictes** : `router` (HTTP) → `service` (règles métier) → `repository` (ORM).
  Un router ne touche jamais à l'ORM ; une règle métier ne vit jamais dans un router.
- **Les règles métier vont dans les services** (« on ne convoque pas sur un tournoi
  annulé », « on ne confirme pas un tournoi passé »).
- **Autorisation** : uniquement via les dépendances de `app/api/deps.py`
  (`CurrentUser`, `AdminUser`, `RefereeUser`). Jamais de contrôle de rôle ailleurs,
  jamais de confiance dans le frontend.
- **Erreurs** : lever les exceptions de `app/services/errors.py`. Le gestionnaire
  de `app/main.py` les traduit en réponses HTTP — pas de `HTTPException` dans les services.
- **Chaque endpoint** : schémas Pydantic + fonction de service + fonction de repository
  + tests (cas nominal **et** refus d'authentification/autorisation).
- **Chaque changement de modèle** passe par une migration Alembic
  (`alembic revision --autogenerate`), jamais par une modification manuelle de la base.
  Vérifier ensuite `alembic check`.
- **Notifications** : jamais envoyées dans la requête HTTP. L'API crée une ligne
  `notifications` (`queued`) et met un job en file ; le worker envoie.
- **Tests** : toujours `NOTIFICATION_PROVIDER=console`. Aucun appel à la vraie API WhatsApp.
- **Frontend** : textes en français via les clés de `src/i18n/fr.ts`, jamais en dur.
  Régénérer le client API (`npm run api:generate`) après un changement de schéma backend.
- **Numéros de téléphone** : toujours normalisés en E.164 via `app/services/phone.py`.
