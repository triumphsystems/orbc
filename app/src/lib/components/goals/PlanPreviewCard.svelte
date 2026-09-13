<script lang="ts">
	import { Clock, Globe, Search, Bell, Play, Sliders } from '@lucide/svelte';
	import type { AutomationOut, ExecutionPlan } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import PlanSchemaGrid from './PlanSchemaGrid.svelte';
	import PlanWorkflowPipeline from './PlanWorkflowPipeline.svelte';
	import PlanMissingParams from './PlanMissingParams.svelte';

	interface Props {
		automation: AutomationOut;
		onRunNow?: (id: string) => void;
		running?: boolean;
	}

	let { automation, onRunNow, running = false }: Props = $props();

	const plan: ExecutionPlan = $derived(automation.plan);
	let userInputs = $state<Record<string, string>>({});

	$effect(() => {
		if (plan.missing_parameters) {
			const initial: Record<string, string> = {};
			for (const p of plan.missing_parameters) {
				initial[p.parameter_name] = p.default_value || '';
			}
			userInputs = initial;
		}
	});
</script>

<Card class="space-y-6 border-orbit-cyan/30 shadow-glow-cyan/10">
	<!-- Header -->
	<div
		class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-white/10 pb-4"
	>
		<div>
			<div class="flex items-center gap-2 mb-1 flex-wrap">
				<span
					class="px-2 py-0.5 rounded text-[11px] font-mono uppercase bg-orbit-cyan/20 text-orbit-cyan border border-orbit-cyan/30 font-semibold"
				>
					{plan.domain || 'GENERAL'} DOMAIN
				</span>
				{#if plan.geography}
					<span
						class="px-2 py-0.5 rounded text-[11px] font-mono bg-surface-700 text-slate-300 border border-white/10 flex items-center gap-1"
					>
						<Globe size={11} />
						{plan.geography}
					</span>
				{/if}
			</div>
			<h2 class="text-base sm:text-lg font-semibold text-slate-50 font-display">
				{plan.objective}
			</h2>
			<p class="text-xs text-slate-400 font-mono mt-1">Goal: "{automation.raw_goal}"</p>
		</div>

		<div class="flex items-center gap-2 w-full sm:w-auto justify-end">
			<a
				href="/workflows"
				class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-800 hover:bg-surface-700 border border-white/10 text-xs text-slate-300 hover:text-white transition-colors font-mono"
				title="Customize in Visual Workflow Canvas"
			>
				<Sliders size={13} class="text-orbit-cyan" />
				<span>Workflow Canvas</span>
			</a>

			{#if onRunNow}
				<Button
					variant="primary"
					size="md"
					loading={running}
					onclick={() => onRunNow(automation.id)}
					class="font-medium w-full sm:w-auto"
				>
					<Play size={15} />
					<span>Launch Mission</span>
				</Button>
			{/if}
		</div>
	</div>

	<!-- Synthesized Workflow DAG Pipeline -->
	{#if plan.workflow_nodes && plan.workflow_nodes.length > 0}
		<PlanWorkflowPipeline nodes={plan.workflow_nodes} />
	{/if}

	<!-- Interactive Missing Parameter Elicitation -->
	{#if plan.missing_parameters && plan.missing_parameters.length > 0}
		<PlanMissingParams parameters={plan.missing_parameters} bind:userInputs />
	{/if}

	<!-- Plan Grid -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
		<!-- Frequency & Schedule -->
		<div class="p-3.5 rounded-lg bg-surface-850 border border-white/5 space-y-1.5">
			<div class="flex items-center gap-1.5 text-xs text-slate-400 font-mono uppercase">
				<Clock size={13} class="text-orbit-cyan" />
				<span>Cadence & Schedule</span>
			</div>
			<div class="flex items-center gap-2">
				<span class="text-sm font-semibold text-slate-100 uppercase">{plan.frequency}</span>
				{#if plan.schedule_time}
					<span class="text-xs font-mono text-slate-400"
						>@ {plan.schedule_time} ({plan.timezone})</span
					>
				{/if}
			</div>
		</div>

		<!-- Search Query -->
		<div class="p-3.5 rounded-lg bg-surface-850 border border-white/5 space-y-1.5 md:col-span-2">
			<div class="flex items-center gap-1.5 text-xs text-slate-400 font-mono uppercase">
				<Search size={13} class="text-orbit-cyan" />
				<span>Discovery Query</span>
			</div>
			<div
				class="text-xs font-mono text-slate-200 truncate bg-surface-900 px-2.5 py-1 rounded border border-white/5"
			>
				{plan.search_query}
			</div>
		</div>
	</div>

	<!-- Extraction Schema -->
	<PlanSchemaGrid schema={plan.extraction_schema} />

	<!-- Condition Triggers if present -->
	{#if plan.condition}
		<div
			class="p-3 rounded-lg bg-amber-950/20 border border-amber-500/20 flex items-center justify-between"
		>
			<div class="flex items-center gap-2">
				<Bell size={15} class="text-amber-400" />
				<span class="text-xs text-slate-300">Alert Condition Trigger:</span>
				<code
					class="text-xs font-mono px-2 py-0.5 rounded bg-surface-900 text-amber-300 border border-amber-500/30"
				>
					{plan.condition}
				</code>
			</div>
			{#if plan.notification_channel}
				<span class="text-xs font-mono text-slate-400">Sink: {plan.notification_channel}</span>
			{/if}
		</div>
	{/if}
</Card>
