<script lang="ts">
	import {
		Sparkles,
		ArrowRight,
		Plus,
		Cpu,
		FileText,
		DollarSign,
		Database,
		Activity
	} from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';

	interface Props {
		onSubmit: (goal: string) => void;
		loading?: boolean;
		placeholder?: string;
	}

	let {
		onSubmit,
		loading = false,
		placeholder = 'Describe your web data objective — e.g. Track GPU pricing across cloud providers every 6h and sync to DB...'
	}: Props = $props();

	let goalText = $state('');

	const promptPills = [
		{
			label: 'Cloud GPU & Compute Pricing',
			icon: Cpu,
			goal: 'Every 6 hours, track on-demand and spot pricing for H100, A100, and RTX 4090 GPUs across RunPod, Lambda Labs, CoreWeave, and AWS'
		},
		{
			label: 'AI Model Leaderboards',
			icon: Sparkles,
			goal: 'Daily, monitor LMSYS Chatbot Arena and OpenRouter leaderboards for new LLM releases, benchmark scores, and pricing per million tokens'
		},
		{
			label: 'ML Datasets & Benchmarks',
			icon: Database,
			goal: 'Weekly, track and extract open-source instruction-tuning datasets and evaluation benchmarks from HuggingFace and PapersWithCode with license types and token counts'
		},
		{
			label: 'arXiv Research Preprints',
			icon: FileText,
			goal: 'Daily at 6 AM, extract newly published arXiv preprints on LLM reasoning and agent evaluation with author affiliations and GitHub repo links'
		},
		{
			label: 'Staff AI Engineer Salaries',
			icon: DollarSign,
			goal: 'Weekly on Monday, aggregate verified Staff and Senior AI engineer compensation bands, base/equity splits, and level distributions across Tier 1 tech firms'
		},
		{
			label: 'Cloud & API Status',
			icon: Activity,
			goal: 'Every 15 minutes, monitor status pages and incident disclosures across major cloud and AI API providers, alerting on service degradation'
		}
	];

	function handleSubmit(e?: Event) {
		e?.preventDefault();
		if (!goalText.trim() || loading) return;
		onSubmit(goalText.trim());
	}

	function selectPill(goal: string) {
		goalText = goal;
	}
</script>

<div class="w-full space-y-4">
	<!-- Heroic Web Data Prompt Card -->
	<form onsubmit={handleSubmit} class="relative group">
		<!-- Subtle ambient glow on hover/focus -->
		<div
			class="absolute -inset-1 bg-gradient-to-r from-orbit-cyan/20 via-sky-500/15 to-emerald-500/20 rounded-3xl opacity-30 group-focus-within:opacity-75 blur-md transition-all duration-300 pointer-events-none"
		></div>

		<div
			class="relative bg-surface-900 border border-white/10 group-focus-within:border-orbit-cyan/40 rounded-2xl p-4 md:p-5 shadow-2xl transition-colors space-y-3"
		>
			{#if loading && orbitStore.goalReasoningStage}
				<div
					class="px-3 py-1.5 rounded-lg bg-orbit-cyan/10 border border-orbit-cyan/30 text-orbit-cyan text-xs font-mono flex items-center gap-2 animate-in fade-in duration-200"
				>
					<Sparkles size={13} class="animate-spin text-orbit-cyan shrink-0" />
					<span class="truncate">{orbitStore.goalReasoningStage.message}</span>
				</div>
			{/if}

			<div class="flex items-start gap-3">
				<textarea
					bind:value={goalText}
					{placeholder}
					disabled={loading}
					rows="3"
					class="w-full bg-transparent text-sm md:text-base text-slate-100 placeholder-slate-500 focus:outline-none resize-none font-sans leading-relaxed"
					onkeydown={(e) => {
						if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
							handleSubmit();
						}
					}}
				></textarea>
			</div>

			<!-- Bottom Toolbar in Prompt Box -->
			<div class="flex items-center justify-between gap-2 pt-3 border-t border-white/5">
				<div class="flex items-center gap-2">
					<button
						type="button"
						onclick={() => (goalText = goalText ? `${goalText} (country: Nigeria)` : 'Track ')}
						class="inline-flex items-center gap-1.5 px-2.5 md:px-3 py-1 rounded-lg bg-surface-800 hover:bg-surface-700 border border-white/5 text-xs text-slate-300 hover:text-white transition-colors font-sans"
						title="Add country, domain, or website context"
					>
						<Plus size={13} class="text-orbit-cyan" />
						<span>Add context</span>
					</button>

					<span class="text-[11px] font-mono text-slate-500 hidden md:inline">
						Press <kbd
							class="px-1.5 py-0.5 rounded bg-surface-800 text-slate-400 border border-white/10 text-[10px]"
							>Ctrl+Enter</kbd
						> to run
					</span>
				</div>

				<Button
					type="submit"
					variant="primary"
					size="md"
					{loading}
					disabled={!goalText.trim()}
					class="shrink-0 font-medium py-1.5 px-3 md:py-2 md:px-4 text-xs md:text-sm"
				>
					<Sparkles size={14} />
					<span class="inline md:hidden">Start</span>
					<span class="hidden md:inline">Start Mission</span>
					<ArrowRight size={14} class="hidden md:inline" />
				</Button>
			</div>
		</div>
	</form>

	<!-- Quick Examples for Data & Engineering Teams -->
	<div class="space-y-2">
		<div class="flex items-center gap-1.5 text-xs text-slate-400 px-1 font-mono">
			<span>Examples:</span>
		</div>
		<div class="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none -mx-1 px-1">
			{#each promptPills as pill}
				<button
					type="button"
					onclick={() => selectPill(pill.goal)}
					class="inline-flex items-center gap-1.5 md:gap-2 px-3 md:px-3.5 py-1.5 rounded-full bg-surface-900/80 hover:bg-surface-800 border border-white/10 hover:border-orbit-cyan/40 text-xs text-slate-300 hover:text-slate-100 transition-all shrink-0 font-sans shadow-sm active:scale-95 whitespace-nowrap"
				>
					<pill.icon size={13} class="text-orbit-cyan shrink-0" />
					<span>{pill.label}</span>
				</button>
			{/each}
		</div>
	</div>
</div>
