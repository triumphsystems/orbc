<script lang="ts">
	import { GitBranch, Play, RefreshCw, CheckCircle2, RotateCw } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		onDeploy: () => void;
		onReset: () => void;
		onSyncTopology?: () => void;
		deploying?: boolean;
		deployed?: boolean;
		syncing?: boolean;
	}

	let {
		onDeploy,
		onReset,
		onSyncTopology,
		deploying = false,
		deployed = false,
		syncing = false
	}: Props = $props();
</script>

<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
	<div class="hidden sm:block">
		<h1 class="text-xl sm:text-2xl font-bold text-slate-100 flex items-center gap-2 font-display">
			<GitBranch size={22} class="text-orbit-cyan" />
			<span>Pipeline Studio</span>
		</h1>
		<p class="text-xs text-slate-400 font-sans mt-0.5">
			Orchestrate source discovery, LLM schema extraction, databases, S3 storage, and notifications.
		</p>
	</div>

	<div class="flex items-center gap-2 w-full sm:w-auto">
		{#if onSyncTopology}
			<Button
				variant="secondary"
				size="sm"
				loading={syncing}
				onclick={onSyncTopology}
				title="Fetch live adapter configurations from backend"
				class="flex-1 sm:flex-initial justify-center px-2.5 sm:px-3 text-xs"
			>
				<RotateCw size={13} class="text-orbit-cyan" />
				<span class="sm:hidden">Sync</span>
				<span class="hidden sm:inline">Sync Active Topology</span>
			</Button>
		{/if}

		<Button
			variant="secondary"
			size="sm"
			onclick={onReset}
			title="Reset to empty pipeline canvas"
			class="flex-1 sm:flex-initial justify-center px-2.5 sm:px-3 text-xs"
		>
			<RefreshCw size={13} />
			<span>Reset</span>
		</Button>

		<Button
			variant={deployed ? 'secondary' : 'primary'}
			size="sm"
			loading={deploying}
			disabled={deploying}
			onclick={onDeploy}
			class="flex-1 sm:flex-initial justify-center px-2.5 sm:px-3 text-xs {deployed
				? 'border-emerald-500/40 text-emerald-300 bg-emerald-950/30'
				: ''}"
		>
			{#if deployed}
				<CheckCircle2 size={14} class="text-emerald-400" />
				<span class="sm:hidden">Deployed!</span>
				<span class="hidden sm:inline">Pipeline Deployed!</span>
			{:else}
				<Play size={14} />
				<span class="sm:hidden">Deploy</span>
				<span class="hidden sm:inline">Deploy Pipeline</span>
			{/if}
		</Button>
	</div>
</div>
