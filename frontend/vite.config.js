import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI backend so no CORS issues in dev.
    proxy: {
      "/scan": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
