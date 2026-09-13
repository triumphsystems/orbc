<script lang="ts">
	import OrbitMark from './OrbitMark.svelte';

	interface Props {
		size?: 'sm' | 'md' | 'lg';
		showWordmark?: boolean;
		animated?: boolean;
		class?: string;
	}

	let {
		size = 'md',
		showWordmark = true,
		animated = true,
		class: className = ''
	}: Props = $props();

	const wordmarkSizes = {
		sm: 'text-sm tracking-wide',
		md: 'text-base tracking-widest',
		lg: 'text-xl tracking-[0.2em]'
	};
</script>

<div class="inline-flex items-center gap-2.5 select-none {className}">
	<!-- Vector Planetary Orbit Mark -->
	<OrbitMark {size} {animated} />

	<!-- Optional Wordmark & Telemetry Badge -->
	{#if showWordmark}
		<div class="flex flex-col">
			<div class="flex items-center gap-1.5 leading-none">
				<span class="font-extrabold text-white font-display {wordmarkSizes[size]}"> ORBIT </span>
				<span class="w-1.5 h-1.5 rounded-full bg-orbit-emerald animate-pulse"></span>
			</div>
			<span
				class="text-[9px] font-semibold tracking-widest text-orbit-cyan-glow uppercase mt-0.5 opacity-80"
			>
				Autonomous Data Ops
			</span>
		</div>
	{/if}
</div>
