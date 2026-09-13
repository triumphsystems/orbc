<script lang="ts">
	import { goto } from '$app/navigation';
	import { Layers, Search, Plus } from '@lucide/svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import AutomationTable from '$lib/components/automations/AutomationTable.svelte';
	import AutomationCard from '$lib/components/automations/AutomationCard.svelte';

	let searchQuery = $state('');
	let runningId = $state<string | null>(null);

	const filteredAutomations = $derived.by(() => {
		if (!searchQuery.trim()) return orbitStore.automations;
		const q = searchQuery.toLowerCase();
		return orbitStore.automations.filter(
			(a) =>
				a.raw_goal.toLowerCase().includes(q) ||
				a.plan.objective.toLowerCase().includes(q) ||
				a.plan.domain.toLowerCase().includes(q)
		);
	});

	async function handleRun(id: string) {
		runningId = id;
		try {
			const run = await orbitStore.triggerRun(id);
			if (run) {
				goto(`/runs/${run.id}`);
			}
		} finally {
			runningId = null;
		}
	}

	async function handleDelete(id: string) {
		if (confirm('Are you sure you want to terminate and delete this automation?')) {
			await orbitStore.deleteAutomation(id);
		}
	}
</script>

<div class="max-w-6xl mx-auto space-y-4 sm:space-y-6">
	<!-- Desktop Header -->
	<div
		class="hidden sm:flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
	>
		<div>
			<h1 class="text-2xl font-bold text-slate-100 flex items-center gap-2 font-display">
				<Layers size={22} class="text-orbit-cyan" />
				<span>Automation Fleet</span>
			</h1>
			<p class="text-xs text-slate-400 font-sans mt-1">
				Your active automated data pipelines. Monitor recurring data extraction schedules, inspect
				data schemas, and execute runs on demand.
			</p>
		</div>

		<a href="/">
			<Button variant="primary" size="md">
				<Plus size={16} />
				<span>New Mission</span>
			</Button>
		</a>
	</div>

	<!-- Filter & Search Bar (with inline New Mission button on mobile) -->
	<div
		class="flex items-center gap-2 sm:gap-3 bg-surface-900 border border-white/10 p-2.5 sm:p-3 rounded-xl"
	>
		<div class="relative flex-1 min-w-0">
			<Search size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Search automations..."
				class="w-full pl-8 pr-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orbit-cyan/50 font-mono"
			/>
		</div>

		<a href="/" class="sm:hidden shrink-0">
			<Button variant="primary" size="sm" class="px-2.5 text-xs">
				<Plus size={14} />
				<span>New</span>
			</Button>
		</a>
	</div>

	<!-- Desktop View: Automations Table -->
	<div class="hidden md:block">
		<AutomationTable
			automations={filteredAutomations}
			runningAutomationId={runningId}
			onRun={handleRun}
			onDelete={handleDelete}
		/>
	</div>

	<!-- Mobile View: Automation Cards -->
	<div class="md:hidden space-y-3">
		{#each filteredAutomations as auto (auto.id)}
			<AutomationCard
				automation={auto}
				running={runningId === auto.id}
				onRun={handleRun}
				onDelete={handleDelete}
			/>
		{:else}
			<div
				class="border border-white/10 rounded-xl p-8 text-center bg-surface-900 text-slate-500 font-mono text-xs"
			>
				No matching automations found.
			</div>
		{/each}
	</div>
</div>
