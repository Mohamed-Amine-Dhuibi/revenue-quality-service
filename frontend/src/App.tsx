import { useState } from "react";
import { analyse } from "./api";
import type { AnalyseResponse } from "./types";
import UploadForm, { type SubmitArgs } from "./components/UploadForm";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [data, setData] = useState<AnalyseResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(args: SubmitArgs) {
    setLoading(true);
    setError(null);
    try {
      setData(await analyse(args));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      {data ? (
        <Dashboard data={data} onReset={() => setData(null)} />
      ) : (
        <>
          <div className="topbar">
            <div className="brand">
              <div className="logo">RQ</div>
              <div>
                <h1>Revenue Quality Scoring</h1>
                <p>Bank-statement revenue trustworthiness for SME lending</p>
              </div>
            </div>
          </div>
          <UploadForm onSubmit={handleSubmit} loading={loading} error={error} />
        </>
      )}
    </div>
  );
}
