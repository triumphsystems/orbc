<script lang="ts">
	import { Search, Download, FileText } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		searchQuery: string;
		filterMode: 'all' | 'valid' | 'anomaly';
		totalCount: number;
		validCount: number;
		anomalyCount: number;
		onSearchChange: (query: string) => void;
		onFilterChange: (mode: 'all' | 'valid' | 'anomaly') => void;
		onExportCSV: () => void;
		onExportJSON: () => void;
	}

	let {
		searchQuery,
		filterMode,
		totalCount,
		validCount,
		anomalyCount,
		onSearchChange,
		onFilterChange,
		onExportCSV,
		onExportJSON
	}: Props = $props();
</script>

<div
	class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 bg-surface-900 border border-white/10 p-3 rounded-xl"
>
	<!-- Search & Filters -->
	<div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-1">
		<div class="relative flex-1 min-w-0">
			<Search size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
			<input
				type="text"
				value={searchQuery}
				oninput={(e) => onSearchChange(e.currentTarget.value)}
				placeholder="Filter records..."
				class="w-full pl-8 pr-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orbit-cyan/50 font-mono"
			/>
		</div>

		<!-- Filter Pills -->
		<div
			class="flex items-center gap-1 bg-surface-800 p-0.5 rounded-lg border border-white/5 font-mono text-xs overflow-x-auto"
		>
			<button
				type="button"
				onclick={() => onFilterChange('all')}
				class="px-2.5 py-1 rounded-md transition-colors whitespace-nowrap {filterMode === 'all'
					? 'bg-surface-700 text-white font-medium'
					: 'text-slate-400 hover:text-slate-200'}"
			>
				All ({totalCount})
			</button>
			<button
				type="button"
				onclick={() => onFilterChange('valid')}
				class="px-2.5 py-1 rounded-md transition-colors whitespace-nowrap {filterMode === 'valid'
					? 'bg-emerald-950/80 text-emerald-400 font-medium'
					: 'text-slate-400 hover:text-slate-200'}"
			>
				Valid ({validCount})
			</button>
			<button
				type="button"
				onclick={() => onFilterChange('anomaly')}
				class="px-2.5 py-1 rounded-md transition-colors whitespace-nowrap {filterMode === 'anomaly'
					? 'bg-rose-950/80 text-rose-400 font-medium'
					: 'text-slate-400 hover:text-slate-200'}"
			>
				Anomalies ({anomalyCount})
			</button>
		</div>
	</div>

	<!-- Action Exports -->
	<div class="flex items-center gap-2 self-end lg:self-auto shrink-0">
		<Button variant="secondary" size="sm" onclick={onExportCSV} disabled={totalCount === 0}>
			<Download size={13} />
			<span>CSV</span>
		</Button>
		<Button variant="secondary" size="sm" onclick={onExportJSON} disabled={totalCount === 0}>
			<FileText size={13} />
			<span>JSON</span>
		</Button>
	</div>
</div>
