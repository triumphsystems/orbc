<script lang="ts">
	import { ShieldAlert, X } from '@lucide/svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';

	let dismissed = $state(false);
</script>

{#if !orbitStore.daemonConnected && !dismissed}
	<div
		class="bg-rose-950/90 border-b border-rose-500/20 px-4 sm:px-6 py-2.5 text-xs flex items-center gap-3"
	>
		<ShieldAlert size={14} class="text-rose-400 shrink-0" />
		<span class="text-rose-200 flex-1 min-w-0">
			<strong class="font-semibold text-rose-300">Daemon unreachable.</strong>
			<span class="hidden sm:inline">
				The Orbit core service is offline — automations will not run.</span
			>
		</span>
		<div class="flex items-center gap-2 shrink-0">
			<button
				type="button"
				onclick={() => orbitStore.checkHealth()}
				class="px-2.5 py-1 rounded-md bg-rose-900/80 hover:bg-rose-800 text-rose-100 text-[11px] font-medium transition-colors border border-rose-700/50"
			>
				Retry
			</button>
			<button
				type="button"
				onclick={() => (dismissed = true)}
				class="text-rose-400 hover:text-rose-200 transition-colors p-0.5 rounded"
				aria-label="Dismiss"
			>
				<X size={14} />
			</button>
		</div>
	</div>
{/if}
