# Eventi prodotto

Argus e Lynx inviano eventi a `POST /api/integrations/events` con una credenziale
dedicata al prodotto. La secret è mostrata solo alla creazione; nel database viene
conservato esclusivamente l'hash. Le credenziali possono essere ruotate o revocate.

Ogni evento include un `external_event_id`, tipo, timestamp, stato, costo opzionale
e metadati non sensibili. La coppia prodotto/evento esterno è univoca: una consegna
ripetuta restituisce il risultato già registrato senza duplicare run o costi.

Esempio:

```json
{
  "external_event_id": "argus-run-42-completed",
  "event_type": "run.completed",
  "occurred_at": "2026-09-09T08:00:00Z",
  "run_external_id": "argus-run-42",
  "status": "completed",
  "cost_cents": 18,
  "metadata": {"source": "argus"}
}
```

Non inserire prompt, token, PII o secret nei metadati.
