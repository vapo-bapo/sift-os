# Operazioni

Controlli rapidi:

- `/health`: processo vivo;
- `/ready`: dipendenze pronte;
- dashboard prodotti: run riusciti/falliti e costi;
- audit: modifiche amministrative e risultati;
- log Railway: cercare il request ID restituito al client.

Per un errore SSO verificare, nell'ordine: entitlement Platform, mapping
`platform_user_id`, issuer/audience, raggiungibilità JWKS e orologio dei servizi. Per
eventi mancanti verificare stato della credenziale, prodotto associato e
`external_event_id`. Non correggere dati di produzione manualmente: usare migration
o una procedura applicativa auditabile.

Backup e restore PostgreSQL devono essere provati periodicamente in staging. Le
credenziali vanno ruotate dopo qualsiasi sospetta esposizione.
