<script lang="ts">
	import { X, RefreshCw, ExternalLink } from '@lucide/svelte';
	import { api } from '$lib/api/client';
	import type { TemplateOut } from '$lib/api/client';

	interface Props {
		template: TemplateOut | null;
		onClose: () => void;
	}
	let { template, onClose }: Props = $props();

	let htmlContent = $state<string | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let iframeEl = $state<HTMLIFrameElement | null>(null);

	const sampleSources = [
		'https://arxiv.org/html/2601.13243v1',
		'https://www.researchgate.net/publication/394100858',
		'https://grants.nih.gov/funding/search'
	];

	const sampleData = [
		{ source_url: 'https://arxiv.org/html/2601.13243v1', title: 'Research Grant Alpha', amount: '$48,500', deadline: '2026-11-30', status: 'open' },
		{ source_url: 'https://www.researchgate.net/publication/394100858', title: 'Fellowship Program B', amount: '$12,000', deadline: '2026-10-15', status: 'verified' },
		{ source_url: 'https://grants.nih.gov/funding/search', title: 'Contract Award C', amount: '$210,000', deadline: '2026-09-30', status: 'open' }
	];

	async function loadPreview() {
		if (!template) return;
		loading = true;
		error = null;
		try {
			htmlContent = await api.previewTemplate(
				template.schema_definition,
				sampleData,
				template.schema_definition?.title || template.name,
				sampleSources
			);
		} catch (e: any) {
			error = e.message || 'Preview failed';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (template) loadPreview();
	});

	$effect(() => {
		if (htmlContent && iframeEl) {
			const doc = iframeEl.contentDocument || iframeEl.contentWindow?.document;
			if (doc) {
				doc.open();
				doc.write(htmlContent);
				doc.close();
			}
		}
	});
</script>

{#if template}
	<div
		class="fixed inset-0 bg-void/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
		role="dialog"
		aria-modal="true"
		aria-label="Template Preview"
	>
		<div
			class="w-full max-w-4xl bg-surface-900 border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden h-[85vh] max-h-[820px]"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-5 py-3.5 border-b border-white/10 shrink-0">
				<div class="flex items-center gap-2">
					<span class="text-sm font-bold text-white font-display truncate">{template.name}</span>
					<span
						class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-surface-800 border border-white/10 text-slate-400"
						>{template.format.toUpperCase()} Preview</span
					>
				</div>
				<div class="flex items-center gap-2">
					<button
						type="button"
						onclick={loadPreview}
						disabled={loading}
						class="p-1.5 rounded-lg text-slate-400 hover:text-orbit-cyan hover:bg-surface-800 transition-colors disabled:opacity-50"
						title="Refresh preview"
					>
						<RefreshCw size={14} class={loading ? 'animate-spin' : ''} />
					</button>
					<button
						type="button"
						onclick={onClose}
						class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
					>
						<X size={16} />
					</button>
				</div>
			</div>

			<!-- Preview Body -->
			<div class="flex-1 w-full relative overflow-hidden bg-surface-950 min-h-[350px]">
				{#if loading}
					<div
						class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface-950/60 z-10"
					>
						<RefreshCw size={24} class="text-orbit-cyan animate-spin" />
						<span class="text-xs font-mono text-slate-400">Rendering preview…</span>
					</div>
				{:else if error}
					<div class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center p-6 z-10">
						<p class="text-sm font-mono text-rose-400">{error}</p>
						<button
							type="button"
							onclick={loadPreview}
							class="text-xs font-mono text-orbit-cyan hover:underline">Retry</button
						>
					</div>
				{:else}
					<iframe
						bind:this={iframeEl}
						title="Template Preview"
						class="absolute inset-0 w-full h-full border-0 bg-transparent"
						sandbox="allow-same-origin"
					></iframe>
				{/if}
			</div>

			<!-- Footer -->
			<div class="px-5 py-2.5 border-t border-white/10 flex items-center gap-2 shrink-0">
				<ExternalLink size={11} class="text-slate-600" />
				<span class="text-[10px] font-mono text-slate-500"
					>Live preview uses sample data — actual dossiers render with mission extraction results.</span
				>
			</div>
		</div>
	</div>
{/if}
