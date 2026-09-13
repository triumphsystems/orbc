<script lang="ts">
	import {
		CheckCircle2,
		Clock,
		BrainCircuit,
		Search,
		Globe,
		Database,
		ShieldCheck,
		Bell
	} from '@lucide/svelte';
	import type { RunOut } from '$lib/api/types';

	interface Props {
		run: RunOut;
	}

	let { run }: Props = $props();

	const steps = $derived([
		{
			title: 'Goal & Schema',
			icon: BrainCircuit,
			done: true,
			active: false,
			meta: 'Ready'
		},
		{
			title: 'Discovery',
			icon: Search,
			done: (run.sources_found?.length ?? 0) > 0,
			active: run.status === 'discovering' || run.status === 'pending',
			meta: `${run.sources_found?.length || 0} sources`
		},
		{
			title: 'Retrieval',
			icon: Globe,
			done: (run.pages_retrieved?.length ?? 0) > 0,
			active: run.status === 'retrieving',
			meta: `${run.pages_retrieved?.length || 0} pages`
		},
		{
			title: 'Extraction',
			icon: Database,
			done: (run.extracted_count ?? 0) > 0,
			active: run.status === 'extracting',
			meta: `${run.extracted_count || 0} records`
		},
		{
			title: 'Verification',
			icon: ShieldCheck,
			done: (run.validated_count ?? 0) > 0,
			active: run.status === 'validating',
			meta: `${run.validated_count || 0} valid`
		},
		{
			title: 'Sinks & Alerts',
			icon: Bell,
			done: run.status === 'completed' || run.status === 'verified',
			active: run.status === 'evaluating' || run.status === 'storing',
			meta: run.condition_matched ? 'Triggered' : 'Evaluated'
		}
	]);
</script>

<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
	{#each steps as step}
		<div
			class="p-3 rounded-xl border transition-all text-left flex flex-col justify-between space-y-2 {step.done
				? 'bg-emerald-950/20 border-emerald-500/30'
				: step.active
					? 'bg-surface-850 border-orbit-cyan/60 animate-pulse shadow-glow-cyan/20'
					: 'bg-surface-900/60 border-white/5 opacity-60'}"
		>
			<div class="flex items-center justify-between">
				<div class="p-1.5 rounded-lg bg-surface-800 text-slate-300">
					<step.icon
						size={14}
						class={step.done
							? 'text-emerald-400'
							: step.active
								? 'text-orbit-cyan'
								: 'text-slate-500'}
					/>
				</div>
				{#if step.done}
					<CheckCircle2 size={14} class="text-emerald-400" />
				{:else if step.active}
					<Clock size={14} class="text-orbit-cyan animate-spin" />
				{:else}
					<span class="w-2 h-2 rounded-full bg-slate-700"></span>
				{/if}
			</div>

			<div>
				<div class="text-[11px] font-semibold text-slate-100 truncate">{step.title}</div>
				<div class="text-[10px] font-mono text-slate-400 truncate">{step.meta}</div>
			</div>
		</div>
	{/each}
</div>
