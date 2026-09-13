<script lang="ts">
	import { Star, Pencil, Trash2, Eye, FileText } from '@lucide/svelte';
	import type { TemplateOut } from '$lib/api/client';

	interface Props {
		template: TemplateOut;
		onEdit: (t: TemplateOut) => void;
		onDelete: (id: string) => void;
		onPreview: (t: TemplateOut) => void;
	}

	let { template, onEdit, onDelete, onPreview }: Props = $props();

	const formatColors: Record<string, string> = {
		pdf: 'bg-rose-950/40 text-rose-300 border-rose-500/20',
		html: 'bg-cyan-950/40 text-cyan-300 border-cyan-500/20',
		docx: 'bg-blue-950/40 text-blue-300 border-blue-500/20'
	};

	const themeColor = $derived(template.schema_definition?.theme_color as string | undefined);
	const updatedLabel = $derived(
		new Date(template.updated_at).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		})
	);
</script>

<div
	class="group relative bg-surface-900 border border-white/8 hover:border-orbit-cyan/40 rounded-2xl p-4 flex flex-col justify-between h-full transition-all shadow-lg hover:shadow-orbit-cyan/10"
>
	{#if template.is_default}
		<div class="absolute top-3 right-3" title="Default template">
			<Star size={13} class="text-amber-400 fill-amber-400" />
		</div>
	{/if}

	<div class="space-y-3">
		<!-- Header & Description -->
		<div class="flex items-start gap-3">
			<div class="p-2 rounded-lg bg-surface-800 border border-white/5 text-orbit-cyan shrink-0">
				<FileText size={18} />
			</div>
			<div class="min-w-0 flex-1 pr-4">
				<div class="flex items-center gap-2 flex-wrap">
					<span class="text-sm font-semibold text-slate-100 truncate font-display"
						>{template.name}</span
					>
					<span
						class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border {formatColors[
							template.format
						] ?? formatColors.pdf}"
					>
						{template.format.toUpperCase()}
					</span>
				</div>
				<p class="text-[11px] font-sans text-slate-400 mt-1 line-clamp-2">
					{template.description || 'Structured visual layout for automated extraction dossiers.'}
				</p>
			</div>
		</div>

		<!-- Columns / Schema Preview -->
		{#if (template.schema_definition?.columns as string[] | undefined)?.length}
			<div class="flex items-center gap-1.5 flex-wrap">
				{#each ((template.schema_definition?.columns as string[]) || []).slice(0, 3) as col}
					<span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-surface-800/80 border border-white/5 text-slate-300">
						{col}
					</span>
				{/each}
				{#if ((template.schema_definition?.columns as string[]) || []).length > 3}
					<span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-surface-800/40 text-slate-500">
						+{((template.schema_definition?.columns as string[]) || []).length - 3} more
					</span>
				{/if}
			</div>
		{/if}

		<!-- Metadata & Theme Badges -->
		<div class="flex items-center gap-2 flex-wrap text-[10px] font-mono text-slate-400">
			{#if themeColor}
				<span class="flex items-center gap-1 px-2 py-0.5 rounded bg-surface-800 border border-white/5">
					<span class="w-2 h-2 rounded-full" style="background:{themeColor}"></span>Themed
				</span>
			{/if}
			{#if template.schema_definition?.show_summary !== false}
				<span class="px-2 py-0.5 rounded bg-surface-800 border border-white/5">Summary block</span>
			{/if}
			<span class="text-slate-500 ml-auto">Updated {updatedLabel}</span>
		</div>
	</div>

	<!-- Action Controls: Always visible with hover enhancement -->
	<div class="pt-3 mt-3 border-t border-white/8 flex items-center gap-1.5">
		<button
			type="button"
			onclick={() => onPreview(template)}
			class="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-[11px] font-mono rounded-lg bg-surface-800 hover:bg-surface-700 border border-white/5 hover:border-orbit-cyan/30 text-slate-300 hover:text-orbit-cyan transition-colors"
		>
			<Eye size={12} />Preview
		</button>
		<button
			type="button"
			onclick={() => onEdit(template)}
			class="flex-1 flex items-center justify-center gap-1.5 py-1.5 text-[11px] font-mono rounded-lg bg-surface-800 hover:bg-surface-700 border border-white/5 hover:border-white/20 text-slate-300 hover:text-white transition-colors"
		>
			<Pencil size={12} />Edit
		</button>
		<button
			type="button"
			onclick={() => onDelete(template.id)}
			class="p-1.5 rounded-lg bg-surface-800 hover:bg-rose-950/50 border border-white/5 text-slate-400 hover:text-rose-400 hover:border-rose-500/30 transition-colors"
			title="Delete template"
		>
			<Trash2 size={12} />
		</button>
	</div>
</div>
