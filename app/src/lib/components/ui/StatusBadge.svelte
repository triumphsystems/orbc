<script lang="ts">
	import { CheckCircle2, AlertTriangle, XCircle, Clock, PauseCircle, Play } from '@lucide/svelte';

	interface Props {
		status:
			| 'completed'
			| 'success'
			| 'running'
			| 'warning'
			| 'error'
			| 'failed'
			| 'paused'
			| 'pending'
			| string;
		label?: string;
		showIcon?: boolean;
		size?: 'sm' | 'md';
		pulse?: boolean;
	}

	let { status, label, showIcon = true, size = 'sm', pulse = false }: Props = $props();

	const normalizedStatus = $derived(
		['success', 'completed'].includes(status)
			? 'success'
			: ['running'].includes(status)
				? 'running'
				: ['warning', 'partial'].includes(status)
					? 'warning'
					: ['error', 'failed'].includes(status)
						? 'error'
						: ['paused'].includes(status)
							? 'paused'
							: 'pending'
	);

	const displayText = $derived(label || status.toUpperCase());

	const statusClasses = {
		success: 'bg-emerald-950/50 text-emerald-400 border-emerald-500/30 shadow-glow-emerald/20',
		running: 'bg-cyan-950/60 text-orbit-cyan border-cyan-500/40 shadow-glow-cyan/30',
		warning: 'bg-amber-950/50 text-amber-400 border-amber-500/30 shadow-glow-amber/20',
		error: 'bg-rose-950/50 text-rose-400 border-rose-500/30',
		paused: 'bg-slate-800/60 text-slate-400 border-slate-600/30',
		pending: 'bg-surface-700/60 text-slate-300 border-white/10'
	};

	const sizeClasses = {
		sm: 'px-2 py-0.5 text-xs gap-1.5',
		md: 'px-3 py-1 text-sm gap-2'
	};
</script>

<span
	class="inline-flex items-center font-mono font-medium rounded-full border backdrop-blur-md transition-all duration-150 {statusClasses[
		normalizedStatus
	]} {sizeClasses[size]} {pulse || normalizedStatus === 'running' ? 'animate-pulse' : ''}"
>
	{#if showIcon}
		{#if normalizedStatus === 'success'}
			<CheckCircle2 size={size === 'sm' ? 12 : 14} strokeWidth={2} />
		{:else if normalizedStatus === 'running'}
			<Clock size={size === 'sm' ? 12 : 14} strokeWidth={2} class="animate-spin" />
		{:else if normalizedStatus === 'warning'}
			<AlertTriangle size={size === 'sm' ? 12 : 14} strokeWidth={2} />
		{:else if normalizedStatus === 'error'}
			<XCircle size={size === 'sm' ? 12 : 14} strokeWidth={2} />
		{:else if normalizedStatus === 'paused'}
			<PauseCircle size={size === 'sm' ? 12 : 14} strokeWidth={2} />
		{:else}
			<Play size={size === 'sm' ? 10 : 12} strokeWidth={2} />
		{/if}
	{/if}
	<span>{displayText}</span>
</span>
