# Gestion des Arbitres

Plateforme de convocation des arbitres aux tournois, avec notification WhatsApp.

- **Administrateurs** : gèrent les arbitres, créent les tournois, désignent les
  arbitres convoqués et suivent la réception des messages.
- **Arbitres** : consultent leurs convocations et répondent (confirmer / décliner).

Spécification : [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) ·
Architecture et avancement : [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Démarrage avec Docker

```bash
cp .env.example .env          # puis renseigner JWT_SECRET
docker compose up --build
docker compose exec api python -m scripts.seed --demo
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Documentation OpenAPI | http://localhost:8000/docs |
| Interface web | http://localhost:5173 |

## Démarrage sans Docker

La base par défaut est SQLite : ni Postgres ni Redis ne sont nécessaires pour
lancer l'API et les tests. Redis n'est requis que pour le worker.

### Backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Linux/macOS : .venv/bin/python
./.venv/Scripts/python.exe -m alembic upgrade head
./.venv/Scripts/python.exe -m scripts.seed --demo
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Worker (nécessite Redis)

```bash
cd backend
./.venv/Scripts/arq.exe app.worker.settings.WorkerSettings
```

## Comptes de démonstration

Créés par `scripts/seed.py --demo` :

| Rôle | E-mail | Mot de passe |
|------|--------|--------------|
| Administrateur | `admin@example.com` | `ChangeMe!2026` |
| Arbitres (×4) | `prénom.nom@example.ma` | `Arbitre!2026` |

Ces identifiants sont réservés au développement : changer `FIRST_ADMIN_PASSWORD`
avant tout déploiement.

## Qualité

```bash
cd backend
./.venv/Scripts/python.exe -m pytest tests/ -q      # 138 tests
./.venv/Scripts/python.exe -m ruff check app tests scripts alembic
./.venv/Scripts/python.exe -m mypy app scripts      # strict
./.venv/Scripts/python.exe -m alembic check         # dérive modèles/migrations

cd ../frontend
npm test && npm run typecheck && npm run lint && npm run build   # 58 tests
```

## WhatsApp

En développement, `NOTIFICATION_PROVIDER=console` : les messages sont journalisés
au lieu d'être envoyés. Aucun compte Meta n'est nécessaire, et les tests
n'appellent jamais l'API réelle.

Pour un envoi réel, passer à `whatsapp_cloud` et renseigner
`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET` et
`WHATSAPP_VERIFY_TOKEN`. Les messages à l'initiative de l'entreprise exigent un
**template approuvé par Meta** (voir `docs/PROJECT_SPEC.md` §6).
