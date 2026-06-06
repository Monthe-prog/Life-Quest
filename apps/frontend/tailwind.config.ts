import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        operator: {
          void: "#07080A",
          surface: "#11100D",
          purple: "#B772FF",
          cyan: "#6DF7D2"
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

