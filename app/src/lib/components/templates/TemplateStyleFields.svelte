<script lang="ts">
	interface Props {
		title: string;
		showSummary: boolean;
		themeColor: string;
		bgColor: string;
		textColor: string;
		onTitle: (v: string) => void;
		onToggleSummary: () => void;
		onThemeColor: (v: string) => void;
		onBgColor: (v: string) => void;
		onTextColor: (v: string) => void;
	}

	let {
		title,
		showSummary,
		themeColor,
		bgColor,
		textColor,
		onTitle,
		onToggleSummary,
		onThemeColor,
		onBgColor,
		onTextColor
	}: Props = $props();

	const colorFields = $derived([
		{ id: 'tpl-accent', label: 'Accent', val: themeColor, handler: onThemeColor },
		{ id: 'tpl-bg', label: 'Background', val: bgColor, handler: onBgColor },
		{ id: 'tpl-text', label: 'Text', val: textColor, handler: onTextColor }
	]);
</script>

<div class="space-y-2.5 pt-2 border-t border-white/8">
	<h3 class="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Report Style</h3>
	<div class="space-y-1">
		<label for="tpl-title" class="text-[10px] uppercase font-mono text-slate-400 font-semibold"
			>Report Title</label
		>
		<input
			id="tpl-title"
			type="text"
			value={title}
			oninput={(e) => onTitle((e.target as HTMLInputElement).value)}
			placeholder="Orbit Mission Intelligence Briefing"
			class="w-full px-3 py-1.5 bg-surface-800 border border-white/10 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orbit-cyan/60 font-sans"
		/>
	</div>
	<label class="flex items-center gap-3 cursor-pointer">
		<div
			role="checkbox"
			aria-checked={showSummary}
			tabindex="0"
			onclick={onToggleSummary}
			onkeydown={(e) => e.key === 'Enter' && onToggleSummary()}
			class="relative w-9 h-5 rounded-full transition-colors {showSummary
				? 'bg-orbit-cyan'
				: 'bg-surface-700 border border-white/10'}"
		>
			<span
				class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform {showSummary
					? 'translate-x-4'
					: 'translate-x-0'}"
			></span>
		</div>
		<span class="text-xs font-mono text-slate-200">Show Summary Block</span>
	</label>
	<div class="grid grid-cols-3 gap-2">
		{#each colorFields as f}
			<div class="space-y-1">
				<label for={f.id} class="text-[10px] uppercase font-mono text-slate-400">{f.label}</label>
				<div
					class="flex items-center gap-1.5 px-2 py-1.5 bg-surface-800 border border-white/10 rounded-lg"
				>
					<input
						id={f.id}
						type="color"
						value={f.val}
						oninput={(e) => f.handler((e.target as HTMLInputElement).value)}
						class="w-5 h-5 rounded cursor-pointer bg-transparent border-0 p-0 shrink-0"
					/>
					<span class="text-[9px] font-mono text-slate-400 truncate">{f.val}</span>
				</div>
			</div>
		{/each}
	</div>
	<div
		class="w-full h-8 rounded-lg border border-white/10 flex items-center px-3 gap-2"
		style="background:{bgColor}; color:{textColor};"
	>
		<span class="text-xs font-display font-bold" style="color:{themeColor}">Orbit</span>
		<span class="text-[11px] font-sans opacity-80 truncate">{title}</span>
	</div>
</div>
