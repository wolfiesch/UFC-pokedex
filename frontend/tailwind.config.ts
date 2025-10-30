import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pokedexRed: "#E3350D",
        pokedexYellow: "#FFCB05",
        pokedexBlue: "#2A75BB",
      },
    },
  },
  plugins: [],
};

export default config;
