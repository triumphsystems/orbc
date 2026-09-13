<script lang="ts">
	import { Database, RefreshCw } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		totalMissions: number;
		totalRecords: number;
		totalValid: number;
		totalAnomalies: number;
		loading: boolean;
		onRefresh: () => void;
	}

	let { totalMissions, totalRecords, totalValid, totalAnomalies, loading, onRefresh }: Props =
		$props();
</script>

<div class="space-y-3 sm:space-y-5">
	<div class="flex items-center justify-between gap-4">
		<div class="hidden sm:block">
			<h1
				class="text-2xl font-bold text-slate-100 flex items-center gap-2.5 font-display tracking-tight"
			>
				<Database size={24} class="text-orbit-cyan" />
				<span>Data Warehouse</span>
			</h1>
			<p class="text-xs text-slate-400 font-sans mt-1">
				Mission-segregated data repository of validated entities, schema tables, and anomalies.
			</p>
		</div>

		<Button
			variant="secondary"
			size="sm"
			onclick={onRefresh}
			{loading}
			class="w-full sm:w-auto sm:size-md justify-center"
		>
			<RefreshCw size={14} class={loading ? 'animate-spin' : ''} />
			<span class="sm:hidden">Refresh Data</span>
			<span class="hidden sm:inline">Refresh Warehouse</span>
		</Button>
	</div>

	<div class="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3">
		<div
			class="bg-surface-900 border border-white/10 rounded-xl p-3 sm:p-4 flex flex-col justify-between"
		>
			<span class="text-[10px] sm:text-[11px] font-mono text-slate-400 uppercase tracking-wider"
				>Missions Tracked</span
			>
			<div class="text-xl sm:text-2xl font-bold font-mono text-slate-100 mt-1.5 sm:mt-2">
				{totalMissions}
			</div>
		</div>
		<div
			class="bg-surface-900 border border-white/10 rounded-xl p-3 sm:p-4 flex flex-col justify-between"
		>
			<span class="text-[10px] sm:text-[11px] font-mono text-slate-400 uppercase tracking-wider"
				>Total Records</span
			>
			<div class="text-xl sm:text-2xl font-bold font-mono text-orbit-cyan mt-1.5 sm:mt-2">
				{totalRecords}
			</div>
		</div>
		<div
			class="bg-surface-900 border border-white/10 rounded-xl p-3 sm:p-4 flex flex-col justify-between"
		>
			<span class="text-[10px] sm:text-[11px] font-mono text-slate-400 uppercase tracking-wider"
				>Verified Valid</span
			>
			<div class="text-xl sm:text-2xl font-bold font-mono text-emerald-400 mt-1.5 sm:mt-2">
				{totalValid}
			</div>
		</div>
		<div
			class="bg-surface-900 border border-white/10 rounded-xl p-3 sm:p-4 flex flex-col justify-between"
		>
			<span class="text-[10px] sm:text-[11px] font-mono text-slate-400 uppercase tracking-wider"
				>Anomalies</span
			>
			<div class="text-xl sm:text-2xl font-bold font-mono text-rose-400 mt-1.5 sm:mt-2">
				{totalAnomalies}
			</div>
		</div>
	</div>
</div>
