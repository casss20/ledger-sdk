/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(222, 47%, 5%)",
        foreground: "hsl(210, 40%, 98%)",
        card: "hsl(222, 47%, 8%)",
        "card-foreground": "hsl(210, 40%, 98%)",
        primary: "hsl(186, 100%, 51%)", // cyan (#00f3ff)
        "primary-foreground": "hsl(222, 47%, 5%)",
        secondary: "hsl(217, 33%, 17%)",
        muted: "hsl(217, 33%, 17%)",
        accent: {
          success: "hsl(160, 84%, 39%)", // emerald
          warning: "hsl(38, 92%, 50%)",  // amber
          danger: "hsl(0, 84%, 60%)",    // red
        },
        border: "hsl(217, 33%, 20%)",
        input: "hsl(217, 33%, 20%)",
        ring: "hsl(186, 100%, 51%)",
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.25rem",
      },
      animation: {
        "pulse-slow": "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
}
