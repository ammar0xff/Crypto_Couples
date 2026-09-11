import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
    },
    extend: {
      colors: {
        bg: "hsl(232 35% 4.5%)",
        surface: "hsl(229 28% 8%)",
        elevated: "hsl(228 28% 11%)",
        border: "hsl(226 18% 17%)",
        primary: {
          DEFAULT: "hsl(247 100% 69%)",
          foreground: "hsl(0 0% 100%)",
        },
        secondary: {
          DEFAULT: "hsl(228 28% 11%)",
          foreground: "hsl(210 40% 98%)",
        },
        success: "hsl(142 71% 45%)",
        warning: "hsl(38 92% 50%)",
        danger: "hsl(0 84% 60%)",
        info: "hsl(199 89% 48%)",
        text: {
          DEFAULT: "hsl(210 40% 98%)",
          muted: "hsl(215 16% 65%)",
          faint: "hsl(219 13% 47%)",
        },
        muted: "hsl(215 16% 65%)",
        popover: "hsl(229 28% 8%)",
        accent: "hsl(228 28% 14%)",
        input: "hsl(226 18% 17%)",
        card: "hsl(229 28% 8%)",
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.375rem",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out",
        "slide-up": "slide-up 0.25s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;