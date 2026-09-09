# Sicurezza

- Autenticazione demandata a SIFT Platform con ticket monouso e JWT firmato.
- Allowlist staff e RBAC applicati server-side.
- Cookie di sessione HttpOnly/Secure in staging e produzione.
- Protezione CSRF sulle mutazioni browser.
- CORS con origin esatti, senza wildcard in produzione.
- Secret di servizio hashate, revocabili e mai incluse nei log.
- Query parametrizzate tramite SQLAlchemy e validazione Pydantic.
- Audit log per accessi e modifiche sensibili.
- Nessun secret committato; configurazione tramite variabili Railway.

Segnalare vulnerabilità privatamente al responsabile tecnico SIFT includendo impatto,
passi di riproduzione e request ID. Non usare dati reali dei clienti in test o
staging.
