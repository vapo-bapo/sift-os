import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { queryClient } from "../app/queryClient";
import { exchangeSso } from "../features/auth/api";

type CallbackState = "exchanging" | "invalid" | "failed";

export function SsoCallbackPage() {
  const navigate = useNavigate();
  const [state, setState] = useState<CallbackState>("exchanging");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ticket = params.get("sso_ticket");
    const audience = params.get("sso_audience");
    window.history.replaceState(window.history.state, "", window.location.pathname);

    if (!ticket || audience !== "sift-os") {
      setState("invalid");
      return;
    }

    void exchangeSso(ticket)
      .then(() => queryClient.invalidateQueries({ queryKey: ["auth", "me"] }))
      .then(() => navigate("/", { replace: true }))
      .catch(() => setState("failed"));
  }, [navigate]);

  if (state === "invalid") {
    return <main className="status-page"><section><h1>Callback not accepted</h1><p>This sign-in callback is not intended for SIFT OS.</p></section></main>;
  }
  if (state === "failed") {
    return <main className="status-page"><section><h1>Could not sign you in</h1><p>Return to SIFT Platform and start again.</p><a className="button primary" href="https://sift-platform-production.up.railway.app">Open SIFT Platform</a></section></main>;
  }
  return <main className="status-page" aria-live="polite"><p>Securing your SIFT OS session…</p></main>;
}
