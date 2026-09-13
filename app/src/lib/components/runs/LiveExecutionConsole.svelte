<script lang="ts">
	import { Terminal, Copy, Check, ArrowDown } from '@lucide/svelte';
	import type { RunOut } from '$lib/api/types';

	interface Props {
		run: RunOut;
	}

	let { run }: Props = $props();
	let autoScroll = $state(true);
	let copied = $state(false);
	let consoleEl = $state<HTMLDivElement | null>(null);

	const logLines = $derived.by(() => {
		const lines: { time: string; tag: string; msg: string; type: string }[] = [];
		const start = run.started_at ? new Date(run.started_at).toLocaleTimeString() : '00:00:00';
		lines.push({
			time: start,
			tag: 'INIT',
			msg: `Initializing Orbit runner for run ${run.id}`,
			type: 'info'
		});
		lines.push({
			time: start,
			tag: 'PLAN',
			msg: `Loaded target execution plan for mission ${run.automation_id}`,
			type: 'info'
		});

		if (run.sources_found && run.sources_found.length > 0) {
			lines.push({
				time: start,
				tag: 'DISCOVERY',
				msg: `Discovered ${run.sources_found.length} candidate source URL(s)`,
				type: 'success'
			});
			run.sources_found.forEach((url) =>
				lines.push({ time: start, tag: 'SOURCE', msg: `-> ${url}`, type: 'dim' })
			);
		}
		if (run.pages_retrieved && run.pages_retrieved.length > 0) {
			lines.push({
				time: start,
				tag: 'RETRIEVAL',
				msg: `Retrieved ${run.pages_retrieved.length} pages via resilient web proxy`,
				type: 'info'
			});
		}
		if (run.reasoning_log) {
			run.reasoning_log.forEach((entry) => {
				const time = entry.timestamp || start;
				if (entry.decision) {
					const dec = entry.decision;
					lines.push({
						time,
						tag: 'HEALING',
						msg: `[Self-Correction] ${dec.diagnosis || 'Refining discovery'} — Action: ${dec.action || 'retry'}${dec.new_search_query ? ` (Query: "${dec.new_search_query}")` : ''}`,
						type: 'agent'
					});
				} else if (entry.report) {
					lines.push({
						time,
						tag: 'VERIFY',
						msg: `[Quality Verification] ${entry.report.summary || (entry.report.verified ? 'All verification checks passed' : 'Verification completed with warnings')}`,
						type: entry.report.verified ? 'success' : 'warning'
					});
				} else {
					const tag = (entry.stage || entry.step || 'AGENT').toUpperCase();
					const msg = entry.message || (typeof entry === 'string' ? entry : JSON.stringify(entry));
					lines.push({ time, tag, msg, type: 'agent' });
				}
			});
		}
		if (run.extracted_count !== undefined && run.extracted_count > 0) {
			lines.push({
				time: start,
				tag: 'EXTRACT',
				msg: `Extracted ${run.extracted_count} typed structured records`,
				type: 'info'
			});
		}
		if (run.validated_count !== undefined && run.validated_count > 0) {
			lines.push({
				time: start,
				tag: 'VALIDATE',
				msg: `${run.validated_count} records passed JSON schema & anomaly checks`,
				type: 'success'
			});
		}
		if (run.condition_message) {
			lines.push({ time: start, tag: 'ALERT', msg: run.condition_message, type: 'warning' });
		}
		if (run.error) {
			lines.push({ time: start, tag: 'ERROR', msg: run.error, type: 'error' });
		}
		if (run.finished_at) {
			const finishTime = new Date(run.finished_at).toLocaleTimeString();
			lines.push({
				time: finishTime,
				tag: 'COMPLETE',
				msg: `Run execution finished with status: ${run.status.toUpperCase()}`,
				type: 'success'
			});
		}
		return lines;
	});

	$effect(() => {
		if (autoScroll && consoleEl && logLines.length) {
			consoleEl.scrollTop = consoleEl.scrollHeight;
		}
	});

	async function copyLogs() {
		const text = logLines.map((l) => `[${l.time}] [${l.tag}] ${l.msg}`).join('\n');
		await navigator.clipboard.writeText(text);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}
</script>

<div
	class="rounded-xl border border-white/10 bg-black/90 font-mono text-xs overflow-hidden shadow-2xl"
>
	<div
		class="flex items-center justify-between px-4 py-2.5 bg-surface-950/80 border-b border-white/10 select-none"
	>
		<div class="flex items-center gap-2">
			<span class="w-3 h-3 rounded-full bg-rose-500/80 inline-block"></span>
			<span class="w-3 h-3 rounded-full bg-amber-500/80 inline-block"></span>
			<span class="w-3 h-3 rounded-full bg-emerald-500/80 inline-block"></span>
			<span class="text-slate-400 ml-2 font-mono text-[11px] hidden sm:inline"
				>orbit-runner ~ live-build.log</span
			>
		</div>
		<div class="flex items-center gap-3 text-[11px]">
			<button
				type="button"
				onclick={() => (autoScroll = !autoScroll)}
				class="text-slate-400 hover:text-white flex items-center gap-1"
			>
				<ArrowDown size={11} class={autoScroll ? 'text-orbit-cyan' : 'text-slate-600'} />
				<span>Auto-scroll: {autoScroll ? 'ON' : 'OFF'}</span>
			</button>
			<button
				type="button"
				onclick={copyLogs}
				class="text-slate-400 hover:text-white flex items-center gap-1"
			>
				{#if copied}<Check size={12} class="text-emerald-400" /><span>Copied</span>{:else}<Copy
						size={12}
					/><span>Copy</span>{/if}
			</button>
		</div>
	</div>

	<div
		bind:this={consoleEl}
		class="p-4 space-y-1.5 max-h-96 overflow-y-auto font-mono text-[12px] leading-relaxed"
	>
		{#each logLines as line}
			<div class="flex items-start gap-2.5">
				<span class="text-slate-600 shrink-0 select-none text-[11px]">{line.time}</span>
				<span
					class="px-1.5 py-0.5 rounded text-[10px] shrink-0 font-semibold {line.type === 'error'
						? 'bg-rose-950 text-rose-300 border border-rose-500/30'
						: line.type === 'warning'
							? 'bg-amber-950 text-amber-300 border border-amber-500/30'
							: line.type === 'agent'
								? 'bg-purple-950 text-purple-300 border border-purple-500/30'
								: line.type === 'success'
									? 'bg-emerald-950 text-emerald-300 border border-emerald-500/30'
									: 'bg-surface-800 text-orbit-cyan border border-orbit-cyan/30'}"
				>
					{line.tag}
				</span>
				<span
					class="break-all {line.type === 'error'
						? 'text-rose-300'
						: line.type === 'dim'
							? 'text-slate-500'
							: line.type === 'agent'
								? 'text-purple-200'
								: 'text-slate-200'}"
				>
					{line.msg}
				</span>
			</div>
		{/each}
		{#if run.status === 'running' || run.status === 'pending' || run.status === 'discovering' || run.status === 'retrieving' || run.status === 'extracting'}
			<div class="flex items-center gap-2 text-orbit-cyan pt-2 animate-pulse">
				<span class="inline-block w-2 h-2 rounded-full bg-orbit-cyan"></span>
				<span class="text-[11px]">Executing pipeline stage ({run.status})...</span>
			</div>
		{/if}
	</div>
</div>
