# Autenticazione

1. L'utente accede a SIFT Platform.
2. Platform verifica un entitlement attivo per il prodotto interno `sift-os`.
3. Platform emette un ticket monouso e reindirizza al callback SIFT OS.
4. Il browser invia il ticket a `POST /api/auth/sso/exchange`.
5. L'API scambia il ticket server-to-server, valida firma JWKS, issuer, audience,
   scadenza e identità, quindi cerca `platform_user_id` nella allowlist staff.
6. L'API crea una sessione locale con cookie `Secure`, `HttpOnly`, `SameSite=Lax`
   e un cookie CSRF separato.

Un cliente senza entitlement, un utente non presente/attivo nello staff o un ticket
revocato non ottengono una sessione. I ticket non sono memorizzati nel browser oltre
lo scambio. Il logout revoca la sessione e cancella entrambi i cookie.
