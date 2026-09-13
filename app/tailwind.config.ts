import type { Config } from 'tailwindcss';

export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				void: {
					DEFAULT: '#07090E',
					950: '#07090E'
				},
				surface: {
					950: '#07090E',
					900: '#0E131F',
					850: '#111726',
					800: '#141B2D',
					700: '#1D263B',
					600: '#2A364F',
					500: '#3D4C6B'
				},
				orbit: {
					cyan: '#00F2FE',
					'cyan-glow': '#38BDF8',
					violet: '#8B5CF6',
					'violet-glow': '#A855F7',
					emerald: '#10B981',
					amber: '#F59E0B',
					rose: '#EF4444'
				}
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
				mono: ['JetBrains Mono', 'Fira Code', 'monospace']
			},
			boxShadow: {
				'glow-cyan': '0 0 25px -5px rgba(56, 189, 248, 0.3)',
				'glow-violet': '0 0 25px -5px rgba(139, 92, 246, 0.3)',
				'glow-emerald': '0 0 25px -5px rgba(16, 185, 129, 0.3)',
				'glow-amber': '0 0 25px -5px rgba(245, 158, 11, 0.3)'
			},
			animation: {
				'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite'
			}
		}
	},
	plugins: []
} satisfies Config;
