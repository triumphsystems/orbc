<script lang="ts">
	import { CheckCircle2, ShieldAlert } from '@lucide/svelte';
	import type { ResultOut } from '$lib/api/types';

	interface Props {
		row: ResultOut;
		index: number;
		columns: string[];
	}

	let { row, index, columns }: Props = $props();
</script>

<tr class="hover:bg-surface-800/60 transition-colors {row.valid ? '' : 'bg-rose-950/10'}">
	<td class="py-2.5 px-4 text-center text-slate-500">{index + 1}</td>
	<td class="py-2.5 px-4">
		{#if row.valid}
			<span
				class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-emerald-950/50 text-emerald-400 border border-emerald-500/30"
			>
				<CheckCircle2 size={11} /> PASSED
			</span>
		{:else}
			<span
				class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-rose-950/60 text-rose-400 border border-rose-500/30"
				title={row.validation_errors?.join('; ')}
			>
				<ShieldAlert size={11} /> ANOMALY
			</span>
		{/if}
	</td>

	{#each columns as col}
		<td class="py-2.5 px-4 text-slate-200 truncate max-w-xs font-sans">
			{row.data?.[col] !== undefined ? String(row.data[col]) : '—'}
		</td>
	{/each}

	<td class="py-2.5 px-4 text-slate-400 truncate max-w-xs font-mono text-[11px]">
		{#if row.url}
			<a
				href={row.url}
				target="_blank"
				rel="noreferrer"
				class="hover:text-orbit-cyan hover:underline"
			>
				{row.url}
			</a>
		{:else}
			<span class="text-slate-600">—</span>
		{/if}
	</td>
</tr>
