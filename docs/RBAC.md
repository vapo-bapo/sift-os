# RBAC

I permessi sono calcolati sul backend dai ruoli associati al membro staff; il menu
frontend è solo una rappresentazione degli stessi permessi, non una barriera di
sicurezza.

| Ruolo | Ambito principale |
| --- | --- |
| CEO | accesso completo |
| Admin | accesso completo, staff, audit e credenziali |
| Sales lead | intero CRM, assegnazioni, partner, task e dashboard vendite |
| Sales | record CRM propri, partner assegnati e task propri |
| Coding | prodotti, dashboard aziendale, obiettivi e task |

Le route di scrittura richiedono anche un token CSRF. L'ownership viene applicata
nella query e ricontrollata prima di ogni modifica. Le azioni sensibili producono un
audit log con attore, entità, risultato e request ID.
