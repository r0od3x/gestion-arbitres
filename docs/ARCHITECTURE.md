# Architecture — état d'avancement et décisions

Complète `PROJECT_SPEC.md` : ce document enregistre **ce qui est construit** et
**les décisions prises en cours de route**, avec leurs raisons.

Dernière mise à jour : 23 octobre 2026.

---

## 1. Avancement par jalon

| Jalon | État | Détail |
|-------|------|--------|
| **M1 — Fondations** | ✅ terminé | Squelette, config, Alembic, santé, auth, rôles, amorçage, tests |
| **M2 — Arbitres** | ⬜ à faire | Invitation, liste/filtres, édition, désactivation, consentement WhatsApp |
| **M3 — Tournois & désignations** | ⬜ à faire | CRUD, transitions de statut, sélection des arbitres, confirmer/décliner |
| **M4 — Notifications WhatsApp** | 🟡 socle prêt | Interface fournisseur, provider Cloud API, worker et suivi de livraison faits ; reste l'endpoint `convocations/send` et le webhook HTTP |
| **M5 — Finitions** | ⬜ à faire | Boutons de réponse WhatsApp, rappels, journal d'audit, export CSV |

### Ce qui fonctionne aujourd'hui

- `POST /api/v1/auth/login` · `/refresh` · `/logout` · `/accept-invite` · `GET /auth/me`
- `GET /api/v1/healthz` · `/readyz`
- Les cinq tables du modèle de données, créées par une migration Alembic
- Worker ARQ et envoi de notifications avec relances (testés hors HTTP)
- SPA React : connexion, gardes de route par rôle, mise en page, pages d'attente

Vérifié de bout en bout sur un serveur réel : connexion → cookie `refresh_token`
httpOnly → appel authentifié → rafraîchissement du jeton.

**Qualité** : 64 tests backend, 15 tests frontend, `ruff` et `mypy --strict`
sans erreur, `alembic check` sans dérive.

---

## 2. Décisions prises pendant la construction

Les écarts ou précisions par rapport à `PROJECT_SPEC.md`, et pourquoi.

### 2.1 SQLite accepté en développement, Postgres en cible

`DATABASE_URL` accepte les deux. Les types sont choisis pour être portables :
`sa.Uuid` (UUID natif sur Postgres, `CHAR(32)` ailleurs), énumérations en
`VARCHAR` + contrainte, et `JSON().with_variant(JSONB, "postgresql")` pour
`notifications.payload`.

*Pourquoi* : l'API et les tests tournent sans Docker ni service externe, ce qui
raccourcit la boucle de développement. Postgres reste la cible :
`docker-compose.yml` et la CI doivent l'utiliser, car SQLite ne contrôle pas
tout (contraintes différées, types natifs).

### 2.2 Les énumérations ne sont pas des types natifs Postgres

`native_enum=False` : les énumérations sont stockées en `VARCHAR` avec une
contrainte `CHECK`.

*Pourquoi* : ajouter une valeur à un `ENUM` Postgres demande un `ALTER TYPE`
difficile à annuler dans une migration. Une contrainte `CHECK` se modifie
normalement. Le domaine est encore susceptible de bouger (grades, types de
notification).

### 2.3 Toutes les tables sont créées dès M1

La migration initiale crée les cinq tables, pas seulement `users` et
`referee_profiles`.

*Pourquoi* : le modèle de données est entièrement spécifié, et une seule
migration initiale propre vaut mieux que cinq migrations successives. Les
endpoints, eux, restent livrés jalon par jalon.

### 2.4 Le socle de notification est livré avec M1

L'interface fournisseur, `ConsoleProvider`, `WhatsAppCloudProvider`, le worker
ARQ et `NotificationService` existent déjà, avec leurs tests.

*Pourquoi* : c'est la pièce d'architecture la plus structurante (séparation
API/worker, classement des erreurs, idempotence). La valider tôt évite de
découvrir tard que la forme est mauvaise. M4 n'aura plus qu'à brancher
l'endpoint de convocation et le webhook.

### 2.5 Mot de passe nullable sur `users`

`users.password_hash` est `NULL` tant que l'invitation n'est pas acceptée.

*Pourquoi* : un arbitre invité existe en base avant d'avoir un mot de passe.
L'alternative (mot de passe aléatoire jeté) rendrait indistinguables
« invitation en attente » et « compte actif ». `AuthService.authenticate` refuse
ces comptes avec le même message que des identifiants faux.

### 2.6 Le jeton de rafraîchissement est limité à `/api/v1/auth`

Le cookie est posé avec `path=/api/v1/auth`.

*Pourquoi* : il n'est utile qu'aux routes d'authentification. Le limiter réduit
sa surface d'exposition — il n'accompagne pas chaque appel API.

### 2.7 Connexion : réponse de durée constante

