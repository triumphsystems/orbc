<script lang="ts">
	import { ArrowLeft, Terminal, RefreshCw, Play } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		automationId?: string;
		loading: boolean;
		rerunning?: boolean;
		onRefresh: () => void;
		onOpenLogs: () => void;
		onRerun?: () => void;
	}

	let {
		automationId,
		loading,
		rerunning = false,
		onRefresh,
		onOpenLogs,
		onRerun
	}: Props = $props();
</script>

<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
	<a
		href={automationId ? `/automations/${automationId}` : '/automations'}
		class="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-orbit-cyan transition-colors"
	>
		<ArrowLeft size={14} />
		<span>Back to Automation Mission</span>
	</a>

	<div class="flex items-center gap-2 self-end sm:self-auto flex-wrap">
		<Button variant="secondary" size="sm" onclick={onRefresh}>
			<RefreshCw size={13} class={loading ? 'animate-spin' : ''} />
			<span>Refresh</span>
		</Button>
		<Button variant="outline" size="sm" onclick={onOpenLogs}>
			<Terminal size={13} />
			<span>Audit Logs</span>
		</Button>
		{#if onRerun}
			<Button
				variant="primary"
				size="sm"
				loading={rerunning}
				disabled={!automationId}
				onclick={onRerun}
			>
				<Play size={13} />
				<span>Rerun</span>
			</Button>
		{/if}
	</div>
</div>
