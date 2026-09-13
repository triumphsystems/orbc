<script lang="ts">
	import {
		ShieldCheck,
		Download,
		ExternalLink,
		ZoomIn,
		ZoomOut,
		Maximize2,
		FileText,
		CheckCircle2
	} from '@lucide/svelte';
	import { PUBLIC_API_URL } from '$env/static/public';
	import type { RunOut } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		run: RunOut;
	}

	let { run }: Props = $props();
	let zoomLevel = $state(100);
	let showRedactionHighlights = $state(true);

	const apiBase = PUBLIC_API_URL || 'http://localhost:8000/api/v1';
	const reportUrl = $derived(`${apiBase.replace(/\/+$/, '')}/runs/${run.id}/dossier`);
</script>

<div class="bg-surface-900 border border-white/10 rounded-2xl overflow-hidden shadow-2xl space-y-0">
	<!-- Viewer Top Toolbar -->
	<div
		class="px-4 py-3 bg-surface-950/80 border-b border-white/10 flex flex-wrap items-center justify-between gap-3"
	>
		<div class="flex items-center gap-3">
			<div class="flex items-center gap-2 text-xs font-semibold text-slate-200 font-mono">
				<FileText size={15} class="text-orbit-cyan" />
				<span>Report Dossier Preview</span>
			</div>
			<div
				class="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 text-[10px] font-mono"
			>
				<ShieldCheck size={12} />
				<span>Compliance PII Redacted</span>
			</div>
		</div>

		<div class="flex items-center gap-2 font-mono text-xs">
			<div
				class="flex items-center bg-surface-800 border border-white/10 rounded-lg p-0.5 text-slate-300"
			>
				<button
					type="button"
					onclick={() => (zoomLevel = Math.max(50, zoomLevel - 15))}
					class="p-1 hover:text-white"
					title="Zoom Out"
				>
					<ZoomOut size={13} />
				</button>
				<span class="px-2 text-[10px] text-slate-400">{zoomLevel}%</span>
				<button
					type="button"
					onclick={() => (zoomLevel = Math.min(200, zoomLevel + 15))}
					class="p-1 hover:text-white"
					title="Zoom In"
				>
					<ZoomIn size={13} />
				</button>
			</div>

			<a
				href={reportUrl}
				target="_blank"
				rel="noopener noreferrer"
				class="flex items-center gap-1 px-3 py-1 bg-surface-800 hover:bg-surface-700 border border-white/10 hover:border-white/20 text-slate-200 rounded-lg transition-colors"
			>
				<ExternalLink size={12} />
				<span>Open Tab</span>
			</a>
			<a
				href={reportUrl}
				download
				class="flex items-center gap-1 px-3 py-1 bg-orbit-cyan/10 hover:bg-orbit-cyan/20 border border-orbit-cyan/30 text-orbit-cyan rounded-lg transition-colors font-medium"
			>
				<Download size={12} />
				<span>Export Report</span>
			</a>
		</div>
	</div>

	<!-- Interactive Report Viewer Frame -->
	<div
		class="relative bg-surface-950 min-h-[580px] h-[580px] w-full flex items-center justify-center overflow-hidden"
	>
		<iframe
			src={reportUrl}
			title="Orbit Interactive Dossier Viewer"
			class="w-full h-full border-0 transition-transform duration-150 origin-top"
			style="transform: scale({zoomLevel / 100}); width: {10000 / zoomLevel}%; height: {10000 /
				zoomLevel}%;"
		></iframe>
	</div>

	<!-- Footer PII Audit Metadata -->
	<div
		class="px-4 py-2.5 bg-surface-950/60 border-t border-white/10 flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400"
	>
		<div class="flex items-center gap-2">
			<CheckCircle2 size={13} class="text-emerald-400" />
			<span>Automated Compliance Audit: SSN, Credit Cards & Emails masked prior to export.</span>
		</div>
		<span class="text-slate-500">Rendered via Document Intelligence Engine</span>
	</div>
</div>
