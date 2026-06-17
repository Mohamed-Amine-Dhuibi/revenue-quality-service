import { useRef, useState } from "react";
import { DEFAULT_API_BASE } from "../api";

export interface SubmitArgs {
  apiBase: string;
  apiKey: string;
  file: File;
  borrowerName: string;
}

interface Props {
  onSubmit: (args: SubmitArgs) => void;
  loading: boolean;
  error: string | null;
}

export default function UploadForm({ onSubmit, loading, error }: Props) {
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE);
  const [apiKey, setApiKey] = useState(
    localStorage.getItem("rqs_api_key") ?? "dev-local-key-change-me",
  );
  const [borrowerName, setBorrowerName] = useState("Hawk Tech Services LLC");
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function submit() {
    if (!file) return;
    localStorage.setItem("rqs_api_key", apiKey);
    onSubmit({ apiBase, apiKey, file, borrowerName });
  }

  return (
    <div className="upload-wrap">
      <div className="card">
        <h2>Analyse a bank statement</h2>
        <div className="sub">
          Upload a transactions CSV to score revenue quality and surface
          manipulation patterns.
        </div>

        {error && <div className="error">{error}</div>}

        <div
          className={`dropzone ${drag ? "drag" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            const f = e.dataTransfer.files?.[0];
            if (f) setFile(f);
          }}
        >
          <div className="big">{file ? file.name : "Drop CSV here or click to browse"}</div>
          <div className="small">
            {file
              ? `${(file.size / 1024).toFixed(0)} KB · ready to analyse`
              : "columns: date, description, amount, balance_after, counterparty_raw, type"}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div style={{ height: 16 }} />
        <div className="field">
          <label>API key (sent as X-API-Key)</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="your RQS_API_KEY"
          />
        </div>
        <div className="grid cols-2">
          <div className="field">
            <label>API base URL</label>
            <input value={apiBase} onChange={(e) => setApiBase(e.target.value)} />
          </div>
          <div className="field">
            <label>Borrower name (optional)</label>
            <input
              value={borrowerName}
              onChange={(e) => setBorrowerName(e.target.value)}
              placeholder="sharpens related-party detection"
            />
          </div>
        </div>

        <button className="btn" disabled={!file || !apiKey || loading} onClick={submit}>
          {loading ? <span className="spinner" /> : null}
          {loading ? "Analysing…" : "Analyse statement"}
        </button>
      </div>
    </div>
  );
}
