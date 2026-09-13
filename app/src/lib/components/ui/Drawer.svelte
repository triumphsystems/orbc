<script lang="ts">
	import { X } from '@lucide/svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		open: boolean;
		title?: string;
		subtitle?: string;
		onClose: () => void;
		children?: Snippet;
	}

	let { open = $bindable(), title, subtitle, onClose, children }: Props = $props();

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Escape' && open) {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeyDown} />

{#if open}
	<div class="fixed inset-0 z-50 overflow-hidden flex justify-end">
		<!-- Backdrop -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
			onclick={onClose}
		></div>

		<!-- Slide-over panel -->
		<div
			class="relative w-full max-w-xl bg-surface-900 border-l border-white/10 shadow-2xl flex flex-col h-full z-10 animate-in slide-in-from-right duration-200"
		>
			<!-- Header -->
			<div
				class="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-white/10 flex items-center justify-between bg-surface-850"
			>
				<div>
					{#if title}
						<h3 class="text-sm sm:text-base font-semibold text-slate-100 flex items-center gap-2">
							{title}
						</h3>
					{/if}
					{#if subtitle}
						<p
							class="text-[11px] sm:text-xs text-slate-400 mt-0.5 font-mono truncate max-w-xs sm:max-w-md"
						>
							{subtitle}
						</p>
					{/if}
				</div>
				<button
					onclick={onClose}
					class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-700 transition-colors"
					aria-label="Close drawer"
				>
					<X size={18} />
				</button>
			</div>

			<!-- Body Content -->
			<div class="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
				{@render children?.()}
			</div>
		</div>
	</div>
{/if}
