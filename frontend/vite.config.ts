import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API base is configured at runtime via VITE_API_BASE (see src/api.ts);
// no dev proxy needed since the backend enables CORS for this origin.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
