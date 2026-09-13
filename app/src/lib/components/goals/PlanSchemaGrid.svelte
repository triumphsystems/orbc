<script lang="ts">
	import { Database } from '@lucide/svelte';
	import type { ExtractionSchema } from '$lib/api/types';

	interface Props {
		schema?: ExtractionSchema;
	}

	let { schema }: Props = $props();
</script>

<div class="space-y-2.5">
	<div class="flex items-center justify-between flex-wrap gap-1">
		<div class="flex items-center gap-2 text-xs font-mono text-slate-400 uppercase tracking-wider">
			<Database size={14} class="text-orbit-emerald" />
			<span>Dynamic Extraction Schema ({schema?.fields?.length || 0} fields)</span>
		</div>
		<span class="text-[11px] font-mono text-slate-500">Entity: {schema?.entity_name || 'item'}</span
		>
	</div>

	<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
		{#each schema?.fields || [] as field}
			<div
				class="p-2.5 rounded-lg bg-surface-850 border border-white/5 flex flex-col justify-between"
			>
				<div class="flex items-center justify-between gap-1">
					<span class="text-xs font-mono font-medium text-slate-200 truncate">{field.name}</span>
					<span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-700 text-orbit-cyan">
						{field.type}
					</span>
				</div>
				{#if field.description}
					<span class="text-[11px] text-slate-400 mt-1 line-clamp-1">{field.description}</span>
				{/if}
			</div>
		{/each}
	</div>
</div>
