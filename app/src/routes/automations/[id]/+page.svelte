<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { ArrowLeft, Trash2 } from '@lucide/svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';
	import { api } from '$lib/api/client';
	import type { AutomationOut, RunOut } from '$lib/api/types';
	import PlanPreviewCard from '$lib/components/goals/PlanPreviewCard.svelte';
	import RunsHistoryTable from '$lib/components/automations/RunsHistoryTable.svelte';

	let automation = $state<AutomationOut | null>(null);
	let runs = $state<RunOut[]>([]);
	let loading = $state(true);
	let deleting = $state(false);

	const autoId = $derived(page.params.id);

	onMount(async () => {
		if (autoId) {
			try {
				automation = await api.getAutomation(autoId);
				runs = await api.listAutomationRuns(autoId);
			} catch (err) {
				console.error(err);
			} finally {
				loading = false;
			}
		}
	});

	async function handleRunNow() {
		if (!autoId) return;
		const run = await orbitStore.triggerRun(autoId);
		if (run) {
			goto(`/runs/${run.id}`);
		}
	}

	async function handleDelete() {
		if (!autoId) return;
		if (
			confirm(
				'Are you sure you want to terminate and delete this automation and all its run history?'
			)
		) {
			deleting = true;
			try {
				await orbitStore.deleteAutomation(autoId);
				goto('/automations');
			} catch (err) {
				console.error('Failed to delete automation:', err);
				deleting = false;
			}
		}
	}
</script>

<div class="max-w-6xl mx-auto space-y-8">
	<!-- Top Navigation Bar with Actions -->
	<div class="flex items-center justify-between">
		<a
			href="/automations"
			class="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-orbit-cyan transition-colors"
		>
			<ArrowLeft size={14} />
			<span>Back to Automation Fleet</span>
		</a>

		{#if automation}
			<button
				type="button"
				onclick={handleDelete}
				disabled={deleting}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 hover:text-rose-200 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-600/30 transition-all disabled:opacity-50"
			>
				<Trash2 size={13} />
				<span>{deleting ? 'Deleting...' : 'Delete Automation'}</span>
			</button>
		{/if}
	</div>

	{#if loading}
		<div class="text-center py-16 font-mono text-slate-400 text-sm">
			Loading automation details...
		</div>
	{:else if automation}
		<!-- Automation Plan View -->
		<PlanPreviewCard {automation} onRunNow={handleRunNow} running={orbitStore.runningAutomation} />

		<!-- Execution History -->
		<RunsHistoryTable {runs} />
	{:else}
		<div class="text-center py-16 text-rose-400 font-mono text-sm">Automation not found.</div>
	{/if}
</div>
