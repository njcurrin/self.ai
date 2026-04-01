<script lang="ts">
	import { createEventDispatcher, afterUpdate } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import PipelineNode from './PipelineNode.svelte';
	import SourceNodeContent from './SourceNodeContent.svelte';
	import SinkNodeContent from './SinkNodeContent.svelte';
	import TransformNodeContent from './TransformNodeContent.svelte';
	import { DOCUMENT_SPLITTER_TEMPLATE, DOCUMENT_JOINER_TEMPLATE, TEMPLATES_BY_STAGE_TYPE } from './nodeTemplate';
	import type { NodeTemplate } from './nodeTemplate';

	const dispatch = createEventDispatcher();

	export let nodes: NodeDef[] = [];
	export let connections: Connection[] = [];

	type NodeDef = {
		id: string;
		label: string;
		type: 'source' | 'sink' | 'transform';
		x: number;
		y: number;
		headerColor: string;
		config: Record<string, any>;
	};

	type Connection = {
		fromId: string;
		toId: string;
	};

	const NODE_TYPES: Array<{
		type: NodeDef['type'];
		label: string;
		headerColor: string;
		description: string;
		template?: NodeTemplate;
		group?: string;
	}> = [
		{ type: 'source', label: 'Source', headerColor: 'bg-emerald-600', description: 'File input / KB source' },
		{ type: 'sink', label: 'Output', headerColor: 'bg-indigo-600', description: 'Stage output sink' },
		{ type: 'transform', label: 'Document Splitter', headerColor: 'bg-rose-950', description: 'Split docs by separator', template: DOCUMENT_SPLITTER_TEMPLATE, group: 'Document Ops' },
		{ type: 'transform', label: 'Document Joiner', headerColor: 'bg-violet-600', description: 'Join documents', template: DOCUMENT_JOINER_TEMPLATE, group: 'Document Ops' },
	];

	// Canvas pan state
	let panX = 0;
	let panY = 0;
	let isPanning = false;
	let panStartX = 0;
	let panStartY = 0;
	let panOriginX = 0;
	let panOriginY = 0;

	// Context menu state
	let contextMenuVisible = false;
	let contextMenuX = 0;
	let contextMenuY = 0;
	let contextMenuCanvasX = 0;
	let contextMenuCanvasY = 0;

	let canvasEl: HTMLDivElement;
	let containerEl: HTMLDivElement;

	// Connection drawing state
	let draggingConnection: { nodeId: string; port: 'input' | 'output' } | null = null;
	let mousePos = { x: 0, y: 0 };
	let portPositions = new Map<string, { x: number; y: number }>();

	afterUpdate(() => {
		updatePortPositions();
	});

	function updatePortPositions() {
		if (!canvasEl) return;
		const canvasRect = canvasEl.getBoundingClientRect();
		const ports = canvasEl.querySelectorAll('.port');
		const next = new Map<string, { x: number; y: number }>();
		ports.forEach((port) => {
			const el = port as HTMLElement;
			const nodeId = el.dataset.nodeId!;
			const portType = el.dataset.port!;
			const rect = el.getBoundingClientRect();
			next.set(`${nodeId}:${portType}`, {
				x: rect.left + rect.width / 2 - canvasRect.left,
				y: rect.top + rect.height / 2 - canvasRect.top
			});
		});
		portPositions = next;
	}

	// Convert screen coords (relative to canvasEl) to world coords (accounting for pan)
	function screenToWorld(sx: number, sy: number) {
		return { x: sx - panX, y: sy - panY };
	}

	function canvasRelative(e: MouseEvent | PointerEvent): { x: number; y: number } {
		const r = canvasEl.getBoundingClientRect();
		return { x: e.clientX - r.left, y: e.clientY - r.top };
	}

	// --- Pan handling ---
	function onPointerDownCanvas(e: PointerEvent) {
		// Don't start pan if clicking a port or node
		//if ((e.target as HTMLElement).closest('.port')) return;
		// Also handle port drag starts
		const portEl = (e.target as HTMLElement).closest('.port') as HTMLElement | null;
		if (portEl) {
			e.stopPropagation();
			e.preventDefault();
			const nodeId = portEl.dataset.nodeId!;
			const portType = portEl.dataset.port as 'input' | 'output';
			const pos = portPositions.get(`${nodeId}:${portType}`);
			if (pos) mousePos = { ...pos };
			draggingConnection = { nodeId, port: portType };
			canvasEl.setPointerCapture(e.pointerId);
		}
		if ((e.target as HTMLElement).closest('.pipeline-node')) return;
		if (e.button === 1 || (e.button === 0 && !contextMenuVisible)) {
			isPanning = true;
			panStartX = e.clientX;
			panStartY = e.clientY;
			panOriginX = panX;
			panOriginY = panY;
			canvasEl.setPointerCapture(e.pointerId);
		}

	}

	function onPointerMoveCanvas(e: PointerEvent) {
		if (isPanning) {
			panX = panOriginX + (e.clientX - panStartX);
			panY = panOriginY + (e.clientY - panStartY);
		}
		if (draggingConnection) {
			mousePos = canvasRelative(e);
		}
	}

	function onPointerUpCanvas(e: PointerEvent) {
		if (isPanning) {
			isPanning = false;
			canvasEl.releasePointerCapture(e.pointerId);
		}
		if (draggingConnection) {
			canvasEl.releasePointerCapture(e.pointerId);
			const pos = canvasRelative(e);
			const target = findNearestPort(pos.x, pos.y, draggingConnection.nodeId, draggingConnection.port);
			if (target && target.port !== draggingConnection.port && target.nodeId !== draggingConnection.nodeId) {
				const fromId = draggingConnection.port === 'output' ? draggingConnection.nodeId : target.nodeId;
				const toId = draggingConnection.port === 'output' ? target.nodeId : draggingConnection.nodeId;
				if (!connections.some((c) => c.fromId === fromId && c.toId === toId)) {
					connections = [...connections, { fromId, toId }];
					dispatch('configchange', { nodes, connections });
				}
			}
			draggingConnection = null;
		}
	}

	// --- Right-click context menu ---
	function onContextMenu(e: MouseEvent) {
		e.preventDefault();
		const rel = canvasRelative(e);
		const world = screenToWorld(rel.x, rel.y);
		contextMenuX = rel.x;
		contextMenuY = rel.y;
		contextMenuCanvasX = world.x;
		contextMenuCanvasY = world.y;
		contextMenuVisible = true;
	}

	function addNode(type: NodeDef['type'], label: string, headerColor: string, template?: NodeTemplate) {
		const id = uuidv4();
		const defaultParams: Record<string, any> = {};
		if (template) {
			for (const p of template.params) {
				if (p.default !== undefined && p.default !== null) {
					defaultParams[p.name] = p.default;
				}
			}
		}
		nodes = [
			...nodes,
			{
				id,
				label,
				type,
				x: contextMenuCanvasX,
				y: contextMenuCanvasY,
				headerColor,
				config: template ? { stage_type: template.stageType, params: defaultParams } : {}
			}
		];
		contextMenuVisible = false;
		dispatch('configchange', { nodes, connections });
	}

	function dismissContextMenu() {
		contextMenuVisible = false;
	}

	// --- Node interactions ---
	function handleNodeMove(e: CustomEvent<{ id: string; x: number; y: number }>) {
		const { id, x, y } = e.detail;
		nodes = nodes.map((n) => (n.id === id ? { ...n, x, y } : n));
		updatePortPositions();
	}

	function handleNodeConfigChange(nodeId: string, newConfig: Record<string, any>) {
		nodes = nodes.map((n) => (n.id === nodeId ? { ...n, config: newConfig } : n));
		dispatch('configchange', { nodes, connections });
	}

	// --- Connection paths ---
	function bezier(x1: number, y1: number, x2: number, y2: number): string {
		const cpOffset = Math.max(60, Math.abs(x2 - x1) * 0.4);
		return `M ${x1} ${y1} C ${x1 + cpOffset} ${y1}, ${x2 - cpOffset} ${y2}, ${x2} ${y2}`;
	}

	$: computedPaths = (() => {
		const paths: string[] = [];
		for (const conn of connections) {
			const fromPos = portPositions.get(`${conn.fromId}:output`);
			const toPos = portPositions.get(`${conn.toId}:input`);
			paths.push(fromPos && toPos ? bezier(fromPos.x, fromPos.y, toPos.x, toPos.y) : '');
		}
		return paths;
	})();

	$: pendingPath = (() => {
		if (!draggingConnection) return '';
		const pos = portPositions.get(`${draggingConnection.nodeId}:${draggingConnection.port}`);
		if (!pos) return '';
		const isOutput = draggingConnection.port === 'output';
		return bezier(
			isOutput ? pos.x : mousePos.x,
			isOutput ? pos.y : mousePos.y,
			isOutput ? mousePos.x : pos.x,
			isOutput ? mousePos.y : pos.y
		);
	})();

	function findNearestPort(
		clickX: number,
		clickY: number,
		excludeNodeId?: string,
		excludePort?: string
	): { nodeId: string; port: string } | null {
		if (!canvasEl) return null;
		const canvasRect = canvasEl.getBoundingClientRect();
		const ports = canvasEl.querySelectorAll('.port');
		let closest: { nodeId: string; port: string; dist: number } | null = null;
		ports.forEach((port) => {
			const el = port as HTMLElement;
			const nodeId = el.dataset.nodeId!;
			const portType = el.dataset.port!;
			if (nodeId === excludeNodeId && portType === excludePort) return;
			const rect = el.getBoundingClientRect();
			const px = rect.left + rect.width / 2 - canvasRect.left;
			const py = rect.top + rect.height / 2 - canvasRect.top;
			const dist = Math.sqrt((clickX - px) ** 2 + (clickY - py) ** 2);
			if (dist <= 15 && (!closest || dist < closest.dist)) {
				closest = { nodeId, port: portType, dist };
			}
		});
		return closest;
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			draggingConnection = null;
			contextMenuVisible = false;
		}
	}
