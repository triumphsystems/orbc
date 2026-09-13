<script lang="ts">
	import { orbitStore } from '$lib/state/orbit.svelte';
	import OrbitLogo from '$lib/components/ui/OrbitLogo.svelte';
</script>

<!-- Mobile Header Bar (Clean & uncluttered, companion to BottomNav) -->
<header
	class="md:hidden h-14 bg-surface-900/80 border-b border-white/10 px-4 flex items-center justify-between shrink-0 z-30 sticky top-0 backdrop-blur-md"
>
	<a href="/">
		<OrbitLogo size="sm" showWordmark={true} animated={true} />
	</a>

	<div class="flex items-center gap-2">
		<span
			class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono border {orbitStore.daemonConnected
				? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30'
				: 'bg-rose-950/60 text-rose-400 border-rose-500/30'}"
		>
			<span
				class="w-1.5 h-1.5 rounded-full {orbitStore.daemonConnected
					? 'bg-emerald-400 animate-pulse'
					: 'bg-rose-400'}"
			></span>
			{orbitStore.daemonConnected ? 'ONLINE' : 'OFFLINE'}
		</span>
	</div>
</header>
