<script lang="ts">
	import type { ResultOut } from '$lib/api/types';
	import DataTableControls from './DataTableControls.svelte';
	import DataTableRow from './DataTableRow.svelte';

	interface Props {
		results: ResultOut[];
		title?: string;
	}

	let { results = [] }: Props = $props();

	let searchQuery = $state('');
	let filterMode = $state<'all' | 'valid' | 'anomaly'>('all');

	// Extract unique dynamic columns across results
	const columns = $derived.by(() => {
		const cols = new Set<string>();
		for (const r of results) {
			if (r.data && typeof r.data === 'object') {
				Object.keys(r.data).forEach((k) => cols.add(k));
			}
		}
		return Array.from(cols);
	});

	// Filtered records
	const filteredResults = $derived.by(() => {
		return results.filter((r) => {
			if (filterMode === 'valid' && !r.valid) return false;
			if (filterMode === 'anomaly' && r.valid) return false;

			if (searchQuery.trim()) {
				const query = searchQuery.toLowerCase();
				const matchesUrl = r.url?.toLowerCase().includes(query);
				const matchesData = Object.values(r.data || {}).some((v) =>
					String(v).toLowerCase().includes(query)
				);
				return matchesUrl || matchesData;
			}
			return true;
		});
	});

	// CSV Export Handler
	function exportCSV() {
		if (results.length === 0) return;
		const headers = ['id', 'url', 'valid', ...columns];
		const rows = results.map((r) => {
			return [
				r.id,
				`"${r.url || ''}"`,
				r.valid ? 'true' : 'false',
				...columns.map((c) => {
					const val = r.data?.[c];
					return typeof val === 'string' ? `"${val.replace(/"/g, '""')}"` : (val ?? '');
				})
			].join(',');
		});

		const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
		const encodedUri = encodeURI(csvContent);
		const link = document.createElement('a');
		link.setAttribute('href', encodedUri);
		link.setAttribute('download', `orbit_data_${Date.now()}.csv`);
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
	}

	// JSON Export Handler
	function exportJSON() {
		if (results.length === 0) return;
		const dataStr =
			'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(results, null, 2));
		const downloadAnchor = document.createElement('a');
		downloadAnchor.setAttribute('href', dataStr);
		downloadAnchor.setAttribute('download', `orbit_data_${Date.now()}.json`);
		document.body.appendChild(downloadAnchor);
		downloadAnchor.click();
		downloadAnchor.remove();
	}
</script>

<div class="space-y-4">
	<!-- Control Bar -->
	<DataTableControls
		{searchQuery}
		{filterMode}
		totalCount={results.length}
		validCount={results.filter((r) => r.valid).length}
		anomalyCount={results.filter((r) => !r.valid).length}
		onSearchChange={(q) => (searchQuery = q)}
		onFilterChange={(m) => (filterMode = m)}
		onExportCSV={exportCSV}
		onExportJSON={exportJSON}
	/>

	<!-- High-Density Virtual Table -->
	<div class="border border-white/10 rounded-xl overflow-hidden bg-surface-900 shadow-2xl">
		<div class="overflow-x-auto max-h-[500px] overflow-y-auto">
			<table class="w-full text-left border-collapse font-sans text-xs">
				<thead
					class="sticky top-0 bg-surface-850 border-b border-white/10 text-[11px] font-mono uppercase text-slate-400 tracking-wider z-10"
				>
					<tr>
						<th class="py-3 px-4 w-12 text-center">#</th>
						<th class="py-3 px-4 w-28">Status</th>
						{#each columns as col}
							<th class="py-3 px-4 text-slate-200 font-semibold">{col}</th>
						{/each}
						<th class="py-3 px-4">Source URL</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-white/5 font-mono">
					{#each filteredResults as row, idx}
						<DataTableRow {row} index={idx} {columns} />
					{:else}
						<tr>
							<td colspan={columns.length + 3} class="py-12 text-center text-slate-500 font-mono">
								No extracted data records found.
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</div>
