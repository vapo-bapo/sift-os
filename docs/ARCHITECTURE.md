# Architettura

SIFT Platform resta il sistema di identità e autorizzazione all'ingresso. SIFT OS è
un'applicazione separata composta da una SPA React, un'API FastAPI e PostgreSQL.

```text
Browser -> SIFT Platform -> ticket SSO monouso -> SIFT OS Web
Browser -> /api/* -> SIFT OS API -> PostgreSQL
Argus/Lynx -> /api/integrations/events -> SIFT OS API
```

Il web e l'API sono pubblicati come servizi Railway distinti. Nginx serve la SPA e
inoltra `/api` al nome DNS privato dell'API. I moduli backend sono `auth`, `staff`,
`crm`, `partners`, `products`, `integrations`, `company`, `finance`, `dashboard`,
`search`, `admin` e `audit`. La business logic resta nei service; le route validano
input, autenticazione e permessi.

PostgreSQL è l'unica fonte dei dati operativi. Il frontend non contiene mock di
produzione e usa React Query per lo stato remoto.
