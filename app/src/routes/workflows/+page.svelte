<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';
	import WorkflowHeader from '$lib/components/workflow/WorkflowHeader.svelte';
	import WorkflowPalette from '$lib/components/workflow/WorkflowPalette.svelte';
	import WorkflowCanvas from '$lib/components/workflow/WorkflowCanvas.svelte';
	import WorkflowConfigPanel from '$lib/components/workflow/WorkflowConfigPanel.svelte';
	import WorkflowDeployBanner from '$lib/components/workflow/WorkflowDeployBanner.svelte';
	import {
		defaultTriggerNode,
		persistLocalNodes,
		getLocalNodes,
		clearLocalNodes,
		createNodeFromTemplate,
		calculateNextPosition,
		fetchInitialWorkflowNodes
	} from '$lib/components/workflow/workflowLoader';
	import type {
		WorkflowNodeData,
		WorkflowEdge,
		NodeTemplate
	} from '$lib/components/workflow/types';

	let nodes = $state<WorkflowNodeData[]>(
		getLocalNodes() || JSON.parse(JSON.stringify(defaultTriggerNode))
	);
	let selectedNode = $state<WorkflowNodeData | null>(null);
	let paletteOpen = $state(true);
	let deploying = $state(false);
	let deployed = $state(false);
	let syncing = $state(false);
	let deployMessage = $state<string | null>(null);

	const edges = $derived<WorkflowEdge[]>(
		nodes
			.slice(0, -1)
			.map((node, i) => ({
				id: `edge_${node.id}_${nodes[i + 1].id}`,
				from: node.id,
				to: nodes[i + 1].id
			}))
	);

	async function loadTopology() {
		syncing = true;
		try {
			nodes = await fetchInitialWorkflowNodes();
			selectedNode = null;
		} catch (e) {
			console.warn('Failed to fetch workflow topology:', e);
		} finally {
			syncing = false;
		}
	}

	onMount(() => {
		if (typeof window !== 'undefined' && window.innerWidth < 1024) {
			paletteOpen = false;
		}
		loadTopology();
	});

	function handleAddNode(template: NodeTemplate) {
		const { x, y } = calculateNextPosition(nodes);
		nodes.push(createNodeFromTemplate(template, x, y));
		persistLocalNodes(nodes);
		if (typeof window !== 'undefined' && window.innerWidth < 1024) {
			paletteOpen = false;
		}
	}

	function handleUpdatePosition(id: string, x: number, y: number) {
		const node = nodes.find((n) => n.id === id);
		if (node) {
			node.x = x;
			node.y = y;
			persistLocalNodes(nodes);
		}
	}

	function handleDeleteNode(id: string) {
		nodes = nodes.filter((n) => n.id !== id);
		if (selectedNode?.id === id) selectedNode = null;
		persistLocalNodes(nodes);
	}

	async function handleDeploy() {
		deploying = true;
		deployMessage = null;
		try {
			const res = await api.deployWorkflow(nodes);
			nodes = nodes.map((n) => ({ ...n, status: 'configured' }));
			if (selectedNode) selectedNode = { ...selectedNode, status: 'configured' };
			persistLocalNodes(nodes);
			deployMessage = res.message || `Pipeline deployed with ${nodes.length} active stages.`;
			deployed = true;
			setTimeout(() => (deployed = false), 4000);
		} catch (e: any) {
			deployMessage = `Deployment warning: ${e.message || 'Check connection'}`;
		} finally {
			deploying = false;
		}
	}
</script>

<div class="max-w-7xl mx-auto space-y-5">
	<WorkflowHeader
		onDeploy={handleDeploy}
		onReset={() => {
			nodes = JSON.parse(JSON.stringify(defaultTriggerNode));
			selectedNode = null;
			deployMessage = null;
			clearLocalNodes();
		}}
		onSyncTopology={loadTopology}
		{deploying}
		{deployed}
		{syncing}
	/>

	<WorkflowDeployBanner message={deployMessage} onDismiss={() => (deployMessage = null)} />

	<div class="flex flex-col lg:flex-row items-start gap-4">
		{#if paletteOpen}
			<WorkflowPalette onAddNode={handleAddNode} onClose={() => (paletteOpen = false)} />
		{/if}

		<div class="flex-1 w-full min-w-0">
			<WorkflowCanvas
				{nodes}
				{edges}
				{selectedNode}
				{paletteOpen}
				onTogglePalette={() => (paletteOpen = !paletteOpen)}
				onSelectNode={(n) => (selectedNode = n)}
				onDeleteNode={handleDeleteNode}
				onDropNewNode={(template, x, y) => {
					nodes.push(createNodeFromTemplate(template, x, y));
					persistLocalNodes(nodes);
				}}
				onUpdateNodePosition={handleUpdatePosition}
			/>
		</div>

		{#if selectedNode}
			<WorkflowConfigPanel
				node={selectedNode}
				onClose={() => (selectedNode = null)}
				onSave={(cfg) => {
					const idx = nodes.findIndex((n) => n.id === selectedNode?.id);
					if (idx !== -1) {
						nodes[idx].config = { ...cfg };
						nodes[idx].status = 'configured';
						selectedNode = { ...nodes[idx] };
						persistLocalNodes(nodes);
					}
				}}
			/>
		{/if}
	</div>
</div>
