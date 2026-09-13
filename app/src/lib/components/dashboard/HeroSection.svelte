<script lang="ts">
	import OrbitLogo from '$lib/components/ui/OrbitLogo.svelte';
</script>

<div class="text-center space-y-5 pt-8 flex flex-col items-center">
	<OrbitLogo
		size="lg"
		showWordmark={false}
		animated={true}
		class="mb-2 hover:scale-105 transition-transform"
	/>
	<div
		class="inline-flex items-center px-3.5 py-1 rounded-full bg-orbit-cyan/10 border border-orbit-cyan/30 text-orbit-cyan text-xs font-mono shadow-glow-cyan/20"
	>
		<span>Set the goal. Walk away.</span>
	</div>
	<h1 class="text-4xl sm:text-5xl font-bold tracking-tight text-white font-display">
		Autonomous Web Data Operations
	</h1>
	<p class="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
		Define your data extraction objectives in plain language. Orbit discovers web sources, extracts
		verified structured data, and runs continuously on schedule with complete audit trails.
	</p>
</div>
