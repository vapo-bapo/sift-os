# SIFT OS — Design di sistema

## Obiettivo e perimetro

SIFT OS è il sistema operativo interno di SIFT per otto membri iniziali. È il source of truth per staff, CRM, pipeline, partner, revenue share, telemetria prodotto aggregata, attività, obiettivi, notifiche e management accounting. SIFT Platform resta il source of truth esclusivo per identità, password, account cliente, workspace, licenze ed entitlement.

Il lavoro è diviso in incrementi verticali nell'ordine richiesto: foundation; autenticazione e RBAC; CRM; partner; Product Operations; Company; Finance; dashboard; hardening; staging e produzione. Ogni incremento comprende schema, API, UI, autorizzazioni, audit, test e documentazione necessari. Il CRM non viene aperto agli utenti prima che autenticazione e RBAC siano verificati.

## Evidenze della discovery

SIFT Platform usa:

- frontend React 19, TypeScript, Vite, React Router e TanStack Query;
- backend Python FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, psycopg e PostgreSQL;
- sessioni browser opache in cookie HttpOnly, con solo digest HMAC nel database;
- cookie CSRF e header `X-CSRF-Token` per le mutazioni;
- password Argon2id memorizzate esclusivamente nella Platform;
- ticket SSO monouso di 60 secondi, exchange server-side e assertion RS256 di 300 secondi;
- JWKS pubblico e claim di identità, workspace, prodotto ed entitlement;
- deploy Railway tramite Docker, migrazioni controllate e healthcheck;
- design language editoriale con palette crema/sabbia/inchiostro/oro, tipografia forte, bordi sottili, densità controllata e pochi elementi decorativi.

Il database production contiene nove utenti attivi. Gli otto mapping verificati sono:

- Alessandro Bellucco → `4ac5662a-1eaa-4f47-9dae-406eefdf6e40`;
- Braghin Gregorio → `a02ba528-67bf-405b-8d81-bafb3d5314f7`;
- Lorenzo Di Lenna → `0de642b4-8a97-422b-8aaa-e05d581e528a`;
- Dalsoglio Luca → `da0a87e1-ded0-449b-9988-6e4e8f825ed4`;
- Matteo Pinton → `2011db5d-7c26-4a1e-aa60-9007f9dc8a87`;
- Melchionda Federico → `8e195348-3a4a-479a-af5b-3cf4cc69ae3e`;
- Michael Nordin → `d13cd18f-bd38-4ebc-b379-4a8fc39408f0`;
- Alexis Solomon → `6cf7bdfc-c119-454b-ab3d-c448e56ed197`.

`Aliceg76` è stato confermato non-staff e non riceverà accesso. Nessun controllo userà dominio email, nome o altra euristica.

Il checkout locale di SIFT Platform, inclusi i due commit di correzione successivi a `origin/main`, è la base autorevole approvata.

## Architettura e confini

SIFT OS è un monorepo con due applicazioni distribuibili separatamente:

- `apps/api`: FastAPI modulare per auth, staff, CRM, partner, prodotti/eventi, Company, Finance, analytics, notifiche, admin e audit;
- `apps/web`: React/TypeScript/Vite con routing per ruolo, TanStack Query, React Hook Form, Zod e componenti visuali derivati dalla Platform.

PostgreSQL SIFT OS è separato dal database Platform. Non esistono foreign key cross-database né letture dirette del database Platform, Argus o Lynx. I confini sono:

- Platform → OS: SSO e, dove necessario, API/eventi per riferimenti cliente e licenza;
- Argus/Lynx → OS: endpoint eventi autenticato con credenziali distinte;
- browser → web → `/api/*` → API su rete privata Railway → PostgreSQL OS.

Il web pubblico mantiene browser e API same-origin. I moduli backend comunicano tramite servizi applicativi e transazioni esplicite; audit e notifiche reagiscono agli eventi di dominio senza creare dipendenze circolari.

## Autenticazione e sessioni

La Platform aggiunge `sift-os` al catalogo prodotti con launch URL configurabile. L'entitlement viene assegnato solo agli otto utenti interni. Il flusso è:

1. la Platform autentica l'utente e verifica stato, membership, entitlement e prodotto;
2. emette il ticket monouso già implementato;
3. SIFT OS scambia il ticket con la Platform;
4. verifica firma e claim RS256 (`iss`, `aud=sift-os`, `sub`, `exp`, `iat`, `jti`, prodotto ed entitlement) tramite JWKS;
5. cerca `sub` in `staff_members.platform_user_id` e richiede `active=true`;
6. crea una sessione OS opaca in cookie Secure, HttpOnly e SameSite=Lax, con CSRF per le mutazioni.

