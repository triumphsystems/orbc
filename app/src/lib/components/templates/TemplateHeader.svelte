<script lang="ts">
	import { FileText, Plus, RefreshCw } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		loading?: boolean;
		onNew: () => void;
		onRefresh: () => void;
	}

	let { loading = false, onNew, onRefresh }: Props = $props();
</script>

<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
	<div class="hidden sm:block">
		<h1 class="text-xl sm:text-2xl font-bold text-slate-100 flex items-center gap-2 font-display">
			<FileText size={22} class="text-orbit-cyan" />
			<span>Template Studio</span>
		</h1>
		<p class="text-xs text-slate-400 font-sans mt-0.5">
			Design visual PDF/HTML report templates and apply them to mission dossier generation.
		</p>
	</div>

	<div class="flex items-center gap-2 w-full sm:w-auto">
		<Button
			variant="secondary"
			size="sm"
			{loading}
			onclick={onRefresh}
			class="flex-1 sm:flex-initial justify-center px-2.5 sm:px-3 text-xs"
			title="Refresh templates"
		>
			<RefreshCw size={13} class="text-orbit-cyan" />
			<span class="hidden sm:inline">Refresh</span>
		</Button>
		<Button
			variant="primary"
			size="sm"
			onclick={onNew}
			class="flex-1 sm:flex-initial justify-center px-2.5 sm:px-3 text-xs"
		>
			<Plus size={14} />
			<span>New Template</span>
		</Button>
	</div>
</div>
