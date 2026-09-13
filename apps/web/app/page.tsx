"use client";

import { useEffect, useState } from "react";
import styles from "./page.module.css";

type HealthState = {
  status: string | null;
  json: Record<string, unknown> | null;
  loaded: boolean;
  error: string | null;
  at: string | null;
};

const MAX_ATTEMPTS = 2;
const RETRY_DELAY_MS = 800;

export default function HealthPage() {
  const [state, setState] = useState<HealthState>({
    status: null,
    json: null,
    loaded: false,
    error: null,
    at: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function checkHealth(): Promise<void> {
      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
        if (cancelled) return;
        try {
          const res = await fetch("/api/health");
          if (!res.ok) {
            throw new Error(`HTTP ${res.status} ${res.statusText}`);
          }
          const json: Record<string, unknown> = await res.json();
          if (cancelled) return;
          setState({
            status: typeof json.status === "string" ? json.status : "unknown",
            json,
            loaded: true,
            error: null,
            at: new Date().toISOString(),
          });
          return;
        } catch (err) {
          if (cancelled) return;
          const message = err instanceof Error ? err.message : String(err);
          if (attempt >= MAX_ATTEMPTS) {
            setState({
              status: null,
              json: null,
              loaded: true,
              error: message,
              at: new Date().toISOString(),
            });
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
        }
      }
    }

    void checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const healthy = state.loaded && state.error === null && state.status === "ok";

  return (
    <main className={styles.main}>
      <h1 className={styles.heading}>System Health — Phase 0</h1>
      <section className={styles.card}>
        <dl>
          <div className={styles.row}>
            <dt>Backend status</dt>
            <dd>{state.loaded && state.error === null ? state.status : "—"}</dd>
          </div>
          <div className={styles.row}>
            <dt>Fetch succeeded</dt>
            <dd>{state.loaded ? (state.error === null ? "yes" : "no") : "pending"}</dd>
          </div>
          <div className={styles.row}>
            <dt>Timestamp</dt>
            <dd>{state.at ?? "—"}</dd>
          </div>
        </dl>
        <p className={!state.loaded ? styles.checking : healthy ? styles.ok : styles.failed}>
          PHASE 0 HEALTH PATH: {!state.loaded ? "CHECKING" : healthy ? "OK" : "FAILED"}
        </p>
        {state.error !== null && <p className={styles.error}>Error: {state.error}</p>}
        <pre className={styles.code}>
          <code>{state.loaded ? JSON.stringify(state.json, null, 2) : "awaiting /api/health response…"}</code>
        </pre>
      </section>
    </main>
  );
}