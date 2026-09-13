<script lang="ts">
	import { onMount } from 'svelte';
	import { RefreshCw, Filter, Layers, Target } from '@lucide/svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';
	import { api } from '$lib/api/client';
	import type { AutomationOut, ResultOut } from '$lib/api/types';
	import WarehouseHeader from '$lib/components/data/WarehouseHeader.svelte';
	import WarehouseMissionCard from '$lib/components/data/WarehouseMissionCard.svelte';

	interface MissionData {
		automation: AutomationOut;
		results: ResultOut[];
		validCount: number;
		anomalyCount: number;
		totalCount: number;
	}

	let missionsData = $state<MissionData[]>([]);
	let selectedMissionId = $state<string>('all');
	let loading = $state(true);

	const totalRecords = $derived(missionsData.reduce((acc, m) => acc + m.totalCount, 0));
	const totalValid = $derived(missionsData.reduce((acc, m) => acc + m.validCount, 0));
	const totalAnomalies = $derived(missionsData.reduce((acc, m) => acc + m.anomalyCount, 0));

	const visibleMissions = $derived(
		selectedMissionId === 'all'
			? missionsData
			: missionsData.filter((m) => m.automation.id === selectedMissionId)
	);

	async function loadWarehouseData() {
		loading = true;
		try {
			await orbitStore.loadAutomations();
			const missions: MissionData[] = [];
			await Promise.all(
				orbitStore.automations.map(async (auto) => {
					try {
						const runs = await api.listAutomationRuns(auto.id);
						const autoResults: ResultOut[] = runs.flatMap((r) => r.results || []);
						const valid = autoResults.filter((r) => r.valid).length;
						missions.push({
							automation: auto,
							results: autoResults,
							validCount: valid,
							anomalyCount: autoResults.length - valid,
							totalCount: autoResults.length
						});
					} catch {}
				})
			);
			missionsData = missions;
		} finally {
			loading = false;
		}
	}

	onMount(loadWarehouseData);
</script>

<div class="max-w-7xl mx-auto space-y-6">
	<WarehouseHeader
		totalMissions={missionsData.length}
		{totalRecords}
		{totalValid}
		{totalAnomalies}
		{loading}
		onRefresh={loadWarehouseData}
	/>

	<!-- Mission Selector Tabs -->
	<div
		class="bg-surface-900 border border-white/10 p-2 rounded-xl flex items-center gap-2 overflow-x-auto"
	>
		<div class="flex items-center gap-1.5 text-xs text-slate-400 px-2 shrink-0 font-mono">
			<Filter size={13} class="text-orbit-cyan" />
			<span>Filter Mission:</span>
		</div>

		<button
			type="button"
			onclick={() => (selectedMissionId = 'all')}
			class="px-3 py-1.5 rounded-lg text-xs font-mono transition-colors shrink-0 flex items-center gap-1.5 {selectedMissionId ===
			'all'
				? 'bg-orbit-cyan/20 text-orbit-cyan border border-orbit-cyan/40 font-medium'
				: 'text-slate-400 hover:text-slate-200'}"
		>
			<Layers size={13} />
			<span>All Missions</span>
			<span class="px-1.5 py-0.2 text-[10px] rounded bg-white/10 text-slate-300 font-mono"
				>{missionsData.length}</span
			>
		</button>

		{#each missionsData as m}
			<button
				type="button"
				onclick={() => (selectedMissionId = m.automation.id)}
				class="px-3 py-1.5 rounded-lg text-xs font-mono transition-colors shrink-0 flex items-center gap-1.5 max-w-xs truncate {selectedMissionId ===
				m.automation.id
					? 'bg-orbit-cyan/20 text-orbit-cyan border border-orbit-cyan/40 font-medium'
					: 'text-slate-400 hover:text-slate-200'}"
				title={m.automation.raw_goal}
			>
				<Target size={13} />
				<span class="truncate">{m.automation.plan?.objective || m.automation.raw_goal}</span>
				<span class="px-1.5 py-0.2 text-[10px] rounded bg-white/10 text-slate-300 font-mono"
					>{m.totalCount}</span
				>
			</button>
		{/each}
	</div>

	<!-- Collapsible Mission Cards -->
	{#if loading && missionsData.length === 0}
		<div
			class="bg-surface-900 border border-white/10 rounded-xl p-12 text-center text-slate-400 font-mono text-xs flex flex-col items-center gap-3"
		>
			<RefreshCw size={24} class="animate-spin text-orbit-cyan" />
			<span>Indexing data warehouse records...</span>
		</div>
	{:else if visibleMissions.length === 0}
		<div
			class="bg-surface-900 border border-white/10 rounded-xl p-12 text-center text-slate-400 font-mono text-xs"
		>
			No records found in the warehouse for the selected view.
		</div>
	{:else}
		<div class="space-y-4">
			{#each visibleMissions as mission (mission.automation.id)}
				<WarehouseMissionCard
					automation={mission.automation}
					results={mission.results}
					validCount={mission.validCount}
					anomalyCount={mission.anomalyCount}
					totalCount={mission.totalCount}
				/>
			{/each}
		</div>
	{/if}
</div>
