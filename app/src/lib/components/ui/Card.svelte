<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		hoverEffect?: boolean;
		glow?: 'cyan' | 'violet' | 'emerald' | 'amber' | 'none';
		children?: Snippet;
	}

	let {
		hoverEffect = true,
		glow = 'none',
		class: className = '',
		children,
		...restProps
	}: Props = $props();

	const glowClasses = {
		none: '',
		cyan: 'shadow-glow-cyan/20 border-cyan-500/30',
		violet: 'shadow-glow-violet/20 border-violet-500/30',
		emerald: 'shadow-glow-emerald/20 border-emerald-500/30',
		amber: 'shadow-glow-amber/20 border-amber-500/30'
	};
</script>

<div
	class="bg-surface-900/90 border border-white/[0.08] rounded-xl p-5 backdrop-blur-md transition-all duration-200 {hoverEffect
		? 'hover:border-white/[0.18]'
		: ''} {glowClasses[glow]} {className}"
	{...restProps}
>
	{@render children?.()}
</div>
