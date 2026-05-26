import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        operator: {
          void: "#050507",
          surface: "#0D0D11",
          purple: "#D000FF",
          cyan: "#00F0FF"
        }
      },
      fontFamily: {
        mono: ["var(--font-operator)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"]
      }
    }
  },
  plugins: []
};

export default config;

