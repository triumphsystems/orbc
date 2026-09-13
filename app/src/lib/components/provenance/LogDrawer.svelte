<script lang="ts">
	import { Terminal, ShieldAlert, Globe, Search, BrainCircuit, ExternalLink } from '@lucide/svelte';
	import type { RunOut } from '$lib/api/types';
	import Drawer from '$lib/components/ui/Drawer.svelte';

	interface Props {
		open: boolean;
		run: RunOut | null;
		activeNode?: string | null;
		onClose: () => void;
	}

	let { open = $bindable(), run, activeNode = 'all', onClose }: Props = $props();
</script>

<Drawer
	{open}
	{onClose}
	title={activeNode === 'all'
		? 'Run Telemetry & Audit Logs'
		: `Inspection: ${activeNode?.toUpperCase()}`}
	subtitle={run ? `Run ID: ${run.id} • Status: ${run.status.toUpperCase()}` : ''}
>
	{#if run}
		<!-- Error Alert if failed -->
		{#if run.error}
			<div class="p-4 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 space-y-1">
				<div class="flex items-center gap-2 font-semibold text-xs text-rose-200">
					<ShieldAlert size={16} />
					<span>Execution Failure Trace</span>
				</div>
				<p class="text-xs font-mono">{run.error}</p>
			</div>
		{/if}

		<!-- Condition Alert if triggered -->
		{#if run.condition_message}
			<div
				class="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-300 space-y-1"
			>
				<div class="font-semibold text-xs text-amber-200">Condition Evaluation:</div>
				<p class="text-xs font-mono">{run.condition_message}</p>
			</div>
		{/if}

		<!-- Discovered Sources Tab -->
		{#if activeNode === 'all' || activeNode === 'discovery'}
			<div class="space-y-2">
				<div
					class="flex items-center gap-2 text-xs font-mono text-slate-300 uppercase tracking-wider"
				>
					<Search size={14} class="text-orbit-violet" />
					<span>Discovered Candidate Sources ({run.sources_found?.length || 0})</span>
				</div>
				<div
					class="bg-surface-950 border border-white/10 rounded-xl p-3 space-y-1.5 font-mono text-xs max-h-48 overflow-y-auto"
				>
					{#each run.sources_found || [] as url}
						<div
							class="flex items-center justify-between gap-2 text-slate-300 hover:text-orbit-cyan"
						>
							<span class="truncate">{url}</span>
							<a
								href={url}
								target="_blank"
								rel="noreferrer"
								class="shrink-0 text-slate-500 hover:text-slate-200"
							>
								<ExternalLink size={12} />
							</a>
						</div>
					{:else}
						<div class="text-slate-600 italic">No sources discovered yet.</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Retrieved Pages Tab -->
		{#if activeNode === 'all' || activeNode === 'retrieval'}
			<div class="space-y-2">
				<div
					class="flex items-center gap-2 text-xs font-mono text-slate-300 uppercase tracking-wider"
				>
					<Globe size={14} class="text-orbit-cyan" />
					<span>Proxy Retrieved Pages ({run.pages_retrieved?.length || 0})</span>
				</div>
				<div
					class="bg-surface-950 border border-white/10 rounded-xl p-3 space-y-1.5 font-mono text-xs max-h-48 overflow-y-auto"
				>
					{#each run.pages_retrieved || [] as pageUrl}
						<div class="flex items-center justify-between gap-2 text-slate-300">
							<span class="truncate">{pageUrl}</span>
							<span
								class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
								>200 OK</span
							>
						</div>
					{:else}
						<div class="text-slate-600 italic">No pages retrieved.</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Agent Brain Reasoning Log -->
		{#if activeNode === 'all' || activeNode === 'goal' || activeNode === 'validation'}
			<div class="space-y-2">
				<div
					class="flex items-center gap-2 text-xs font-mono text-slate-300 uppercase tracking-wider"
				>
					<BrainCircuit size={14} class="text-orbit-emerald" />
					<span>Agent Brain Reasoning Log ({run.reasoning_log?.length || 0} events)</span>
				</div>
				<div
					class="bg-surface-950 border border-white/10 rounded-xl p-3 space-y-2.5 font-mono text-xs max-h-64 overflow-y-auto"
				>
					{#each run.reasoning_log || [] as entry}
						<div class="border-b border-white/5 pb-2.5 last:border-0 last:pb-0 space-y-1">
							<div class="flex items-center justify-between text-[11px] text-slate-400">
								<span class="text-orbit-cyan font-semibold"
									>{entry.stage ? entry.stage.toUpperCase() : entry.step || 'AGENT'}</span
								>
								<span>{entry.timestamp || ''}</span>
							</div>
							{#if entry.decision}
								<p class="text-purple-200 text-xs font-sans">
									<strong class="text-purple-300">Self-Correction:</strong>
									{entry.decision.diagnosis}
								</p>
								{#if entry.decision.new_search_query}
									<p class="text-[11px] text-slate-400 font-mono">
										→ Retried with: <code class="text-orbit-cyan"
											>"{entry.decision.new_search_query}"</code
										>
									</p>
								{/if}
							{:else if entry.report}
								<p class="text-emerald-300 text-xs font-sans">
									<strong>Verification:</strong>
									{entry.report.summary || 'Completed verification'}
								</p>
							{:else}
								<p class="text-slate-200 text-xs font-sans">
									{entry.message || JSON.stringify(entry)}
								</p>
							{/if}
						</div>
					{:else}
						<div class="text-slate-600 italic">No agent log events recorded.</div>
					{/each}
				</div>
			</div>
		{/if}
	{:else}
		<div class="text-center py-12 text-slate-500 font-mono text-sm">No active run selected.</div>
	{/if}
</Drawer>
