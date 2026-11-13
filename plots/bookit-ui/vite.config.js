import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
 
// The proxy sends every /api request to Django, so the browser sees one origin (no CORS setup needed).
export default defineConfig({
  plugins: [react() , tailwindcss()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
 