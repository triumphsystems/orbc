<script lang="ts">
	import { Play, Trash2 } from '@lucide/svelte';
	import type { AutomationOut } from '$lib/api/types';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		automation: AutomationOut;
		running?: boolean;
		onRun: (id: string) => void;
		onDelete: (id: string) => void;
	}

	let { automation, running = false, onRun, onDelete }: Props = $props();
</script>

<div
	class="bg-surface-900 border border-white/10 rounded-xl p-4 space-y-3 hover:border-white/20 transition-colors shadow-lg"
>
	<div class="flex items-center justify-between gap-2">
		<div class="flex items-center gap-2 min-w-0">
			<StatusBadge
				status={automation.active ? 'success' : 'paused'}
				label={automation.active ? 'ACTIVE' : 'PAUSED'}
			/>
			<span
				class="px-2 py-0.5 rounded text-[10px] uppercase font-mono bg-surface-800 text-orbit-violet border border-orbit-violet/30 truncate max-w-[110px]"
			>
				{automation.plan?.domain || 'GENERAL'}
			</span>
		</div>
		<span class="text-[11px] font-mono uppercase text-slate-400 shrink-0">
			{automation.plan?.frequency}
		</span>
	</div>

	<div class="min-w-0 space-y-1">
		<a
			href={`/automations/${automation.id}`}
			class="font-medium text-sm text-slate-100 hover:text-orbit-cyan truncate block transition-colors"
			title={automation.plan?.objective || automation.raw_goal}
		>
			{automation.plan?.objective || automation.raw_goal}
		</a>
		<p class="text-xs text-slate-400 font-mono truncate" title={automation.raw_goal}>
			"{automation.raw_goal}"
		</p>
	</div>

	<div class="flex items-center justify-between pt-2.5 border-t border-white/5 text-xs">
		<span class="text-[11px] font-mono text-slate-500">
			{new Date(automation.created_at).toLocaleDateString()}
		</span>
		<div class="flex items-center gap-2">
			<Button variant="primary" size="sm" onclick={() => onRun(automation.id)} loading={running}>
				<Play size={12} />
				<span>Run</span>
			</Button>
			<button
				type="button"
				onclick={() => onDelete(automation.id)}
				class="p-1.5 text-slate-500 hover:text-rose-400 rounded hover:bg-rose-950/40 transition-colors"
				title="Delete automation"
			>
				<Trash2 size={14} />
			</button>
		</div>
	</div>
</div>
