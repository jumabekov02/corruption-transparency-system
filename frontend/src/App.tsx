import { useEffect, useState } from "react";

// Vite exposes env vars prefixed with VITE_ via import.meta.env.
const API = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function App() {
  // "state" = a value React re-renders when it changes.
  const [status, setStatus] = useState<string>("checking…");

  // Runs once after the page first renders: call the backend and show the result.
  useEffect(() => {
    fetch(`${API}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <main className="page">
      <h1>Public Procurement Risk Monitoring</h1>
      <p>Frontend skeleton is running.</p>
      <p>
        Backend health: <strong>{status}</strong>
      </p>
    </main>
  );
}
