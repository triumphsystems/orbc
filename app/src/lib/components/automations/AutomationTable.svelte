<script lang="ts">
	import { Play, Trash2 } from '@lucide/svelte';
	import type { AutomationOut } from '$lib/api/types';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		automations: AutomationOut[];
		runningAutomationId?: string | null;
		onRun: (id: string) => void;
		onDelete: (id: string) => void;
	}

	let { automations, runningAutomationId = null, onRun, onDelete }: Props = $props();
</script>

<div class="border border-white/10 rounded-xl overflow-hidden bg-surface-900 shadow-2xl">
	<div class="overflow-x-auto">
		<table class="w-full text-left border-collapse font-sans text-xs">
			<thead
				class="bg-surface-850 border-b border-white/10 text-[11px] font-mono uppercase text-slate-400 tracking-wider"
			>
				<tr>
					<th class="py-3 px-4">Status</th>
					<th class="py-3 px-4">Domain</th>
					<th class="py-3 px-4">Objective & Goal</th>
					<th class="py-3 px-4">Cadence</th>
					<th class="py-3 px-4">Created</th>
					<th class="py-3 px-4 text-right">Actions</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-white/5 font-mono">
				{#each automations as auto}
					<tr class="hover:bg-surface-800/60 transition-colors">
						<td class="py-3 px-4">
							<StatusBadge
								status={auto.active ? 'success' : 'paused'}
								label={auto.active ? 'ACTIVE' : 'PAUSED'}
							/>
						</td>
						<td class="py-3 px-4">
							<span
								class="px-2 py-0.5 rounded text-[10px] uppercase bg-surface-800 text-orbit-violet border border-orbit-violet/30"
							>
								{auto.plan?.domain || 'GENERAL'}
							</span>
						</td>
						<td class="py-3 px-4 max-w-md font-sans">
							<a
								href={`/automations/${auto.id}`}
								class="font-medium text-slate-100 hover:text-orbit-cyan block"
							>
								{auto.plan?.objective || auto.raw_goal}
							</a>
							<span class="text-[11px] text-slate-400 font-mono line-clamp-1 mt-0.5"
								>"{auto.raw_goal}"</span
							>
						</td>
						<td class="py-3 px-4 text-slate-300">
							<span class="uppercase">{auto.plan?.frequency}</span>
							{#if auto.plan?.schedule_time}
								<span class="text-slate-500 text-[11px] block">{auto.plan.schedule_time}</span>
							{/if}
						</td>
						<td class="py-3 px-4 text-slate-500 text-[11px]">
							{new Date(auto.created_at).toLocaleDateString()}
						</td>
						<td class="py-3 px-4 text-right space-x-2">
							<Button
								variant="primary"
								size="sm"
								onclick={() => onRun(auto.id)}
								loading={runningAutomationId === auto.id}
							>
								<Play size={12} />
								<span>Run</span>
							</Button>
							<button
								type="button"
								onclick={() => onDelete(auto.id)}
								class="p-1.5 text-slate-500 hover:text-rose-400 rounded hover:bg-rose-950/40 transition-colors"
								title="Delete automation"
							>
								<Trash2 size={14} />
							</button>
						</td>
					</tr>
				{:else}
					<tr>
						<td colspan={6} class="py-12 text-center text-slate-500 font-mono">
							No matching automations found.
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
