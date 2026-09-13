<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	interface Props extends HTMLButtonAttributes {
		variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
		size?: 'sm' | 'md' | 'lg';
		loading?: boolean;
		children?: Snippet;
	}

	let {
		variant = 'primary',
		size = 'md',
		loading = false,
		class: className = '',
		disabled = false,
		children,
		...restProps
	}: Props = $props();

	const variantClasses = {
		primary:
			'bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium hover:from-cyan-400 hover:to-blue-500 shadow-glow-cyan/50 border border-cyan-400/30',
		secondary:
			'bg-surface-800 hover:bg-surface-700 text-slate-100 border border-white/10 shadow-sm',
		outline:
			'bg-transparent border border-white/20 hover:border-orbit-cyan/60 text-slate-200 hover:text-orbit-cyan hover:bg-orbit-cyan/5',
		ghost: 'bg-transparent text-slate-300 hover:text-white hover:bg-surface-700/50',
		danger:
			'bg-rose-950/50 text-rose-300 border border-rose-600/30 hover:bg-rose-900/60 hover:text-rose-200'
	};

	const sizeClasses = {
		sm: 'px-2.5 py-1 text-xs rounded-md gap-1.5',
		md: 'px-4 py-2 text-sm rounded-lg gap-2',
		lg: 'px-5 py-2.5 text-base rounded-xl gap-2.5'
	};
</script>

<button
	class="inline-flex items-center justify-center font-sans transition-all duration-150 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none {variantClasses[
		variant
	]} {sizeClasses[size]} {className}"
	disabled={disabled || loading}
	{...restProps}
>
	{#if loading}
		<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
			></circle>
			<path
				class="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			></path>
		</svg>
	{/if}
	{@render children?.()}
</button>
