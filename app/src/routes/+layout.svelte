<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import {
		Radio,
		Layers,
		Database,
		GitBranch,
		FileText,
		Activity,
		RefreshCw,
		Menu,
		PanelLeftClose,
		PanelLeftOpen
	} from '@lucide/svelte';
	import { orbitStore } from '$lib/state/orbit.svelte';
	import DesktopSidebar from '$lib/components/layout/DesktopSidebar.svelte';
	import MobileNav from '$lib/components/layout/MobileNav.svelte';
	import MobileBottomNav from '$lib/components/layout/MobileBottomNav.svelte';
	import DaemonAlert from '$lib/components/layout/DaemonAlert.svelte';

	let { children } = $props();

	onMount(() => {
		orbitStore.initSidebar();
		orbitStore.checkHealth();
		orbitStore.loadAutomations();

		// Background polling for health status every 10 seconds
		const timer = setInterval(() => {
			orbitStore.checkHealth();
		}, 10000);

		return () => clearInterval(timer);
	});

	const navItems = [
		{ href: '/', label: 'Overview', shortLabel: 'Overview', icon: Radio },
		{ href: '/automations', label: 'Automation Fleet', shortLabel: 'Automation', icon: Layers },
		{ href: '/workflows', label: 'Workflows', shortLabel: 'Workflows', icon: GitBranch },
		{ href: '/data', label: 'Data Warehouse', shortLabel: 'Warehouse', icon: Database },
		{ href: '/templates', label: 'Template Studio', shortLabel: 'Templates', icon: FileText }
	];
</script>

<div class="min-h-screen flex flex-col md:flex-row bg-void text-slate-100 font-sans">
	<!-- Mobile Header & Navigation Drawer -->
	<MobileNav />

	<!-- Desktop Navigation Sidebar -->
	<DesktopSidebar {navItems} />

	<!-- Main Content Canvas -->
	<div class="flex-1 flex flex-col min-w-0 overflow-hidden">
		<!-- Top Bar (Desktop header with status & quick toggle) -->
		<header
			class="hidden md:flex h-14 bg-surface-900/80 backdrop-blur-md border-b border-white/10 px-4 sm:px-6 items-center justify-between shrink-0 z-10"
		>
			<div class="flex items-center gap-3">
				<button
					type="button"
					onclick={() => orbitStore.toggleSidebar()}
					class="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-surface-800 transition-colors"
					title={orbitStore.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
				>
					<Menu size={16} />
				</button>

				<div class="h-4 w-px bg-white/10 mx-1"></div>

				<div class="flex items-center gap-2.5 text-xs font-mono text-slate-400">
					<Activity size={14} class="text-orbit-cyan animate-pulse" />
					<span
						>Active Automations: <strong class="text-slate-100"
							>{orbitStore.activeAutomationsCount}</strong
						></span
					>
				</div>
			</div>

			<div class="flex items-center gap-3">
				<button
					type="button"
					onclick={() => orbitStore.loadAutomations()}
					class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-800 transition-colors"
					title="Refresh Telemetry"
				>
					<RefreshCw size={14} class={orbitStore.loading ? 'animate-spin' : ''} />
				</button>
			</div>
		</header>

		<!-- Global Error Banner if Daemon Unreachable -->
		<DaemonAlert />

		<!-- Page Viewport -->
		<main class="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 pb-24 md:pb-8 space-y-6 md:space-y-8">
			{@render children()}
		</main>
	</div>

	<!-- Mobile Bottom Navigation Bar -->
	<MobileBottomNav {navItems} />
</div>
