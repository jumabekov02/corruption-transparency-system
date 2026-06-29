import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on 0.0.0.0 so the container is reachable from your PC
    port: 5173,
    watch: {
      usePolling: true, // needed for live-reload to work inside Docker on Windows
    },
  },
});