L'assertion Platform non viene salvata in `localStorage`. SIFT OS non riceve né conserva password o hash password. Logout OS revoca solo la sessione OS. Ticket riutilizzati, assertion invalide, utenti non mappati e staff disattivati sono rifiutati. La chiave pubblica Platform viene aggiornata tramite JWKS con cache breve e refresh su `kid` sconosciuto.

## RBAC e autorizzazione dati

Le autorizzazioni vengono applicate nelle dipendenze e nei servizi backend, mai soltanto nell'interfaccia. Il modello combina ruolo, permission esplicite, reparto, ownership e sensibilità del dato.

- `CEO`, `ADMIN`, `CODING` per Alessandro Bellucco: accesso completo e superadmin;
- `SALES_LEAD` per Lorenzo Di Lenna: controllo completo Sales e Partner, senza segreti tecnici o Finance riservata;
- `SALES` per Alexis Solomon, Braghin Gregorio e Melchionda Federico: record assegnati, flusso My Day e metriche non sensibili;
- `CODING` per Michael Nordin, Dalsoglio Luca e Matteo Pinton: Product Operations, task, obiettivi e metriche aggregate, senza PII commerciale non necessaria o Finance riservata.

`staff_members` contiene una riga unica per `platform_user_id`; ruoli multipli sono rappresentati con una relazione normalizzata e permission override limitate. Le query Sales applicano il filtro owner nel database. Il Sales Lead può riassegnare record del reparto; il Sales ordinario non può modificare record altrui. Finance richiede CEO/Admin. Ogni endpoint nega per default.

## Modello dati e regole

Lo schema usa UUID per chiavi esposte, timestamp UTC, denaro in integer cents e valuta ISO con default EUR. Le tabelle minime richieste sono implementate con foreign key, check constraint, unique constraint e indici per owner, stage, account, date, email, dominio, follow-up, identificativi esterni ed eventi.

I principali aggregati sono:

- CRM: account, contatti, opportunità, attività e stage history append-only;
- Partner: partner, agreement versionati, clienti attribuiti e commissioni;
- Product Operations: prodotti, run, eventi grezzi idempotenti e credenziali servizio;
- Company: obiettivi, task e notifiche;
- Finance: entries, snapshot e attribuzioni a cliente, partner e prodotto;
- Governance: staff, permission, configurazioni e audit append-only.

La normalizzazione dei domini rimuove protocollo, `www`, slash finali e differenze di maiuscole. Le email vengono normalizzate in lowercase. Il sistema segnala i duplicati e richiede una decisione esplicita; non fonde o cancella automaticamente.

Ogni transizione opportunity crea una riga in `opportunity_stage_history` nella stessa transazione. `STALE` è uno stato calcolato/configurabile e non cambia lo stage. Il revenue share appartiene all'agreement effettivo e deve sommare al 100%; il default 80/20 è configurazione, non costante distribuita. La regola iniziale di attivazione partner è la creazione del primo cliente attribuito; resta configurabile e una eventuale attivazione manuale richiede audit. Le metriche derivano da eventi e history, non da contatori statici non ricostruibili.

## API e flussi applicativi

Le API vivono sotto `/api`, con envelope di errore stabile, pagination cursor/offset coerente, filtri server-side e ordinamento allowlisted. Gli endpoint della specifica sono organizzati per router e servizi; nessun `main.py` monolitico.

I flussi prioritari sono:

- My Day: follow-up odierni/scaduti, nuovi lead, meeting e attività recenti, con completamento attività e creazione atomica del prossimo follow-up;
- Pipeline: vista kanban e tabella sulla stessa query canonica, stage mutation dedicata e history;
- CSV: upload temporaneo, preview, mapping, validazione, duplicate warning e commit esplicito in batch;
- Partner: firma, onboarding, attivazione e primo cliente come date distinte;
- Event ingestion: autenticazione servizio, validazione versionata, insert idempotente per `event_id`, aggiornamento run e metriche nella stessa transazione;
- Finance: entries e snapshot auditati, KPI calcolati con intervalli temporali espliciti;
- Search: endpoint globale limitato dalle stesse policy di visibilità delle risorse sorgenti.

Le credenziali Argus e Lynx sono indipendenti. Il segreto viene mostrato una sola volta; il database conserva un digest resistente e metadati di rotazione/revoca. Secret, ticket e token non entrano nei log.

## Frontend e UX

Il frontend riusa token, logo, palette, tipografia, spacing e tono visivo della Platform, adattandoli a un prodotto operativo più denso. La navigazione è role-aware: Dashboard, Sales, Partners, Product Operations, Company, Finance e Admin compaiono solo quando pertinenti.

