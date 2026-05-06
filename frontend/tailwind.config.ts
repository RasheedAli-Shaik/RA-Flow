import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}", "../shared/**/*.ts"],
  theme: {
    extend: {
      colors: {
        shell: "#091019",
        panel: "#0f1f2d",
        panelSoft: "#172b3b",
        neon: "#6bf1c7",
        ember: "#ff8a4d",
        frost: "#9dd8ff",
        paper: "#f3efe7"
      },
      boxShadow: {
        glow: "0 24px 80px rgba(107, 241, 199, 0.18)"
      },
      fontFamily: {
        display: ["Space Grotesk", "Segoe UI", "sans-serif"],
        body: ["Manrope", "Segoe UI", "sans-serif"]
      }
    }
  },
  plugins: []
} satisfies Config;

