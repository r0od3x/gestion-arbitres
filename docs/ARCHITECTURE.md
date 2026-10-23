# Architecture — état d'avancement et décisions

Complète `PROJECT_SPEC.md` : ce document enregistre **ce qui est construit** et
**les décisions prises en cours de route**, avec leurs raisons.

Dernière mise à jour : 23 octobre 2026 (jalon M3 terminé).

---

## 1. Avancement par jalon

| Jalon | État | Détail |
|-------|------|--------|
| **M1 — Fondations** | ✅ terminé | Squelette, config, Alembic, santé, auth, rôles, amorçage, tests |
| **M2 — Arbitres** | ✅ terminé | Invitation, liste/filtres, édition, désactivation, consentement WhatsApp |
| **M3 — Tournois & désignations** | ✅ terminé | CRUD, transitions de statut, sélection des arbitres, confirmer/décliner |
| **M4 — Notifications WhatsApp** | 🟡 socle prêt | Interface fournisseur, provider Cloud API, worker et suivi de livraison faits ; reste l'endpoint `convocations/send` et le webhook HTTP |
| **M5 — Finitions** | ⬜ à faire | Boutons de réponse WhatsApp, rappels, journal d'audit, export CSV |

### Ce qui fonctionne aujourd'hui

**Authentification** — `POST /auth/login` · `/refresh` · `/logout` ·
`/accept-invite` · `GET /auth/me`, plus `GET /healthz` · `/readyz`.

**Arbitres (administrateur)** — `GET /referees` (filtres grade, ville, statut,
recherche texte, pagination), `POST /referees/invite`, `GET` et `PATCH
/referees/{id}`, `POST /referees/{id}/deactivate` · `/activate` ·
`/invite/resend`.

**Arbitres (soi-même)** — `GET /me`, `GET` et `PATCH /me/profile`.

**Tournois** — `GET /tournaments` (filtres statut, ville, période, recherche ;
un arbitre ne voit jamais les brouillons), `POST /tournaments`, `GET` et `PATCH
/tournaments/{id}`, `POST /tournaments/{id}/publish` · `/cancel` · `/complete`.

**Désignations** — `GET` et `PUT /tournaments/{id}/assignments` (mise à jour
différentielle), `GET /me/assignments`, `POST /me/assignments/{id}/confirm` ·
`/decline`.

**Hors HTTP** — les cinq tables via une migration Alembic ; worker ARQ et envoi
de notifications avec relances.

**SPA React** — connexion, activation de compte par lien d'invitation, gardes
de route par rôle, liste des arbitres filtrable et paginée, formulaire
d'invitation avec lien à transmettre, profil arbitre modifiable avec
consentement WhatsApp, liste des tournois avec transitions de statut, fiche
tournoi et sélecteur d'arbitres, « mes convocations » avec confirmer/décliner.

Parcours vérifié de bout en bout sur un serveur réel : l'administrateur invite
un arbitre (téléphone normalisé en E.164) → l'arbitre active son compte via le
lien → il complète son profil et donne son consentement WhatsApp → ses
tentatives de changer son grade (422) et d'accéder aux routes admin (403) sont
refusées → l'administrateur le désactive → il ne peut plus se connecter (401).

**Qualité** : 138 tests backend, 58 tests frontend, `ruff` et `mypy --strict`
sans erreur, `eslint` et `prettier` sans erreur, `alembic check` sans dérive.

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

### 2.14 Le consentement WhatsApp n'est jamais donné par un administrateur

`RefereeInviteRequest` ne contient pas `whatsapp_opt_in` : un arbitre invité
démarre toujours à `false`. Seul l'arbitre peut le passer à `true`, depuis son
profil, et `whatsapp_opt_in_at` est horodaté à cet instant (effacé au retrait).

*Pourquoi* : le consentement doit venir de la personne concernée (loi 09-08 /
CNDP). Un administrateur qui cocherait la case à sa place rendrait la preuve de
consentement sans valeur. `RefereeAdminUpdate` accepte `whatsapp_opt_in`
uniquement pour permettre un **retrait** à la demande de l'arbitre.

