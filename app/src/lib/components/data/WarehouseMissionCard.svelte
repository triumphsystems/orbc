<script lang="ts">
	import {
		ChevronDown,
		ChevronRight,
		CheckCircle2,
		ShieldAlert,
		ArrowUpRight,
		Calendar,
		Table
	} from '@lucide/svelte';
	import type { AutomationOut, ResultOut } from '$lib/api/types';
	import DataTable from './DataTable.svelte';

	interface Props {
		automation: AutomationOut;
		results: ResultOut[];
		validCount: number;
		anomalyCount: number;
		totalCount: number;
	}

	let { automation, results, validCount, anomalyCount, totalCount }: Props = $props();
	let isExpanded = $state(false);
</script>

<div
	class="bg-surface-900 border border-white/10 rounded-xl overflow-hidden shadow-xl transition-all"
>
	<!-- Collapsible Header Banner -->
	<div
		role="button"
		tabindex="0"
		onclick={() => (isExpanded = !isExpanded)}
		onkeydown={(e) => e.key === 'Enter' && (isExpanded = !isExpanded)}
		class="p-4 sm:p-5 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 cursor-pointer hover:bg-surface-850 select-none transition-colors"
	>
		<div class="space-y-1.5 min-w-0 flex-1">
			<div class="flex items-center gap-2 flex-wrap">
				<span
					class="px-2 py-0.5 rounded text-[10px] font-mono bg-orbit-cyan/10 text-orbit-cyan border border-orbit-cyan/30 uppercase tracking-wider"
				>
					Entity: {automation.plan?.extraction_schema?.entity_name || 'item'}
				</span>
				{#if automation.plan?.frequency}
					<span
						class="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-800 text-slate-400 border border-white/10 flex items-center gap-1"
					>
						<Calendar size={10} />
						<span>{automation.plan.frequency}</span>
					</span>
				{/if}
				<span
					class="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-800 text-slate-300 border border-white/10 flex items-center gap-1"
				>
					<Table size={10} />
					<span>{totalCount} records</span>
				</span>
			</div>

			<div class="flex items-center gap-2">
				{#if isExpanded}
					<ChevronDown size={16} class="text-orbit-cyan shrink-0" />
				{:else}
					<ChevronRight size={16} class="text-slate-400 shrink-0" />
				{/if}
				<h2 class="text-base sm:text-lg font-bold text-slate-100 font-display truncate">
					{automation.plan?.objective || automation.raw_goal}
				</h2>
			</div>
		</div>

		<!-- Telemetry & Actions -->
		<div
			class="flex items-center gap-3 self-end lg:self-auto shrink-0"
			onclick={(e) => e.stopPropagation()}
			role="presentation"
		>
			<div class="flex items-center gap-2 font-mono text-xs">
				<span
					class="flex items-center gap-1 text-emerald-400 bg-emerald-950/40 px-2 py-1 rounded border border-emerald-500/20"
				>
					<CheckCircle2 size={12} />
					{validCount} valid
				</span>
				{#if anomalyCount > 0}
					<span
						class="flex items-center gap-1 text-rose-400 bg-rose-950/40 px-2 py-1 rounded border border-rose-500/20"
					>
						<ShieldAlert size={12} />
						{anomalyCount} anomalies
					</span>
				{/if}
			</div>

			<a
				href="/automations/{automation.id}"
				class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-mono bg-surface-800 hover:bg-surface-700 text-slate-200 border border-white/10 transition-colors"
			>
				<span>Automation</span>
				<ArrowUpRight size={12} />
			</a>

			<button
				type="button"
				onclick={() => (isExpanded = !isExpanded)}
				class="px-3 py-1.5 rounded-lg text-xs font-mono bg-orbit-cyan/10 hover:bg-orbit-cyan/20 text-orbit-cyan border border-orbit-cyan/30 transition-colors"
			>
				{isExpanded ? 'Collapse' : 'Expand'}
			</button>
		</div>
	</div>

	<!-- Expanded Body -->
	{#if isExpanded}
		<div class="p-4 sm:p-5 pt-0 border-t border-white/5 space-y-4">
			{#if automation.plan?.extraction_schema?.fields?.length}
				<div class="flex items-center gap-2 flex-wrap text-xs font-mono text-slate-400 pt-3">
					<span class="text-[11px] text-slate-500">Schema Columns:</span>
					{#each automation.plan.extraction_schema.fields as field}
						<span
							class="px-2 py-0.5 rounded text-[11px] bg-surface-800 border border-white/5 text-slate-300"
						>
							{field.name}
							<span class="text-slate-500 text-[10px]"
								>({field.type}{field.required ? ' *' : ''})</span
							>
						</span>
					{/each}
				</div>
			{/if}

			<DataTable
				{results}
				title={`${automation.plan?.extraction_schema?.entity_name || 'Item'} Records`}
			/>
		</div>
	{/if}
</div>
