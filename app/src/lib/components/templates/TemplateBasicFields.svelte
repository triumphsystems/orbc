<script lang="ts">
	import { Star } from '@lucide/svelte';

	interface Props {
		name: string;
		description: string;
		format: string;
		isDefault: boolean;
		onName: (v: string) => void;
		onDescription: (v: string) => void;
		onFormat: (v: string) => void;
		onToggleDefault: () => void;
	}

	let {
		name,
		description,
		format,
		isDefault,
		onName,
		onDescription,
		onFormat,
		onToggleDefault
	}: Props = $props();
</script>

<div class="space-y-2.5">
	<h3 class="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Basic Info</h3>
	<div class="space-y-1">
		<label for="tpl-name" class="text-[10px] uppercase font-mono text-slate-400 font-semibold"
			>Template Name *</label
		>
		<input
			id="tpl-name"
			type="text"
			value={name}
			oninput={(e) => onName((e.target as HTMLInputElement).value)}
			placeholder="Executive Briefing, Contract Report..."
			class="w-full px-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orbit-cyan/60 font-sans"
		/>
	</div>
	<div class="space-y-1">
		<label for="tpl-desc" class="text-[10px] uppercase font-mono text-slate-400 font-semibold"
			>Description</label
		>
		<textarea
			id="tpl-desc"
			value={description}
			oninput={(e) => onDescription((e.target as HTMLTextAreaElement).value)}
			placeholder="Optional description..."
			rows={2}
			class="w-full px-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orbit-cyan/60 font-mono resize-none"
		></textarea>
	</div>
	<div class="space-y-1">
		<span class="text-[10px] uppercase font-mono text-slate-400 font-semibold">Output Format</span>
		<div
			class="flex items-center rounded-lg bg-surface-800 p-0.5 border border-white/10 text-[11px] font-mono gap-0.5"
		>
			{#each ['pdf', 'html', 'docx'] as fmt}
				<button
					type="button"
					onclick={() => onFormat(fmt)}
					class="flex-1 py-1.5 px-2 rounded-md font-semibold text-center transition-colors {format ===
					fmt
						? 'bg-orbit-cyan/20 text-orbit-cyan border border-orbit-cyan/30'
						: 'text-slate-400 hover:text-slate-200'}">{fmt.toUpperCase()}</button
				>
			{/each}
		</div>
	</div>
	<label class="flex items-center gap-3 cursor-pointer">
		<div
			role="checkbox"
			aria-checked={isDefault}
			tabindex="0"
			onclick={onToggleDefault}
			onkeydown={(e) => e.key === 'Enter' && onToggleDefault()}
			class="relative w-9 h-5 rounded-full transition-colors {isDefault
				? 'bg-orbit-cyan'
				: 'bg-surface-700 border border-white/10'}"
		>
			<span
				class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform {isDefault
					? 'translate-x-4'
					: 'translate-x-0'}"
			></span>
		</div>
		<span class="text-xs font-mono text-slate-200">Default Template</span>
		{#if isDefault}<Star size={12} class="text-amber-400 fill-amber-400 ml-auto shrink-0" />{/if}
	</label>
</div>