### 2.15 Deux schémas de mise à jour distincts, pas un seul filtré

`RefereeAdminUpdate` et `RefereeProfileUpdate` sont deux schémas séparés, tous
deux en `extra="forbid"`.

*Pourquoi* : le second ne contient ni `grade`, ni `license_number`, ni
`notes_admin`. Un arbitre qui tente de se promouvoir reçoit un 422 explicite
plutôt qu'un succès où le champ aurait été silencieusement ignoré. L'écart de
privilèges est visible dans le type, pas enfoui dans une liste de champs
autorisés.

### 2.16 Aucune route « soi-même » ne prend d'identifiant

Les routes de `api/v1/me.py` résolvent le profil depuis le jeton via
`RefereeUser`.

*Pourquoi* : sans identifiant dans l'URL, il n'existe aucun chemin de code par
lequel un arbitre pourrait lire ou modifier le profil d'un autre. La protection
est structurelle, pas une vérification qu'on pourrait oublier.

### 2.17 Désactivation plutôt que suppression

`POST /referees/{id}/deactivate` bascule `users.is_active`; aucune route ne
supprime d'arbitre.

*Pourquoi* : les convocations passées référencent l'arbitre. Supprimer la ligne
détruirait l'historique ou casserait les clés étrangères. Un compte désactivé ne
peut plus se connecter et les jetons existants sont rejetés au coup suivant.

### 2.18 Le lien d'invitation est retourné à l'administrateur

`POST /referees/invite` répond avec `invite_url`, que l'interface affiche et
permet de copier.

*Pourquoi* : l'envoi d'e-mails n'est pas encore en place, et attendre cette
brique bloquerait tout le parcours d'intégration. L'administrateur transmet le
lien par le canal de son choix. **Limite connue** : le lien circule hors du
système, donc sans traçabilité. À remplacer par un envoi automatique en phase 2.

### 2.19bis Les changements de session passent tous par `AuthProvider`

`adoptSession(accessToken)` est le seul moyen d'ouvrir une session autrement
qu'avec un mot de passe. La page d'activation d'invitation l'appelle au lieu de
poser le jeton directement sur le client HTTP.

*Pourquoi* : trouvé en pilotant l'application dans un vrai navigateur. La page
d'activation posait le jeton sur le client HTTP sans prévenir l'état React.
Sur un navigateur où un administrateur était déjà connecté, l'arbitre qui
activait son compte atterrissait **dans la session de l'administrateur** : les
gardes de route lisaient l'utilisateur périmé. `adoptSession` vide le cache de
requêtes, pose le jeton, recharge `/auth/me` et met l'état à jour — dans cet
ordre. Couvert par un test de non-régression.

### 2.19 Le format du téléphone est validé côté serveur uniquement

Les formulaires laissent passer la saisie libre ; `services/phone.py` normalise
en E.164 et le message d'erreur du serveur est affiché tel quel.