</script>

<svelte:window on:keydown={handleKeyDown} />

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	class="relative w-full h-full overflow-hidden"
	bind:this={containerEl}
	on:click={dismissContextMenu}
>
	<!-- Canvas surface -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="absolute inset-0 overflow-hidden"
		class:cursor-crosshair={!!draggingConnection}
		class:cursor-grabbing={isPanning}
		class:cursor-grab={!isPanning && !draggingConnection}
		bind:this={canvasEl}
		on:pointerdown={onPointerDownCanvas}
		on:pointermove={onPointerMoveCanvas}
		on:pointerup={onPointerUpCanvas}
		on:contextmenu={onContextMenu}
	>
		<!-- Infinite dot grid -->
		<svg class="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
			<defs>
				<pattern id="dot-grid" x={panX % 20} y={panY % 20} width="20" height="20" patternUnits="userSpaceOnUse">
					<circle cx="10" cy="10" r="1" class="fill-gray-200 dark:fill-gray-700" />
				</pattern>
			</defs>
			<rect width="100%" height="100%" fill="url(#dot-grid)" />
		</svg>

		<!-- Connection lines (in screen space, ports track their own positions) -->
		<svg class="absolute inset-0 w-full h-full pointer-events-none" style="z-index: 1;">
			{#each connections as conn, i}
				{#if computedPaths[i]}
					<path d={computedPaths[i]} fill="none" stroke="#94a3b8" stroke-width="2" />
				{/if}
			{/each}
			{#if pendingPath}
				<path d={pendingPath} fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6 3" opacity="0.6" />
			{/if}
		</svg>

		<!-- World-space node container, shifted by pan -->
		<div class="absolute inset-0" style="z-index: 2; transform: translate({panX}px, {panY}px);">
			{#each nodes as node (node.id)}
				<PipelineNode
					id={node.id}
					label={node.label}
					type={node.type}
					x={node.x}
					y={node.y}
					headerColor={node.headerColor}
					on:move={handleNodeMove}
				>
					{#if node.type === 'source'}
						<SourceNodeContent
							config={node.config}
							on:configchange={(e) => handleNodeConfigChange(node.id, e.detail)}
						/>
					{:else if node.type === 'sink'}
						<SinkNodeContent config={node.config} stageLabel="output" />
					{:else if node.type === 'transform'}
						{@const tpl = node.config?.stage_type ? TEMPLATES_BY_STAGE_TYPE[node.config.stage_type] : null}
						{#if tpl}
							<TransformNodeContent
								template={tpl}
								config={node.config}
								on:configchange={(e) => handleNodeConfigChange(node.id, e.detail)}
								/>
						{/if}
					{/if}
				</PipelineNode>
			{/each}
		</div>

		<!-- Empty state hint -->
		{#if nodes.length === 0}
			<div class="absolute inset-0 flex items-center justify-center pointer-events-none select-none">
				<div class="text-center text-gray-400 dark:text-gray-600">
					<div class="text-sm font-medium mb-1">Empty pipeline</div>
					<div class="text-xs">Right-click anywhere to add nodes</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Context menu (rendered in container so it stays inside the KB panel) -->
	{#if contextMenuVisible}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="absolute z-50 min-w-[160px] rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 py-1 text-sm"
			style="left: {contextMenuX}px; top: {contextMenuY}px;"
			on:click|stopPropagation
		>
			<div class="px-3 py-1.5 text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Add Node</div>
			{#each NODE_TYPES as nt, i}
				{#if nt.group && (i === 0 || NODE_TYPES[i - 1].group !== nt.group)}
					<div class="px-3 pt-2 pb-0.5 text-[10px] uppercase tracking-wider text-gray-400 font-semibold border-t border-gray-100 dark:border-gray-800 mt-1">
						{nt.group}
					</div>
				{/if}
				<button
					class="w-full flex items-center gap-2.5 px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800 transition text-left"
					on:click={() => addNode(nt.type, nt.label, nt.headerColor, nt.template)}
				>
					<span class="w-2 h-2 rounded-full flex-shrink-0 {nt.headerColor}"></span>
					<span class="font-medium text-gray-700 dark:text-gray-200">{nt.label}</span>
					<span class="text-gray-400 text-[11px] truncate">{nt.description}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>
