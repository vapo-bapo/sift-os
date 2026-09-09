# Deployment Railway

## Repository e servizi

- repository: `vapo-bapo/sift-os`;
- branch di rilascio attuale: `codex/sift-os-initial`;
- progetto Railway: `sift-platform` (`d1123efe-12c0-4e73-ae52-a7e12103a18f`);
- web: `sift-os-web` (`2fdcd65f-ea22-4fbd-af5e-8d9b6c53231b`);
- API: `sift-os-api` (`a9bb8fd7-8bff-4d63-a892-c37be41a1586`);
- PostgreSQL: servizio condiviso, database logico separato `sift_os`.

Il deployment attuale usa l'ambiente `production` del progetto esistente. La
specifica richiede anche `staging`: deve essere creato clonando i servizi ma usando
un database separato prima di abilitare promozioni automatiche.

## Build e avvio

| Servizio | Dockerfile | Avvio | Healthcheck |
| --- | --- | --- | --- |
| `sift-os-web` | `Dockerfile.web` | entrypoint Nginx | `/ready` tramite proxy |
| `sift-os-api` | `Dockerfile.api` | migration, seed idempotente, Uvicorn | `/ready` |

Entrambi ascoltano `PORT`. Il web usa `SIFT_OS_API_ORIGIN` per inoltrare `/api`,
`/health` e `/ready` al nome DNS privato dell'API. Il browser vede un solo origin.

## Variabili

API:

- `APP_ENV=production` oppure `staging`;
- `DATABASE_URL` (URL PostgreSQL privato, database dell'ambiente);
- `SIFT_OS_PUBLIC_URL`;
- `SIFT_PLATFORM_PUBLIC_URL`;
- `SIFT_PLATFORM_SSO_ISSUER`;
- `SIFT_PLATFORM_SSO_AUDIENCE=sift-os`;
- `SIFT_PLATFORM_JWKS_URL`;
- `SESSION_SECRET`, `CSRF_SECRET`;
- `COOKIE_DOMAIN` se viene adottato un dominio condiviso;
- `CORS_ALLOWED_ORIGINS` con origin esatti;
- `LOG_LEVEL`.

Web:

- `SIFT_OS_API_ORIGIN=http://sift-os-api.railway.internal:<porta>`;
- `PORT` fornito da Railway.

Platform:

- `SIFT_OS_LAUNCH_URL=https://<host-web>/auth/callback`.

## Procedura di rilascio

1. Eseguire CI completa.
2. Distribuire lo stesso commit in staging.
3. Applicare le migration al database staging e svolgere smoke test SSO, CRM,
   partner, eventi, task e finanza.
4. Promuovere il commit in produzione.
5. L'API esegue `alembic upgrade head` prima dell'avvio e poi seed idempotenti.
6. Verificare `/health`, `/ready`, scambio SSO e `/api/me`.

## Rollback

Ripristinare su Railway l'immagine dell'ultimo commit valido. Non fare downgrade
automatico dello schema: le migration devono restare backward-compatible per il
rilascio precedente. Per una migration distruttiva preparare prima una migration di
ripristino e un backup verificato. In caso di problema dati, isolare le scritture,
ripristinare il backup in una nuova istanza e confrontare prima dello switch.

## Dominio

L'URL Railway corrente è
`https://sift-os-web-production.up.railway.app`. Un custom domain può sostituirlo
solo dopo configurazione DNS esplicita; aggiornare insieme URL Platform, issuer,
CORS e cookie. Non inventare o cambiare DNS durante il deploy applicativo.
