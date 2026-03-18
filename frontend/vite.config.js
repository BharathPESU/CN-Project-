import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";

const httpsEnabled = process.env.VITE_HTTPS === "true";
const certPath = process.env.VITE_SSL_CERT;
const keyPath = process.env.VITE_SSL_KEY;

const httpsConfig =
  httpsEnabled && certPath && keyPath
    ? {
        cert: fs.readFileSync(certPath),
        key: fs.readFileSync(keyPath),
      }
    : httpsEnabled;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    https: httpsConfig,
    // Proxy API calls to the FastAPI backend so no CORS issues in dev.
    proxy: {
      "/scan": {
        target: "https://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
