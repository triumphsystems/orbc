<script lang="ts">
	import type { WorkflowNodeData, WorkflowEdge } from './types';

	interface Props {
		nodes: WorkflowNodeData[];
		edges: WorkflowEdge[];
		nodeWidth?: number;
		nodeHeight?: number;
	}

	let { nodes, edges, nodeWidth = 220, nodeHeight = 85 }: Props = $props();

	function getNodeCenter(nodeId: string) {
		const node = nodes.find((n) => n.id === nodeId);
		if (!node) return null;
		return {
			x1: node.x + nodeWidth,
			y1: node.y + nodeHeight / 2,
			x2: node.x,
			y2: node.y + nodeHeight / 2
		};
	}

	function calculateBezierPath(fromId: string, toId: string): string {
		const from = getNodeCenter(fromId);
		const to = getNodeCenter(toId);
		if (!from || !to) return '';

		const startX = from.x1;
		const startY = from.y1;
		const endX = to.x2;
		const endY = to.y2;

		const dx = Math.max(40, Math.abs(endX - startX) * 0.5);
		return `M ${startX} ${startY} C ${startX + dx} ${startY}, ${endX - dx} ${endY}, ${endX} ${endY}`;
	}
</script>

<svg class="absolute inset-0 w-full h-full pointer-events-none z-0">
	<defs>
		<linearGradient id="orbitLineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
			<stop offset="0%" stop-color="#06b6d4" stop-opacity="0.8" />
			<stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.8" />
		</linearGradient>
	</defs>

	{#each edges as edge (edge.id)}
		{@const path = calculateBezierPath(edge.from, edge.to)}
		{#if path}
			<path
				d={path}
				fill="none"
				stroke="rgba(255,255,255,0.15)"
				stroke-width="3"
				stroke-linecap="round"
			/>
			<path
				d={path}
				fill="none"
				stroke="url(#orbitLineGrad)"
				stroke-width="2"
				stroke-dasharray="6,4"
				class="animate-pulse"
			/>
		{/if}
	{/each}
</svg>
