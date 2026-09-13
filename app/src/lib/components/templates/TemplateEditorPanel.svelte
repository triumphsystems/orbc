<script lang="ts">
	import { X, Save } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import TemplateBasicFields from './TemplateBasicFields.svelte';
	import TemplateStyleFields from './TemplateStyleFields.svelte';
	import TemplateColumnEditor from './TemplateColumnEditor.svelte';
	import type { TemplateOut } from '$lib/api/client';

	interface Props {
		template: TemplateOut | null;
		saving?: boolean;
		saveError?: string | null;
		onClose: () => void;
		onSave: (payload: {
			name: string;
			description: string;
			format: string;
			schema_definition: Record<string, any>;
			is_default: boolean;
		}) => void;
	}

	let { template, saving = false, saveError = null, onClose, onSave }: Props = $props();

	let trackedId = $state<string | null>(null);
	let name = $state('');
	let description = $state('');
	let format = $state('pdf');
	let isDefault = $state(false);
	let themeColor = $state('#00F2FE');
	let bgColor = $state('#090d16');
	let textColor = $state('#e2e8f0');
	let showSummary = $state(true);
	let title = $state('Orbit Mission Intelligence Briefing');
	let columns = $state<string[]>(['title', 'amount', 'deadline', 'status']);

	$effect(() => {
		const id = template?.id ?? '__new__';
		if (id === trackedId) return;
		trackedId = id;
		const s = template?.schema_definition ?? {};
		name = template?.name ?? '';
		description = template?.description ?? '';
		format = template?.format ?? 'pdf';
		isDefault = template?.is_default ?? false;
		themeColor = (s.theme_color as string) ?? '#00F2FE';
		bgColor = (s.background_color as string) ?? '#090d16';
		textColor = (s.text_color as string) ?? '#e2e8f0';
		showSummary = s.show_summary !== false;
		title = (s.title as string) ?? 'Orbit Mission Intelligence Briefing';
		columns =
			Array.isArray(s.columns) && s.columns.length > 0
				? [...(s.columns as string[])]
				: ['title', 'amount', 'deadline', 'status'];
	});

	function handleSave() {
		onSave({
			name: name.trim(),
			description: description.trim(),
			format,
			is_default: isDefault,
			schema_definition: {
				title,
				theme_color: themeColor,
				background_color: bgColor,
				text_color: textColor,
				show_summary: showSummary,
				columns
			}
		});
	}

	const isNew = $derived(!template?.id);
</script>

<aside
	class="w-full lg:w-96 bg-surface-900 border border-white/10 rounded-2xl flex flex-col shadow-2xl shrink-0 max-h-[780px] overflow-hidden"
>
	<div class="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
		<span class="text-xs font-bold text-white uppercase tracking-wider font-mono"
			>{isNew ? 'New Template' : 'Edit Template'}</span
		>
		<button
			type="button"
			onclick={onClose}
			class="p-1 rounded text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
			><X size={14} /></button
		>
	</div>

	<div class="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
		<TemplateBasicFields
			{name}
			{description}
			{format}
			{isDefault}
			onName={(v) => (name = v)}
			onDescription={(v) => (description = v)}
			onFormat={(v) => (format = v)}
			onToggleDefault={() => (isDefault = !isDefault)}
		/>
		<TemplateStyleFields
			{title}
			{showSummary}
			{themeColor}
			{bgColor}
			{textColor}
			onTitle={(v) => (title = v)}
			onToggleSummary={() => (showSummary = !showSummary)}
			onThemeColor={(v) => (themeColor = v)}
			onBgColor={(v) => (bgColor = v)}
			onTextColor={(v) => (textColor = v)}
		/>
		<TemplateColumnEditor {columns} onChange={(cols) => (columns = cols)} />

		{#if saveError}
			<div
				class="px-3 py-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300 text-[11px] font-mono"
			>
				{saveError}
			</div>
		{/if}
	</div>

	<div class="px-4 py-3 border-t border-white/10 flex items-center justify-between gap-2 shrink-0">
		<Button variant="secondary" size="sm" onclick={onClose}>Cancel</Button>
		<Button
			variant="primary"
			size="sm"
			loading={saving}
			disabled={saving || !name.trim()}
			onclick={handleSave}
		>
			<Save size={12} /><span>{isNew ? 'Create Template' : 'Save Changes'}</span>
		</Button>
	</div>
</aside>
