<script lang="ts">
	import TemplateCard from './TemplateCard.svelte';
	import type { TemplateOut } from '$lib/api/client';

	interface Props {
		templates: TemplateOut[];
		loading: boolean;
		onEdit: (t: TemplateOut) => void;
		onDelete: (id: string) => void;
		onPreview: (t: TemplateOut) => void;
		onNew: () => void;
	}

	let { templates, loading, onEdit, onDelete, onPreview, onNew }: Props = $props();
	const hasTemplates = $derived(templates.length > 0);
</script>

{#if loading && !hasTemplates}
	<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
		{#each Array(3) as _}
			<div
				class="bg-surface-900 border border-white/8 rounded-2xl p-4 animate-pulse space-y-3 h-44"
			>
				<div class="flex gap-3">
					<div class="w-10 h-10 rounded-lg bg-surface-800"></div>
					<div class="flex-1 space-y-2">
						<div class="h-3 bg-surface-800 rounded w-3/4"></div>
						<div class="h-2 bg-surface-800 rounded w-full"></div>
					</div>
				</div>
				<div class="h-2 bg-surface-800 rounded w-1/2"></div>
			</div>
		{/each}
	</div>
{:else if !hasTemplates}
	<div class="flex flex-col items-center justify-center py-20 gap-4 text-center">
		<div
			class="w-16 h-16 rounded-2xl bg-surface-900 border border-white/10 flex items-center justify-center"
		>
			<svg
				class="w-8 h-8 text-slate-600"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
				/>
			</svg>
		</div>
		<div>
			<p class="text-sm font-semibold text-slate-300 font-display">No templates yet</p>
			<p class="text-xs font-mono text-slate-500 mt-1">
				Create your first PDF report template to get started.
			</p>
		</div>
		<button
			type="button"
			onclick={onNew}
			class="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-semibold font-sans hover:from-cyan-400 hover:to-blue-500 transition-all"
		>
			Create Template
		</button>
	</div>
{:else}
	<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
		{#each templates as template (template.id)}
			<TemplateCard {template} {onEdit} {onDelete} {onPreview} />
		{/each}
	</div>
{/if}
