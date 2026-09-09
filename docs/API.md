# API

Tutte le route applicative hanno prefisso `/api`; `/health` e `/ready` sono endpoint
operativi. Gli errori hanno forma stabile con `error.code`, `error.message` e request
ID. Le liste restituiscono `items`, `total`, `page`, `page_size`.

Gruppi principali:

- autenticazione: `/api/auth/sso/exchange`, `/api/me`, `/api/logout`;
- CRM: `/api/accounts`, `/api/contacts`, `/api/opportunities`, `/api/activities`;
- partner: `/api/partners` e `/api/partners/{id}/clients`;
- prodotti: `/api/products` e metriche;
- eventi: `/api/integrations/events`;
- lavoro: `/api/objectives`, `/api/tasks`, `/api/notifications`;
- finanza: `/api/finance/entries`, `/api/finance/snapshots`, `/api/finance/metrics`;
- dashboard: `/api/dashboard`, `/sales`, `/products`, `/finance`;
- amministrazione: `/api/staff`, `/api/admin/audit`, credenziali prodotto;
- ricerca globale: `/api/search?q=...`.

Le richieste mutative della sessione browser richiedono `X-CSRF-Token`. Gli eventi
macchina usano `Authorization: Bearer <service-secret>`.
