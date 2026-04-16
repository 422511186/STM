/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#3B82F6',
          hover: '#2563EB',
          light: '#EFF6FF',
          dark: '#1E3A5F',
        },
        success: {
          DEFAULT: '#10B981',
          hover: '#059669',
          bg: '#ECFDF5',
          'bg-dark': '#064E3B',
        },
        warning: {
          DEFAULT: '#F59E0B',
          hover: '#D97706',
          bg: '#FFFBEB',
          'bg-dark': '#78350F',
        },
        error: {
          DEFAULT: '#EF4444',
          hover: '#DC2626',
          bg: '#FEF2F2',
          'bg-dark': '#7F1D1D',
          subtle: '#FEE2E2',
          'subtle-dark': '#5C2020',
        },
        info: {
          DEFAULT: '#3B82F6',
          bg: '#EFF6FF',
          'bg-dark': '#1E3A5F',
        },
        text: {
          DEFAULT: '#111827',
          secondary: '#4B5563',
          muted: '#9CA3AF',
          'dark': '#F9FAFB',
        },
        bg: {
          main: '#F3F4F6',
          sidebar: '#FFFFFF',
          card: '#FFFFFF',
          input: '#F9FAFB',
          hover: '#F3F4F6',
          modal: '#FFFFFF',
          'main-dark': '#111827',
          'sidebar-dark': '#1F2937',
          'card-dark': '#1F2937',
          'input-dark': '#374151',
          'hover-dark': '#374151',
          'modal-dark': '#1F2937',
        },
        border: {
          DEFAULT: '#D1D5DB',
          focus: '#3B82F6',
          light: '#E5E7EB',
          'dark': '#4B5563',
          'light-dark': '#374151',
        },
      },
      spacing: {
        'xs': '4px',
        'sm': '8px',
        'md': '16px',
        'lg': '24px',
        'xl': '32px',
      },
      borderRadius: {
        'sm': '6px',
        'md': '10px',
        'lg': '16px',
        'xl': '20px',
      },
    },
  },
  plugins: [],
}
