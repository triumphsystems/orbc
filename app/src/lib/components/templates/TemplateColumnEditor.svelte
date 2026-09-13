<script lang="ts">
	import { Plus, Trash2 } from '@lucide/svelte';

	interface Props {
		columns: string[];
		onChange: (cols: string[]) => void;
	}

	let { columns, onChange }: Props = $props();
	let newColumn = $state('');

	function add() {
		const col = newColumn.trim().toLowerCase().replace(/\s+/g, '_');
		if (col && !columns.includes(col)) onChange([...columns, col]);
		newColumn = '';
	}

	function remove(col: string) {
		onChange(columns.filter((c) => c !== col));
	}
</script>

<section class="space-y-2.5 pt-2 border-t border-white/8">
	<h3 class="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Data Columns</h3>
	<p class="text-[10px] font-mono text-slate-500">
		Fields from extraction records shown in the report table.
	</p>

	<div class="flex flex-wrap gap-1.5">
		{#each columns as col}
			<span
				class="flex items-center gap-1 pl-2.5 pr-1 py-1 bg-surface-800 border border-white/10 rounded-full text-[11px] font-mono text-slate-200"
			>
				{col}
				<button
					type="button"
					onclick={() => remove(col)}
					class="p-0.5 rounded-full hover:bg-rose-950/50 hover:text-rose-400 text-slate-500 transition-colors"
				>
					<Trash2 size={10} />
				</button>
			</span>
		{/each}
	</div>

	<div class="flex gap-2">
		<input
			type="text"
			bind:value={newColumn}
			placeholder="Add column (e.g. status)"
			onkeydown={(e) => e.key === 'Enter' && add()}
			class="flex-1 px-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orbit-cyan/60 font-mono"
		/>
		<button
			type="button"
			onclick={add}
			class="p-1.5 rounded-lg bg-surface-800 hover:bg-orbit-cyan/20 border border-white/10 hover:border-orbit-cyan/40 text-slate-300 hover:text-orbit-cyan transition-colors"
		>
			<Plus size={14} />
		</button>
	</div>
</section>