La prima viewport è specifica per ruolo: cockpit CEO, My Day per Sales, Sales Dashboard per Sales Lead e Product Operations per Coding. Tabelle e kanban condividono filtri persistenti nell'URL. Azioni frequenti sono keyboard-friendly e riducono i passaggi: apri lead, registra esito, crea follow-up, passa al successivo. Desktop è prioritario; My Day e attività restano pienamente usabili su smartphone.

Ogni pagina gestisce in modo esplicito loading, vuoto, unauthorized, forbidden, errore di validazione, errore server e rete. Le mutazioni ottimistiche sono usate solo quando è sicuro ripristinare lo stato; le transizioni critiche attendono conferma server.

## Sicurezza, audit e osservabilità

CORS production usa origin esatte; il percorso normale è same-origin. Cookie, CSRF, scadenza sessione e rate limiting proteggono auth, exchange, import ed event ingestion. Input, filtri e ordinamenti sono allowlisted. Nessun hard delete business è esposto nella UI: si usano `archived_at` e `archived_by`.

Audit append-only obbligatorio per ruoli, ownership, stage rilevanti, agreement, revenue share, Finance, archiviazioni, credenziali e admin. I log strutturati includono request ID, route, status, durata, environment e identificativo utente quando appropriato, senza PII o segreti non necessari.

Healthcheck liveness e readiness sono separati. La readiness verifica il database e le dipendenze indispensabili, ma non rende l'app indisponibile per integrazioni opzionali. Alert in-app coprono scadenze, stale deal, assegnazioni, lifecycle partner, task e degrado prodotto.

## Test e criteri di accettazione

Il backend usa pytest con PostgreSQL isolato per test di integrazione. Il frontend usa Vitest e Testing Library. Playwright copre i cinque percorsi obbligatori: CEO, Sales Lead, Sales, Coding e Customer escluso. I test includono auth/SSO, RBAC e ownership, stage history, revenue share, Finance, idempotenza eventi, credenziali revocate, CSRF, migration upgrade e assenza di accesso diretto per clienti.

La CI esegue lint, format check, typecheck, test, migration sanity, build frontend e build Docker. Nessun test usa production. La Definition of Done richiede risultati reali: funzionalità non eseguite o non verificabili per mancanza di credenziali vengono dichiarate come limitazioni, non come completate.

## Deploy Railway

Il progetto Railway dedicato `SIFT OS Production` contiene `sift-os-web`, `sift-os-api` e PostgreSQL privato. Staging usa ambiente e database separati. Il web è l'unico servizio browser-facing e inoltra `/api` all'API privata; l'endpoint eventi passa dallo stesso dominio pubblico ed è protetto da credenziali servizio.

Dockerfile deterministici costruiscono web e API separatamente. Alembic viene eseguito in un pre-deploy controllato; l'applicazione non usa `create_all()` in produzione. Il dominio resta configurato tramite `SIFT_OS_PUBLIC_URL` finché non viene verificato e autorizzato un dominio reale. DNS non viene modificato automaticamente.

Il rilascio segue test → build → staging → smoke test → produzione. Il rollback del codice ridistribuisce l'ultima immagine valida; una migration viene retrocessa solo dopo prova su copia del database e valutazione della perdita dati.

## Modifiche minime a SIFT Platform

La Platform riceve soltanto le modifiche necessarie:

- nuova configurazione `SIFT_OS_LAUNCH_URL`;
- prodotto `sift-os` nel catalogo, con stile coerente;
- entitlement esclusivo agli otto UUID verificati;
- test che il prodotto non sia visibile al non-staff e che launch/exchange abbiano audience corretta.

Il protocollo SSO, le password, le sessioni e il database utenti non vengono riprogettati. Se serve distinguere prodotti interni, il catalogo riceve un attributo esplicito e il backend filtra la visibilità; non si usa una regola frontend o basata sull'email.

## Sequenza di consegna

1. Foundation monorepo, PostgreSQL, migrazioni, Docker, CI e documentazione iniziale.
2. Integrazione Platform, SSO receiver, sessioni OS, seed staff e RBAC.
3. CRM completo e flusso My Day.
4. Partner, agreement, clienti e revenue share.
5. Event ingestion, credenziali e Product Operations.
6. Objectives, task e notifiche.
7. Finance e KPI.
8. Dashboard role-specific e analytics ricostruibili.
9. Hardening, performance, responsive, audit ed E2E.
10. Staging, smoke test, configurazione produzione e handoff finale.

Ogni fase lascia mainline buildabile e testata. I commit restano piccoli e logici, e le modifiche Platform vengono mantenute in un branch separato dall'implementazione SIFT OS.
