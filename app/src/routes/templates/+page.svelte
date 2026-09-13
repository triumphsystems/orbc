<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';
	import type { TemplateOut } from '$lib/api/client';
	import TemplateHeader from '$lib/components/templates/TemplateHeader.svelte';
	import TemplateGrid from '$lib/components/templates/TemplateGrid.svelte';
	import TemplateEditorPanel from '$lib/components/templates/TemplateEditorPanel.svelte';
	import TemplatePreviewModal from '$lib/components/templates/TemplatePreviewModal.svelte';

	let templates = $state<TemplateOut[]>([]);
	let loading = $state(false);
	let loadError = $state<string | null>(null);
	let editorOpen = $state(false);
	let editingTemplate = $state<TemplateOut | null>(null);
	let saving = $state(false);
	let saveError = $state<string | null>(null);
	let previewTemplate = $state<TemplateOut | null>(null);
	let deleteConfirmId = $state<string | null>(null);

	async function loadTemplates() {
		loading = true;
		loadError = null;
		try {
			templates = await api.listTemplates();
		} catch (e: any) {
			loadError = e.message || 'Failed to load templates';
		} finally {
			loading = false;
		}
	}

	onMount(loadTemplates);

	function openNew() {
		editingTemplate = null;
		saveError = null;
		editorOpen = true;
	}
	function openEdit(t: TemplateOut) {
		editingTemplate = t;
		saveError = null;
		editorOpen = true;
	}
	function closeEditor() {
		editorOpen = false;
		editingTemplate = null;
		saveError = null;
	}

	async function handleSave(payload: {
		name: string;
		description: string;
		format: string;
		schema_definition: Record<string, any>;
		is_default: boolean;
	}) {
		if (!payload.name.trim()) {
			saveError = 'Template name is required.';
			return;
		}
		saving = true;
		saveError = null;
		try {
			if (editingTemplate) {
				const updated = await api.updateTemplate(editingTemplate.id, payload);
				templates = templates.map((t) => (t.id === updated.id ? updated : t));
			} else {
				const created = await api.createTemplate(payload);
				templates = [created, ...templates];
			}
			closeEditor();
		} catch (e: any) {
			saveError = e.message || 'Failed to save template';
		} finally {
			saving = false;
		}
	}

	async function handleDelete(id: string) {
		if (deleteConfirmId !== id) {
			deleteConfirmId = id;
			setTimeout(() => {
				if (deleteConfirmId === id) deleteConfirmId = null;
			}, 3000);
			return;
		}
		try {
			await api.deleteTemplate(id);
			templates = templates.filter((t) => t.id !== id);
			deleteConfirmId = null;
		} catch (e: any) {
			loadError = e.message || 'Failed to delete template';
		}
	}

	const defaultTemplate = $derived(templates.find((t) => t.is_default));
</script>

<div class="max-w-7xl mx-auto space-y-5">
	<TemplateHeader {loading} onNew={openNew} onRefresh={loadTemplates} />

	{#if loadError}
		<div
			class="px-4 py-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs font-mono"
		>
			{loadError}
		</div>
	{/if}

	{#if deleteConfirmId}
		<div
			class="px-4 py-3 rounded-xl bg-amber-950/40 border border-amber-500/30 text-amber-300 text-xs font-mono flex items-center gap-3"
		>
			<span>Click Delete again to confirm permanent removal.</span>
			<button
				type="button"
				onclick={() => (deleteConfirmId = null)}
				class="ml-auto text-amber-400 hover:underline">Cancel</button
			>
		</div>
	{/if}

	<div class="flex flex-col lg:flex-row items-start gap-5">
		<div class="flex-1 min-w-0">
			<TemplateGrid
				{templates}
				{loading}
				onEdit={openEdit}
				onDelete={handleDelete}
				onPreview={(t) => (previewTemplate = t)}
				onNew={openNew}
			/>
		</div>

		{#if editorOpen}
			<TemplateEditorPanel
				template={editingTemplate}
				{saving}
				{saveError}
				onClose={closeEditor}
				onSave={handleSave}
			/>
		{/if}
	</div>

	{#if defaultTemplate && !editorOpen}
		<div
			class="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-900 border border-amber-500/20 text-xs font-mono text-slate-400"
		>
			<svg class="w-3.5 h-3.5 text-amber-400 fill-amber-400 shrink-0" viewBox="0 0 24 24"
				><path
					d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
				/></svg
			>
			<span
				>Default template: <strong class="text-slate-200">{defaultTemplate.name}</strong> — applied automatically
				to all new mission dossiers.</span
			>
		</div>
	{/if}
</div>

<TemplatePreviewModal template={previewTemplate} onClose={() => (previewTemplate = null)} />
