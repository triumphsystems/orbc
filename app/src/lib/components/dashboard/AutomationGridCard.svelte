<script lang="ts">
	import { Play, ArrowRight } from '@lucide/svelte';
	import type { AutomationOut } from '$lib/api/types';
	import Card from '$lib/components/ui/Card.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		automation: AutomationOut;
		running?: boolean;
		onRun: (id: string) => void;
	}

	let { automation, running = false, onRun }: Props = $props();
</script>

<Card class="flex flex-col justify-between space-y-3 hover:border-white/20 transition-all">
	<div class="space-y-2">
		<div class="flex items-center justify-between gap-2">
			<span
				class="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-surface-800 text-orbit-violet border border-orbit-violet/20"
			>
				{automation.plan?.domain || 'GENERAL'}
			</span>
			<StatusBadge
				status={automation.active ? 'success' : 'paused'}
				label={automation.active ? 'ACTIVE' : 'PAUSED'}
			/>
		</div>
		<h3 class="text-sm font-medium text-slate-100 leading-snug line-clamp-2">
			{automation.plan?.objective || automation.raw_goal}
		</h3>
		<p class="text-[11px] text-slate-500">
			<span class="uppercase font-semibold text-slate-400">{automation.plan?.frequency}</span>
			{#if automation.plan?.schedule_time}
				<span class="font-mono"> · {automation.plan.schedule_time}</span>
			{/if}
		</p>
	</div>

	<div class="flex items-center justify-between border-t border-white/5 pt-3">
		<a
			href={`/automations/${automation.id}`}
			class="text-xs font-medium text-slate-400 hover:text-white transition-colors flex items-center gap-1"
		>
			<span>Inspect</span>
			<ArrowRight size={11} />
		</a>

		<Button variant="primary" size="sm" loading={running} onclick={() => onRun(automation.id)}>
			<Play size={12} />
			<span>Run now</span>
		</Button>
	</div>
</Card>
