<script lang="ts">
	import type { RunOut } from '$lib/api/types';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';

	interface Props {
		run: RunOut;
	}

	let { run }: Props = $props();
</script>

<div
	class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-white/5 pb-4"
>
	<div>
		<div class="flex items-center gap-2 mb-1 flex-wrap">
			<span class="text-xs font-mono text-slate-400">RUN:</span>
			<code class="text-xs font-mono text-orbit-cyan break-all">{run.id}</code>
			<StatusBadge status={run.status} />
		</div>
		<div class="text-xs text-slate-400 font-mono">
			Started: {new Date(run.started_at).toLocaleString()}
			{#if run.finished_at}
				• Finished: {new Date(run.finished_at).toLocaleString()}
			{/if}
		</div>
	</div>

	<!-- Telemetry Counter Chips -->
	<div class="grid grid-cols-2 sm:flex sm:items-center gap-2 text-xs font-mono">
		<div
			class="px-3 py-1.5 rounded-lg bg-surface-800 border border-white/5 text-center sm:text-left"
		>
			<span class="text-slate-500 text-[10px] block sm:inline">SOURCES:</span>
			<strong class="text-slate-200">{run.sources_found?.length || 0}</strong>
		</div>
		<div
			class="px-3 py-1.5 rounded-lg bg-surface-800 border border-white/5 text-center sm:text-left"
		>
			<span class="text-slate-500 text-[10px] block sm:inline">PAGES:</span>
			<strong class="text-slate-200">{run.pages_retrieved?.length || 0}</strong>
		</div>
		<div
			class="px-3 py-1.5 rounded-lg bg-surface-800 border border-white/5 text-center sm:text-left"
		>
			<span class="text-slate-500 text-[10px] block sm:inline">EXTRACTED:</span>
			<strong class="text-emerald-400">{run.extracted_count || 0}</strong>
		</div>
		<div
			class="px-3 py-1.5 rounded-lg bg-surface-800 border border-white/5 text-center sm:text-left"
		>
			<span class="text-slate-500 text-[10px] block sm:inline">VALIDATED:</span>
			<strong class="text-orbit-cyan">{run.validated_count || 0}</strong>
		</div>
	</div>
</div>
