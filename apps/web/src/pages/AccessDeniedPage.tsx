import { Brand } from "../components/Brand";
import { useAuth } from "../features/auth/AuthProvider";

export function AccessDeniedPage() {
  const { status, error } = useAuth();
  const isForbidden = status === "forbidden";

  return (
    <main className="message-page">
      <Brand />
      <section className="message-card" aria-labelledby="access-title">
        <p className="eyebrow">SIFT OS</p>
        <h1 id="access-title">{isForbidden ? "Access denied" : "Sign-in required"}</h1>
        <p>{isForbidden ? "Your staff account is not currently allowed to use this workspace." : "Open SIFT OS from the SIFT Platform to establish a secure staff session."}</p>
        {error && !isForbidden ? <p className="inline-error" role="alert">We could not verify your session. Please try again from SIFT Platform.</p> : null}
      </section>
    </main>
  );
}
