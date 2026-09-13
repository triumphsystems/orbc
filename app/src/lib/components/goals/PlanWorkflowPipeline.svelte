<script lang="ts">
	import {
		Clock,
		Globe,
		Database,
		Mail,
		MessageSquare,
		Sparkles,
		GitBranch,
		ArrowRight
	} from '@lucide/svelte';
	import type { ExecutionPlan } from '$lib/api/types';

	interface Props {
		nodes: NonNullable<ExecutionPlan['workflow_nodes']>;
	}

	let { nodes }: Props = $props();

	function getNodeIcon(typeId: string) {
		if (typeId.includes('trigger')) return Clock;
		if (typeId.includes('discovery')) return Globe;
		if (typeId.includes('schema') || typeId.includes('database')) return Database;
		if (typeId.includes('email')) return Mail;
		if (typeId.includes('slack')) return MessageSquare;
		if (typeId.includes('dossier')) return Sparkles;
		return GitBranch;
	}
</script>

<div class="space-y-2 p-3.5 rounded-xl bg-surface-900/90 border border-white/10">
	<div class="flex items-center justify-between">
		<div
			class="flex items-center gap-2 text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider"
		>
			<GitBranch size={14} class="text-orbit-cyan" />
			<span>Synthesized Agentic Workflow DAG</span>
		</div>
		<span class="text-[10px] font-mono text-slate-500">Autonomous multi-adapter sequence</span>
	</div>

	<div class="flex items-center gap-2 overflow-x-auto py-2 scrollbar-none">
		{#each nodes as node, i}
			{@const NodeIcon = getNodeIcon(node.typeId || '')}
			<div class="flex items-center gap-2 shrink-0">
				<div
					class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-800 border border-white/10 text-xs font-medium text-slate-200"
				>
					<NodeIcon size={14} class="text-orbit-cyan" />
					<span>{node.label || node.typeId}</span>
					<span
						class="text-[9px] font-mono uppercase px-1 py-0.2 rounded border {node.adapterType ===
						'managed'
							? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/20'
							: 'bg-cyan-950/40 text-cyan-300 border-cyan-500/20'}"
					>
						{node.adapterType || 'managed'}
					</span>
				</div>

				{#if i < nodes.length - 1}
					<ArrowRight size={13} class="text-slate-500 shrink-0" />
				{/if}
			</div>
		{/each}
	</div>
</div>