`AuthService.authenticate` vérifie le mot de passe contre un hash factice quand
l'e-mail est inconnu, et renvoie le même message dans tous les cas.

*Pourquoi* : sans cela, le temps de réponse révèle si une adresse est inscrite
(énumération de comptes). Le message unique ferme la même fuite côté contenu.

### 2.8 Erreurs métier plutôt que `HTTPException`

Les services lèvent les exceptions de `app/services/errors.py` ; un gestionnaire
unique dans `app/main.py` les traduit en JSON `{detail, code}`.

*Pourquoi* : les services restent testables sans FastAPI, le format d'erreur est
uniforme pour le frontend, et les règles métier ne dépendent pas du transport
HTTP.

### 2.9 Les webhooks de livraison ne peuvent pas faire régresser un statut

`NotificationService.apply_provider_status` compare un rang
(`queued < sent < delivered < read`) et ignore tout statut moins avancé.

*Pourquoi* : Meta ne garantit pas l'ordre d'arrivée des webhooks. Un `sent`
livré après un `read` ferait reculer l'affichage administrateur.

### 2.10 Relance selon le type d'erreur, pas systématique

`SendResult.retryable` est vrai sur erreur réseau, 5xx, 408 et 429 ; faux sur
les autres 4xx. Une notification relançable reste `queued` jusqu'à épuisement de
`NOTIFICATION_MAX_ATTEMPTS`, puis passe à `failed`.

*Pourquoi* : réessayer un template inexistant ou un numéro invalide échouera
autant de fois et retardera la file. Ces erreurs doivent remonter vite à l'admin.

### 2.11 Limitation de débit en mémoire

`SlidingWindowLimiter` stocke les tentatives dans le process (10 connexions par
IP / 5 minutes).

*Pourquoi* : suffisant pour un process unique et sans dépendance. **Limite
connue** : avec plusieurs workers, chacun a son compteur. Passer le stockage sur
Redis avant de déployer en multi-process.

### 2.12 Jeton d'accès en mémoire côté SPA

Il vit dans un module JavaScript, jamais dans `localStorage`, et la session est
restaurée au chargement via `POST /auth/refresh`.

*Pourquoi* : `localStorage` est lisible par tout script de la page — un XSS
donnerait le jeton. En mémoire, il disparaît au rechargement, et le cookie
httpOnly reprend la session sans redemander le mot de passe.

### 2.13 i18n sans bibliothèque

`src/i18n/` expose un `t()` typé sur un dictionnaire français.

*Pourquoi* : une clé absente devient une erreur de compilation, sans ajouter de
dépendance. Si le pluriel, les dates relatives ou le changement de langue à
chaud deviennent nécessaires, migrer vers i18next — la forme d'appel `t('clé')`
ne change pas.

---

## 3. Limites connues

À traiter avant une mise en production :

1. **Rate limiting non partagé** entre process (voir 2.11) → passer sur Redis.
2. **Déconnexion non révocable** : les jetons d'accès restent valides jusqu'à
   leur expiration (15 min) même après `logout`. Pour une révocation immédiate,
   tenir une liste de `jti` révoqués dans Redis.
3. **Réutilisation d'un jeton de rafraîchissement non détectée** : un jeton volé
   reste utilisable jusqu'à expiration. Stocker les `jti` émis permettrait de
   repérer une réutilisation.
4. **`COOKIE_SECURE=false` par défaut** pour le développement en HTTP.
   **Obligatoirement `true` en production.**
5. **Journal d'audit absent** (table prévue en phase 2). Les données
   personnelles des arbitres relèvent de la loi 09-08 (CNDP) : tracer les accès
   administrateurs.
6. **Postgres non exercé par les tests** : la CI doit lancer la suite sur
   Postgres 16 en plus de SQLite.

---

## 4. Prochaine étape — M2

Dans l'ordre, en suivant les conventions de `CLAUDE.md` :

1. `schemas/referee.py` — invitation, mise à jour admin, filtres de recherche.
2. `services/referees.py` — invitation (crée `User` + `RefereeProfile` sans mot
   de passe, renvoie le lien d'invitation), édition, désactivation. Normaliser
   le téléphone via `services/phone.py` et horodater `whatsapp_opt_in_at` au
   moment où le consentement passe à vrai.
3. `api/v1/referees.py` — routes admin, toutes derrière `AdminUser`.
4. `api/v1/me.py` — `PATCH /me/profile` derrière `RefereeUser`, limité aux
   champs de `RefereeProfileUpdate`.
5. Tests : cas nominal, refus anonyme, refus arbitre sur une route admin,
   arbitre modifiant le profil d'un autre, téléphone invalide, e-mail en double.
6. Frontend : liste des arbitres (TanStack Query + `Page<T>`), formulaire
   d'invitation, page profil en écriture.

`RefereeRepository.search_statement` / `search_page` sont déjà en place pour la
liste filtrée et paginée.
