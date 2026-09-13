<script lang="ts">
	import { AlertCircle } from '@lucide/svelte';
	import type { MissingParameter } from '$lib/api/types';

	interface Props {
		parameters: MissingParameter[];
		userInputs: Record<string, string>;
		onInputChange?: (key: string, val: string) => void;
	}

	let { parameters, userInputs = $bindable() }: Props = $props();
</script>

<div class="p-4 rounded-xl bg-amber-950/25 border border-amber-500/30 space-y-3">
	<div class="flex items-center gap-2 text-amber-300 text-xs font-semibold uppercase font-mono">
		<AlertCircle size={15} />
		<span>Action Required: Configure Workflow Inputs</span>
	</div>
	<p class="text-xs text-slate-300 leading-relaxed">
		Orbit detected specialized integration steps in your goal. Provide the missing parameters below
		so Orbit can connect the workflow:
	</p>

	<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
		{#each parameters as param}
			<div class="space-y-1">
				<label
					for={param.parameter_name}
					class="text-[11px] font-semibold text-slate-300 font-mono"
				>
					{param.label}
					{#if param.required}<span class="text-rose-400">*</span>{/if}
				</label>
				<p class="text-[10px] text-slate-400 font-mono">{param.prompt}</p>
				<input
					type={param.parameter_name.includes('url') ||
					param.parameter_name.includes('key') ||
					param.parameter_name.includes('secret')
						? 'password'
						: 'text'}
					id={param.parameter_name}
					bind:value={userInputs[param.parameter_name]}
					placeholder={param.default_value || `Enter ${param.label.toLowerCase()}...`}
					class="w-full px-3 py-1.5 bg-surface-900 border border-white/15 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orbit-cyan font-mono"
				/>
			</div>
		{/each}
	</div>
</div>
