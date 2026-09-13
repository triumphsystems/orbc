<script lang="ts">
	import { goto } from '$app/navigation';
	import { Layers, ArrowRight, Plus, Globe, CheckCircle2 } from '@lucide/svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';
	import GoalBar from '$lib/components/goals/GoalBar.svelte';
	import PlanPreviewCard from '$lib/components/goals/PlanPreviewCard.svelte';
	import AutomationGridCard from '$lib/components/dashboard/AutomationGridCard.svelte';
	import type { AutomationOut } from '$lib/api/types';

	let previewAutomation = $state<AutomationOut | null>(null);
	let runningId = $state<string | null>(null);

	async function handleGoalSubmit(goal: string) {
		const created = await orbitStore.createGoal(goal);
		if (created) {
			previewAutomation = created;
		}
	}

	async function handleRunNow(automationId: string) {
		runningId = automationId;
		try {
			const run = await orbitStore.triggerRun(automationId);
			if (run) {
				goto(`/runs/${run.id}`);
			}
		} finally {
			runningId = null;
		}
	}
</script>

<div
	class="max-w-5xl mx-auto flex flex-col justify-between min-h-[calc(100dvh-8rem)] md:min-h-0 md:block md:space-y-12 pb-2 md:pb-16"
>
	<!-- Hero Canvas (Vertically centered on mobile like Gemini, standard flow on desktop) -->
	<section
		class="flex-1 flex flex-col justify-center space-y-4 sm:space-y-6 md:space-y-8 py-2 md:py-12"
	>
		<!-- Heroic Overview Header (Dynamic 2-line viewport auto-fit) -->
		<div class="text-center space-y-2 md:space-y-3">
			<h1
				class="text-[clamp(1.45rem,6.6vw,2.15rem)] sm:text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight font-display text-center leading-[1.12]"
			>
				<span
					class="bg-gradient-to-r from-orbit-cyan via-sky-300 to-orbit-violet bg-clip-text text-transparent block whitespace-nowrap"
				>
					What web data operations
				</span>
				<span class="text-slate-100 block whitespace-nowrap mt-0.5 sm:mt-1 md:mt-2">
					do you want to automate?
				</span>
			</h1>
			<p class="hidden md:block text-sm text-slate-400 max-w-2xl mx-auto font-sans leading-relaxed">
				Define your objective in plain English. Orbit autonomously handles web discovery, structured
				extraction, anomaly validation, condition alerts, and downstream workflows.
			</p>
		</div>

		<!-- AI Prompt & Quick Suggestions Canvas -->
		<GoalBar onSubmit={handleGoalSubmit} loading={orbitStore.interpretingGoal} />
	</section>

	<!-- Dynamic Plan Preview Modal / Card -->
	{#if previewAutomation}
		<div class="space-y-3 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 my-2">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<span class="w-2 h-2 rounded-full bg-orbit-cyan animate-pulse"></span>
					<span class="text-xs font-semibold text-orbit-cyan uppercase tracking-wider font-mono"
						>Extraction Plan Ready</span
					>
				</div>
				<button
					type="button"
					onclick={() => (previewAutomation = null)}
					class="text-xs text-slate-500 hover:text-slate-300 transition-colors font-mono"
				>
					Dismiss
				</button>
			</div>
			<PlanPreviewCard
				automation={previewAutomation}
				onRunNow={handleRunNow}
				running={runningId === previewAutomation.id}
			/>
		</div>
	{/if}

	<!-- ── Mobile Web Monitors Redesign (Sleek Glass Fleet Bar / Carousel) ── -->
	<div class="block md:hidden shrink-0 pt-2">
		{#if orbitStore.automations.length === 0}
			<!-- Compact Mobile Fleet Status Bar (Replaces bulky dashed empty card) -->
			<a
				href="/automations"
				class="flex items-center justify-between p-3 rounded-xl bg-surface-900/80 border border-white/10 hover:border-orbit-cyan/30 transition-all active:scale-[0.99] group shadow-sm"
			>
				<div class="flex items-center gap-2.5">
					<div
						class="w-7 h-7 rounded-lg bg-surface-800 border border-white/5 flex items-center justify-center text-orbit-cyan shrink-0"
					>
						<Layers size={14} />
					</div>
					<div class="text-left">
						<div class="text-xs font-semibold text-slate-200">Active Web Monitors</div>
						<div class="text-[10px] font-mono text-slate-500">
							0 monitors • Fleet ready for missions
						</div>
					</div>
				</div>
				<div
					class="flex items-center gap-1 text-[11px] font-mono text-orbit-cyan group-hover:translate-x-0.5 transition-transform"
				>
					<span>Fleet</span>
					<ArrowRight size={11} />
				</div>
			</a>
		{:else}
			<!-- Mobile Horizontal Monitors Carousel -->
			<div class="space-y-2">
				<div class="flex items-center justify-between px-0.5">
					<div class="flex items-center gap-1.5 text-xs font-bold text-slate-100 font-display">
						<Layers size={14} class="text-orbit-cyan" />
						<span>Active Monitors</span>
						<span
							class="px-1.5 py-0.2 rounded-md bg-surface-800 border border-white/10 text-[10px] font-mono text-slate-400"
						>
							{orbitStore.automations.length}
						</span>
					</div>
					<a
						href="/automations"
						class="text-[11px] font-mono text-slate-400 hover:text-orbit-cyan flex items-center gap-0.5"
					>
						<span>View all</span>
						<ArrowRight size={11} />
					</a>
				</div>
				<div class="flex gap-2.5 overflow-x-auto pb-1 scrollbar-none -mx-1 px-1">
					{#each orbitStore.automations.slice(0, 4) as auto (auto.id)}
						<div class="min-w-[260px] max-w-[280px] shrink-0">
							<AutomationGridCard
								automation={auto}
								running={runningId === auto.id}
								onRun={handleRunNow}
							/>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- ── Desktop Web Monitors Fleet Grid (100% Preserved) ── -->
	<div class="hidden md:block space-y-4 pt-2">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2.5">
				<Layers size={16} class="text-orbit-cyan" />
				<h2 class="text-base font-bold text-slate-100 font-display">Active Web Monitors</h2>
				<span
					class="inline-flex items-center px-2 py-0.5 rounded-md bg-surface-800 border border-white/10 text-[11px] font-mono font-medium text-slate-400"
				>
					{orbitStore.automations.length}
				</span>
			</div>
			<a
				href="/automations"
				class="text-xs font-medium text-slate-400 hover:text-orbit-cyan transition-colors flex items-center gap-1 font-mono"
			>
				<span>View all monitors</span>
				<ArrowRight size={12} />
			</a>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
			{#each orbitStore.automations.slice(0, 6) as auto (auto.id)}
				<AutomationGridCard
					automation={auto}
					running={runningId === auto.id}
					onRun={handleRunNow}
				/>
			{:else}
				<div
					class="col-span-full border border-dashed border-white/10 rounded-2xl p-10 text-center space-y-3 bg-surface-900/40"
				>
					<div
						class="w-12 h-12 rounded-full bg-surface-800 border border-white/5 flex items-center justify-center mx-auto text-orbit-cyan"
					>
						<Globe size={22} />
					</div>
					<div>
						<p class="text-sm font-semibold text-slate-200">No active web monitors yet</p>
						<p class="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
							Type a data goal above or click a suggestion pill to start collecting web data
							hands-off.
						</p>
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>
