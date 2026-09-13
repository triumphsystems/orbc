<script lang="ts">
	import { CheckCircle2, X } from '@lucide/svelte';

	interface Props {
		message: string | null;
		onDismiss: () => void;
	}

	let { message, onDismiss }: Props = $props();
</script>

{#if message}
	<div
		class="p-3 rounded-xl border bg-emerald-950/40 border-emerald-500/30 text-emerald-300 flex items-center justify-between text-xs font-mono animate-in fade-in duration-200"
	>
		<div class="flex items-center gap-2">
			<CheckCircle2 size={15} class="text-emerald-400 shrink-0" />
			<span>{message}</span>
		</div>
		<button
			type="button"
			onclick={onDismiss}
			class="text-slate-400 hover:text-white transition-colors"
			title="Dismiss"
		>
			<X size={14} />
		</button>
	</div>
{/if}
