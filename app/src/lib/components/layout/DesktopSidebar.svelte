<script lang="ts">
	import { page } from '$app/state';
	import type { Component } from 'svelte';
	import { PanelLeftClose, PanelLeftOpen } from '@lucide/svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';
	import OrbitLogo from '$lib/components/ui/OrbitLogo.svelte';
	import OrbitMark from '$lib/components/ui/OrbitMark.svelte';

	interface NavItem {
		href: string;
		label: string;
		icon: Component<{ size?: number; class?: string }>;
	}

	interface Props {
		navItems: NavItem[];
	}

	let { navItems }: Props = $props();
</script>

<aside
	class="hidden md:flex bg-surface-900 border-r border-white/10 flex-col justify-between shrink-0 z-20 sticky top-0 h-screen transition-all duration-200 ease-in-out {orbitStore.sidebarCollapsed
		? 'w-16'
		: 'w-64'}"
>
	<!-- Brand / Logo & Collapse Toggle -->
	<div
		class="p-3.5 border-b border-white/10 flex items-center {orbitStore.sidebarCollapsed
			? 'justify-center'
			: 'justify-between'} gap-2"
	>
		{#if orbitStore.sidebarCollapsed}
			<button
				type="button"
				onclick={() => orbitStore.toggleSidebar()}
				class="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
				title="Expand sidebar"
			>
				<OrbitMark size="sm" animated={true} />
			</button>
		{:else}
			<a href="/" class="group block overflow-hidden">
				<OrbitLogo
					size="md"
					showWordmark={true}
					animated={true}
					class="group-hover:opacity-90 transition-opacity"
				/>
			</a>
			<button
				type="button"
				onclick={() => orbitStore.toggleSidebar()}
				class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors shrink-0"
				title="Collapse sidebar"
			>
				<PanelLeftClose size={16} />
			</button>
		{/if}
	</div>

	<!-- Navigation Links -->
	<nav class="p-2 space-y-1 flex-1 overflow-y-auto overflow-x-hidden">
		{#if !orbitStore.sidebarCollapsed}
			<div
				class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500 font-mono"
			>
				Operations Hub
			</div>
		{/if}

		{#each navItems as item}
			{@const active =
				page.url.pathname === item.href ||
				(item.href !== '/' && page.url.pathname.startsWith(item.href))}
			<a
				href={item.href}
				title={orbitStore.sidebarCollapsed ? item.label : undefined}
				class="flex items-center {orbitStore.sidebarCollapsed
					? 'justify-center p-2.5'
					: 'justify-between px-3 py-2'} rounded-lg text-xs font-medium transition-all group {active
					? 'bg-gradient-to-r from-orbit-cyan/15 to-transparent text-orbit-cyan border-l-2 border-orbit-cyan font-semibold shadow-glow-cyan/10'
					: 'text-slate-300 hover:text-white hover:bg-surface-800/80'}"
			>
				<div class="flex items-center gap-3">
					<item.icon
						size={18}
						class={active
							? 'text-orbit-cyan'
							: 'text-slate-400 group-hover:text-slate-200 transition-colors'}
					/>
					{#if !orbitStore.sidebarCollapsed}
						<span class="truncate">{item.label}</span>
					{/if}
				</div>

				{#if active && !orbitStore.sidebarCollapsed}
					<span class="w-1.5 h-1.5 rounded-full bg-orbit-cyan shadow-glow-cyan"></span>
				{/if}
			</a>
		{/each}
	</nav>

	<!-- Bottom Telemetry & Daemon Status -->
	<div class="p-2.5 border-t border-white/10">
		{#if orbitStore.sidebarCollapsed}
			<div class="flex flex-col items-center gap-2">
				<button
					type="button"
					onclick={() => orbitStore.toggleSidebar()}
					class="p-2 rounded-lg text-slate-400 hover:text-orbit-cyan hover:bg-surface-800 transition-colors"
					title="Expand Sidebar"
				>
					<PanelLeftOpen size={16} />
				</button>
				<div
					class="w-8 h-8 rounded-lg flex items-center justify-center border {orbitStore.daemonConnected
						? 'bg-emerald-950/30 border-emerald-500/20'
						: 'bg-rose-950/40 border-rose-500/25'}"
					title={orbitStore.daemonConnected ? 'Daemon Online' : 'Daemon Offline'}
				>
					<span
						class="w-2 h-2 rounded-full {orbitStore.daemonConnected
							? 'bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.6)]'
							: 'bg-rose-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]'}"
					></span>
				</div>
			</div>
		{:else}
			<div
				class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border {orbitStore.daemonConnected
					? 'bg-emerald-950/30 border-emerald-500/20'
					: 'bg-rose-950/40 border-rose-500/25'}"
			>
				<span
					class="w-2 h-2 rounded-full shrink-0 {orbitStore.daemonConnected
						? 'bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.6)]'
						: 'bg-rose-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]'}"
				></span>
				<div class="flex-1 min-w-0">
					<p
						class="text-xs font-medium {orbitStore.daemonConnected
							? 'text-emerald-300'
							: 'text-rose-300'}"
					>
						{orbitStore.daemonConnected ? 'Daemon online' : 'Daemon offline'}
					</p>
					{#if orbitStore.health}
						<p class="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
							{orbitStore.health.environment} · scheduler {orbitStore.health.scheduler_enabled
								? 'on'
								: 'off'}
						</p>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</aside>
