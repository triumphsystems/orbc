<script lang="ts">
	import { page } from '$app/state';
	import type { Component } from 'svelte';

	interface NavItem {
		href: string;
		label: string;
		shortLabel?: string;
		icon: Component<{ size?: number; class?: string }>;
	}

	interface Props {
		navItems: NavItem[];
	}

	let { navItems }: Props = $props();
</script>

<nav
	class="fixed bottom-0 inset-x-0 z-40 md:hidden bg-surface-900/95 backdrop-blur-xl border-t border-white/10 px-2 pt-1.5 pb-[max(0.5rem,env(safe-area-inset-bottom))] shadow-2xl transition-transform duration-200"
	aria-label="Mobile Navigation"
>
	<div class="flex items-center justify-around max-w-lg mx-auto">
		{#each navItems as item}
			{@const active =
				page.url.pathname === item.href ||
				(item.href !== '/' && page.url.pathname.startsWith(item.href))}
			<a
				href={item.href}
				aria-current={active ? 'page' : undefined}
				class="flex flex-col items-center justify-center flex-1 py-1 px-1 rounded-xl transition-all duration-150 relative group active:scale-95 {active
					? 'text-orbit-cyan font-medium'
					: 'text-slate-400 hover:text-slate-200'}"
			>
				{#if active}
					<span
						class="absolute -top-1.5 w-8 h-0.5 rounded-full bg-orbit-cyan shadow-[0_0_8px_#00F2FE]"
					></span>
				{/if}

				<div
					class="p-1 rounded-lg transition-colors {active
						? 'bg-orbit-cyan/10'
						: 'group-hover:bg-surface-800'}"
				>
					<item.icon
						size={18}
						class={active
							? 'text-orbit-cyan'
							: 'text-slate-400 group-hover:text-slate-200 transition-colors'}
					/>
				</div>

				<span
					class="text-[10px] font-sans tracking-tight mt-0.5 leading-tight {active
						? 'text-orbit-cyan font-semibold'
						: 'text-slate-400'}"
				>
					{item.shortLabel ?? item.label}
				</span>
			</a>
		{/each}
	</div>
</nav>
