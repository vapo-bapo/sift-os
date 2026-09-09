# SIFT OS

Sistema operativo interno SIFT per CRM, vendite, partner, operazioni prodotto,
obiettivi, task, finanza e dashboard direzionale. L'accesso avviene esclusivamente
tramite SIFT Platform e viene autorizzato dal backend.

## Avvio locale

Requisiti: Docker Desktop, oppure Python 3.12 + PostgreSQL 17 + Node.js 22.

```bash
git clone https://github.com/vapo-bapo/sift-os.git
cd sift-os
cp .env.example .env
docker compose up --build
```

L'app è disponibile su `http://localhost:5173`; l'API diretta su
`http://localhost:8001`. Per completare il login locale, SIFT Platform deve essere
raggiungibile su `http://localhost:8000` e deve avere il prodotto interno `sift-os`
abilitato per l'utente.

## Avvio senza Docker

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
npm ci
alembic -c apps/api/alembic.ini upgrade head
python -m app.db.cli seed-all
uvicorn app.main:app --reload --port 8001
```

In un secondo terminale:

```bash
npm run dev --workspace apps/web
```

## Verifiche

```bash
ruff format --check apps/api
ruff check apps/api
mypy apps/api/app
pytest -q
npm run typecheck --workspace apps/web
npm run lint --workspace apps/web
npm run test --workspace apps/web -- --run
npm run build --workspace apps/web
```

Le migrazioni si controllano con:

```bash
alembic -c apps/api/alembic.ini upgrade head
alembic -c apps/api/alembic.ini check
```

## Configurazione

Tutte le variabili supportate sono elencate in `.env.example`. Non inserire mai
secret nel repository. In produzione il browser usa un solo origin: il servizio web
inoltra `/api/*` all'API tramite la rete privata Railway.

## Documentazione

- [Architettura](docs/ARCHITECTURE.md)
- [Autenticazione](docs/AUTH_ARCHITECTURE.md)
- [RBAC](docs/RBAC.md)
- [Database](docs/DATABASE.md)
- [API](docs/API.md)
- [Eventi prodotto](docs/PRODUCT_EVENTS.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Operazioni](docs/OPERATIONS.md)
- [Sicurezza](docs/SECURITY.md)