*Pourquoi* : la validité d'un numéro dépend de la région (`DEFAULT_PHONE_REGION`)
et de la base de `phonenumbers`. Dupliquer cette logique en TypeScript
produirait deux vérités qui divergeraient. Le client valide ce qui est
universel (champ requis, format d'e-mail) et délègue le reste.

---

### 2.20 La machine à états est déclarée, pas dispersée

`TOURNAMENT_TRANSITIONS` (dans `models/enums.py`) énumère les transitions
autorisées ; `TournamentService.change_status` la consulte au lieu d'enchaîner
des `if`.

*Pourquoi* : les règles tiennent en quatre lignes lisibles d'un coup d'œil, et
le frontend dérive de la même table les boutons qu'il affiche. Ajouter un
statut se fait à un seul endroit.

### 2.21 Les désignations sont mises à jour en différentiel

`PUT /tournaments/{id}/assignments` reçoit la **liste cible complète** des
arbitres, puis ajoute les manquants, annule les retirés et ne touche pas aux
autres. La réponse indique `{added, cancelled, unchanged}`.

*Pourquoi* : un remplacement (tout supprimer, tout recréer) détruirait les
réponses déjà données par les arbitres et l'historique de leurs notifications à
chaque enregistrement. Le différentiel conserve l'identité des lignes
inchangées, donc leur `status`, leur `responded_at` et leurs notifications.
Vérifié dans un vrai navigateur : un arbitre confirme, l'administrateur retire
*un autre* arbitre et enregistre, la confirmation survit.

### 2.22 Une désignation annulée est conservée, pas supprimée

Retirer un arbitre passe sa désignation à `cancelled` ; la ligne reste en base
et les listes l'excluent par défaut (`include_cancelled=false`).

*Pourquoi* : la contrainte `UNIQUE (tournament_id, referee_id)` interdit de
recréer une ligne identique, et l'historique « a été convoqué puis retiré » a
une valeur en cas de litige. Re-convoquer un arbitre annulé remet sa
désignation à `pending` et efface sa réponse précédente : c'est une nouvelle
convocation, il doit répondre à nouveau.

### 2.23 Un brouillon renvoie 404 à un arbitre, pas 403

`get_visible_for_referee` traite les tournois non publiés comme inexistants.

*Pourquoi* : un 403 confirmerait qu'un tournoi existe à cet identifiant. Tant
qu'il n'est pas publié, il ne doit rien révéler.

### 2.24 Les compteurs d'effectif sont calculés en une requête

`TournamentRepository.assignment_counts` agrège désignés et confirmés pour
toute la page d'un coup.

*Pourquoi* : afficher « 2/4 désignés, 1 confirmé » par ligne sans cela voudrait
dire une requête par tournoi (N+1). Les désignations annulées sont exclues du
compte : elles ne représentent pas un effectif.

### 2.25 La sélection d'arbitres est dérivée, jamais recopiée

`RefereePicker` garde un brouillon `null` tant que l'utilisateur n'a rien
coché ; l'affichage suit alors le serveur. Au premier clic, le brouillon prend
le relais ; après un enregistrement réussi, il repasse à `null`.

*Pourquoi* : la version initiale synchronisait l'état serveur dans un
`useState` via un `useEffect`, ce qu'ESLint signale à juste titre. Une valeur
dérivée ne peut pas se désynchroniser de sa source, et la liste se rafraîchit
toute seule après enregistrement.

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

## 4. Prochaine étape — M4 (notifications WhatsApp)

Le socle est déjà en place (voir 2.4) : interface fournisseur, provider Cloud
API, worker ARQ, relances et suivi de livraison, tous testés. Il reste à les
brancher sur HTTP :

1. `services/convocations.py` — pour chaque désignation `pending` d'un tournoi
   **publié** sans notification `convocation` déjà envoyée : créer une ligne
   `notifications` (`queued`) et enfiler un job. Les arbitres dont
   `is_notifiable` est faux reçoivent directement une notification `failed`
   avec un motif clair, déjà exposé dans la liste des désignations.
2. `POST /tournaments/{id}/convocations/send` et
   `POST /assignments/{id}/notifications/resend` (admin).
3. `api/v1/webhooks.py` — `GET /webhooks/whatsapp` (défi de vérification avec
   `WHATSAPP_VERIFY_TOKEN`) et `POST` (signature `X-Hub-Signature-256` vérifiée
   par `verify_webhook_signature`, puis `apply_provider_status`). Le webhook
   doit répondre 200 même sur un message inconnu, sinon Meta réessaie en boucle.
4. Créer le template `convocation_tournoi` côté Meta (voir
   `PROJECT_SPEC.md` §6) ; en développement, garder `NOTIFICATION_PROVIDER=console`.
5. Tests : idempotence (deux envois ne produisent pas deux messages), arbitre
   sans consentement marqué `failed`, webhook à signature invalide rejeté (403),
   webhook dans le désordre ignoré (déjà couvert côté service).
6. Frontend : colonne « statut de notification » dans la fiche tournoi, bouton
   « Envoyer les convocations » et relance individuelle.

`AssignmentWithReferee` porte déjà `notification_status`, `notification_error`
et `is_notifiable` : l'interface n'aura pas besoin d'un nouvel appel.
