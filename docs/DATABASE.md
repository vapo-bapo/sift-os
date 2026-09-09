# Database

Il database PostgreSQL è gestito esclusivamente con Alembic. Le tabelle coprono:

- staff, ruoli, sessioni e audit;
- account, contatti, opportunità, cronologia stage e attività CRM;
- partner, accordi e clienti attribuiti;
- prodotti, credenziali di servizio, run ed eventi;
- obiettivi, task e notifiche;
- movimenti e snapshot finanziari.

Gli identificatori sono UUID. Gli importi monetari sono interi in centesimi. Le date
di evento sono timezone-aware e normalizzate in UTC. La cancellazione operativa usa
`archived_at`; i vincoli di unicità e le foreign key proteggono coerenza e
idempotenza.

```bash
alembic -c apps/api/alembic.ini upgrade head
alembic -c apps/api/alembic.ini check
```

Non usare `create_all()` per aggiornare ambienti condivisi.
