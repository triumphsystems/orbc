<script lang="ts">
	import { PanelLeftOpen } from '@lucide/svelte';
	import WorkflowNode from './WorkflowNode.svelte';
	import WorkflowConnections from './WorkflowConnections.svelte';
	import type { WorkflowNodeData, WorkflowEdge, NodeTemplate } from './types';

	interface Props {
		nodes: WorkflowNodeData[];
		edges: WorkflowEdge[];
		selectedNode: WorkflowNodeData | null;
		paletteOpen?: boolean;
		onTogglePalette?: () => void;
		onSelectNode: (node: WorkflowNodeData) => void;
		onDeleteNode: (id: string) => void;
		onDropNewNode: (template: NodeTemplate, x: number, y: number) => void;
		onUpdateNodePosition: (id: string, x: number, y: number) => void;
	}

	let {
		nodes,
		edges,
		selectedNode,
		paletteOpen = true,
		onTogglePalette,
		onSelectNode,
		onDeleteNode,
		onDropNewNode,
		onUpdateNodePosition
	}: Props = $props();

	let canvasEl: HTMLDivElement;
	let draggingNodeId = $state<string | null>(null);
	let dragOffset = $state({ x: 0, y: 0 });

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		if (!canvasEl) return;
		const raw = e.dataTransfer?.getData('application/json');
		if (!raw) return;
		try {
			const template: NodeTemplate = JSON.parse(raw);
			const rect = canvasEl.getBoundingClientRect();
			const x = Math.max(20, Math.min(rect.width - 240, e.clientX - rect.left - 100));
			const y = Math.max(20, Math.min(rect.height - 100, e.clientY - rect.top - 40));
			onDropNewNode(template, x, y);
		} catch {}
	}

	function handleDragNodeStart(e: MouseEvent, node: WorkflowNodeData) {
		draggingNodeId = node.id;
		dragOffset = { x: e.clientX - node.x, y: e.clientY - node.y };
		window.addEventListener('mousemove', handleMouseMove);
		window.addEventListener('mouseup', handleMouseUp);
	}

	function handleMouseMove(e: MouseEvent) {
		if (!draggingNodeId || !canvasEl) return;
		const rect = canvasEl.getBoundingClientRect();
		const newX = Math.max(10, Math.min(rect.width - 230, e.clientX - dragOffset.x));
		const newY = Math.max(10, Math.min(rect.height - 90, e.clientY - dragOffset.y));
		onUpdateNodePosition(draggingNodeId, newX, newY);
	}

	function handleMouseUp() {
		draggingNodeId = null;
		window.removeEventListener('mousemove', handleMouseMove);
		window.removeEventListener('mouseup', handleMouseUp);
	}
</script>

<div
	class="w-full overflow-x-auto overflow-y-hidden rounded-2xl border border-white/10 shadow-2xl backdrop-blur-md custom-scrollbar touch-pan-x"
>
	<div
		bind:this={canvasEl}
		ondragover={handleDragOver}
		ondrop={handleDrop}
		role="region"
		aria-label="Workflow Canvas"
		class="relative min-w-[780px] lg:min-w-full min-h-[520px] h-[520px] lg:min-h-[640px] lg:h-[640px] bg-surface-950/90 select-none overflow-hidden"
	>
		<div
			class="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none"
		></div>

		<!-- Floating In-Canvas Open Library Dock Button -->
		{#if !paletteOpen && onTogglePalette}
			<button
				type="button"
				onclick={onTogglePalette}
				class="absolute top-3 left-3 sm:top-4 sm:left-4 z-20 px-2.5 py-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-surface-900/90 hover:bg-surface-800 border border-white/15 hover:border-orbit-cyan/60 text-xs font-mono text-slate-200 shadow-xl backdrop-blur-md flex items-center gap-1.5 sm:gap-2 transition-all hover:scale-105"
			>
				<PanelLeftOpen size={14} class="text-orbit-cyan" />
				<span>Adapter Library</span>
			</button>
		{/if}

		<WorkflowConnections {nodes} {edges} />

		{#each nodes as node (node.id)}
			<WorkflowNode
				{node}
				selected={selectedNode?.id === node.id}
				onSelect={onSelectNode}
				onDelete={onDeleteNode}
				onDragNodeStart={handleDragNodeStart}
			/>
		{/each}
	</div>
</div>
