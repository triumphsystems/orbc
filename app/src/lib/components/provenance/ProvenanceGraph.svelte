<script lang="ts">
	import {
		BrainCircuit,
		Search,
		Globe,
		Database,
		ShieldCheck,
		Bell,
		CheckCircle2,
		AlertTriangle,
		XCircle,
		Clock,
		ArrowRight
	} from '@lucide/svelte';
	import type { RunOut } from '$lib/api/types';

	interface Props {
		run: RunOut;
		onSelectNode?: (nodeId: string) => void;
		selectedNode?: string | null;
	}

	let { run, onSelectNode, selectedNode }: Props = $props();

	// Derived stage states based on run progress
	const stages = $derived([
		{
			id: 'goal',
			name: 'Goal Synthesis',
			icon: BrainCircuit,
			description: 'LLM objective & schema derived',
			status: 'completed',
			metrics: 'Schema Ready'
		},
		{
			id: 'discovery',
			name: 'Source Discovery',
			icon: Search,
			description: 'Multi-source search queries',
			status:
				run.sources_found && run.sources_found.length > 0
					? 'completed'
					: run.status === 'running'
						? 'running'
						: 'pending',
			metrics: `${run.sources_found?.length || 0} sources found`
		},
		{
			id: 'retrieval',
			name: 'Proxy Retrieval',
			icon: Globe,
			description: 'Resilient web proxy fetching',
			status:
				run.pages_retrieved && run.pages_retrieved.length > 0
					? 'completed'
					: run.status === 'running'
						? 'running'
						: 'pending',
			metrics: `${run.pages_retrieved?.length || 0} pages fetched`
		},
		{
			id: 'extraction',
			name: 'Schema Extraction',
			icon: Database,
			description: 'Typed record extraction',
			status:
				(run.extracted_count ?? 0) > 0
					? 'completed'
					: run.status === 'running'
						? 'running'
						: 'pending',
			metrics: `${run.extracted_count || 0} records extracted`
		},
		{
			id: 'validation',
			name: 'Data Verification',
			icon: ShieldCheck,
			description: 'JSON Schema & Anomaly check',
			status: (run.validated_count ?? 0) > 0 ? 'completed' : run.error ? 'error' : 'pending',
			metrics: `${run.validated_count || 0} validated`
		},
		{
			id: 'condition',
			name: 'Condition & Sinks',
			icon: Bell,
			description: 'Trigger threshold evaluation',
			status:
				run.condition_matched === true
					? 'warning'
					: run.status === 'completed'
						? 'completed'
						: 'pending',
			metrics: run.condition_matched ? 'TRIGGERED' : 'EVALUATED'
		}
	]);

	const nodeStatusStyles = {
		completed: 'border-emerald-500/40 bg-surface-850 hover:border-emerald-400 text-emerald-400',
		running:
			'border-orbit-cyan/60 bg-surface-850 hover:border-orbit-cyan text-orbit-cyan animate-pulse shadow-glow-cyan/30',
		warning: 'border-amber-500/40 bg-surface-850 hover:border-amber-400 text-amber-400',
		error: 'border-rose-500/40 bg-surface-850 hover:border-rose-400 text-rose-400',
		pending: 'border-white/10 bg-surface-900/60 text-slate-500 hover:border-white/20'
	};
</script>

<div class="w-full overflow-x-auto py-2">
	<div class="flex items-center gap-3 min-w-[840px] px-1">
		{#each stages as stage, idx}
			<!-- Stage Node Card -->
			<button
				type="button"
				onclick={() => onSelectNode?.(stage.id)}
				class="flex-1 p-3.5 rounded-xl border text-left transition-all duration-200 cursor-pointer relative group {nodeStatusStyles[
					stage.status as keyof typeof nodeStatusStyles
				]} {selectedNode === stage.id
					? 'ring-2 ring-orbit-cyan ring-offset-2 ring-offset-surface-950'
					: ''}"
			>
				<div class="flex items-center justify-between gap-2 mb-2">
					<div
						class="p-2 rounded-lg bg-surface-800 border border-white/5 text-slate-100 group-hover:text-orbit-cyan transition-colors"
					>
						<stage.icon size={16} />
					</div>
					{#if stage.status === 'completed'}
						<CheckCircle2 size={15} class="text-emerald-400" />
					{:else if stage.status === 'running'}
						<Clock size={15} class="text-orbit-cyan animate-spin" />
					{:else if stage.status === 'warning'}
						<AlertTriangle size={15} class="text-amber-400" />
					{:else if stage.status === 'error'}
						<XCircle size={15} class="text-rose-400" />
					{/if}
				</div>

				<div class="text-xs font-semibold text-slate-100 group-hover:text-white truncate">
					{stage.name}
				</div>
				<div class="text-[11px] font-mono text-slate-400 mt-1 truncate">{stage.metrics}</div>
			</button>

			<!-- Connector Arrow -->
			{#if idx < stages.length - 1}
				<div class="text-slate-600 shrink-0">
					<ArrowRight size={14} />
				</div>
			{/if}
		{/each}
	</div>
</div>
