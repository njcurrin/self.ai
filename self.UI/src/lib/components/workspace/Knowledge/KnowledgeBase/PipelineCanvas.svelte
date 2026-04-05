<script lang="ts">
	import { createEventDispatcher, afterUpdate } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import PipelineNode from './PipelineNode.svelte';
	import SourceNodeContent from './SourceNodeContent.svelte';
	import SinkNodeContent from './SinkNodeContent.svelte';
	import TransformNodeContent from './TransformNodeContent.svelte';
	import {
		DOCUMENT_SPLITTER_TEMPLATE,
		DOCUMENT_JOINER_TEMPLATE,
		WORD_COUNT_FILTER_TEMPLATE,
		NON_ALPHA_NUMERIC_FILTER_TEMPLATE,
		URLS_FILTER_TEMPLATE,
		NUMBERS_FILTER_TEMPLATE,
		WHITESPACE_FILTER_TEMPLATE,
		BULLETS_FILTER_TEMPLATE,
		LONG_WORD_FILTER_TEMPLATE,
		BOILERPLATE_STRING_FILTER_TEMPLATE,
		BOILERPLATE_STRING_MODIFIER_TEMPLATE,
		QUOTATION_REMOVER_MODIFIER_TEMPLATE,
		MARKDOWN_REMOVER_MODIFIER_TEMPLATE,
		NEWLINE_NORMALIZER_MODIFIER_TEMPLATE,
		SLICER_MODIFIER_TEMPLATE,
		URL_REMOVER_MODIFIER_TEMPLATE,
		LINE_REMOVER_MODIFIER_TEMPLATE,
		TEMPLATES_BY_STAGE_TYPE,
        UNICODE_REFORMATTER_MODIFIER_TEMPLATE,
		QUALITY_CLASSIFIER_TEMPLATE,
		DOMAIN_CLASSIFIER_TEMPLATE,
		MULTILINGUAL_DOMAIN_CLASSIFIER_TEMPLATE,
		CONTENT_TYPE_CLASSIFIER_TEMPLATE,
		FINEWEB_EDU_CLASSIFIER_TEMPLATE,
		FINEWEB_MIXTRAL_EDU_CLASSIFIER_TEMPLATE,
		FINEWEB_NEMOTRON_EDU_CLASSIFIER_TEMPLATE,
		PROMPT_TASK_COMPLEXITY_CLASSIFIER_TEMPLATE,
		EXACT_DEDUP_TEMPLATE,
		FUZZY_DEDUP_TEMPLATE,
		SYMBOLS_TO_WORDS_FILTER_TEMPLATE,
		PARENTHESES_FILTER_TEMPLATE,
		MEAN_WORD_LENGTH_FILTER_TEMPLATE,
		PUNCTUATION_FILTER_TEMPLATE,
		ELLIPSIS_FILTER_TEMPLATE,
		COMMON_ENGLISH_WORDS_FILTER_TEMPLATE,
		WORDS_WITHOUT_ALPHABETS_FILTER_TEMPLATE,
		PORNOGRAPHIC_URLS_FILTER_TEMPLATE,
		SUBSTRING_FILTER_TEMPLATE,
		REPEATED_LINES_FILTER_TEMPLATE,
		REPEATED_PARAGRAPHS_FILTER_TEMPLATE,
		REPEATED_LINES_BY_CHAR_FILTER_TEMPLATE,
		REPEATED_PARAGRAPHS_BY_CHAR_FILTER_TEMPLATE,
		REPEATING_TOP_NGRAMS_FILTER_TEMPLATE,
		REPEATING_DUPLICATE_NGRAMS_FILTER_TEMPLATE,
		PYTHON_COMMENT_TO_CODE_FILTER_TEMPLATE,
		GENERAL_COMMENT_TO_CODE_FILTER_TEMPLATE,
		NUMBER_OF_LINES_OF_CODE_FILTER_TEMPLATE,
		XML_HEADER_FILTER_TEMPLATE,
		ALPHA_FILTER_TEMPLATE,
		HTML_BOILERPLATE_FILTER_TEMPLATE,
		TOKENIZER_FERTILITY_FILTER_TEMPLATE,
		PER_EXTENSION_FILTER_TEMPLATE,
		FASTTEXT_QUALITY_FILTER_TEMPLATE,
		FASTTEXT_LANG_ID_TEMPLATE,
		FASTTEXT_LABEL_MODIFIER_TEMPLATE,
		HISTOGRAM_FILTER_TEMPLATE,
		TOKEN_COUNT_FILTER_TEMPLATE,
	} from './nodeTemplate';
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
		{ type: 'transform', label: 'Word Count Filter', headerColor: 'bg-amber-600', description: 'Filter by word count', template: WORD_COUNT_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Non-AlphaNumeric Filter', headerColor: 'bg-amber-600', description: 'Filter by non-alphanumeric ratio', template: NON_ALPHA_NUMERIC_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'URL Filter', headerColor: 'bg-amber-600', description: 'Filter by URL density', template: URLS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Numbers Filter', headerColor: 'bg-amber-600', description: 'Filter by numeric character ratio', template: NUMBERS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Whitespace Filter', headerColor: 'bg-amber-600', description: 'Filter by whitespace ratio', template: WHITESPACE_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Bullets Filter', headerColor: 'bg-amber-600', description: 'Filter by bullet line ratio', template: BULLETS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Long Word Filter', headerColor: 'bg-amber-600', description: 'Filter by max word length', template: LONG_WORD_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Boilerplate Filter', headerColor: 'bg-amber-600', description: 'Filter boilerplate strings', template: BOILERPLATE_STRING_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Symbols to Words Filter', headerColor: 'bg-amber-600', description: 'Filter by symbol-to-word ratio', template: SYMBOLS_TO_WORDS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Parentheses Filter', headerColor: 'bg-amber-600', description: 'Filter by parentheses ratio', template: PARENTHESES_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Mean Word Length Filter', headerColor: 'bg-amber-600', description: 'Filter by average word length', template: MEAN_WORD_LENGTH_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Punctuation Filter', headerColor: 'bg-amber-600', description: 'Filter by sentence end-punctuation rate', template: PUNCTUATION_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Ellipsis Filter', headerColor: 'bg-amber-600', description: 'Filter by ellipsis line ratio', template: ELLIPSIS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Common English Words Filter', headerColor: 'bg-amber-600', description: 'Filter by presence of common English words', template: COMMON_ENGLISH_WORDS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Words Without Alphabets Filter', headerColor: 'bg-amber-600', description: 'Filter by fraction of words with alphabetic chars', template: WORDS_WITHOUT_ALPHABETS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Pornographic URLs Filter', headerColor: 'bg-amber-600', description: 'Remove docs with adult content URLs', template: PORNOGRAPHIC_URLS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Substring Filter', headerColor: 'bg-amber-600', description: 'Keep docs containing a substring at a position', template: SUBSTRING_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Repeated Lines Filter', headerColor: 'bg-amber-600', description: 'Filter docs with many duplicate lines', template: REPEATED_LINES_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Repeated Paragraphs Filter', headerColor: 'bg-amber-600', description: 'Filter docs with many duplicate paragraphs', template: REPEATED_PARAGRAPHS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Repeated Lines by Char Filter', headerColor: 'bg-amber-600', description: 'Filter by repeated-line character ratio', template: REPEATED_LINES_BY_CHAR_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Repeated Paragraphs by Char Filter', headerColor: 'bg-amber-600', description: 'Filter by repeated-paragraph character ratio', template: REPEATED_PARAGRAPHS_BY_CHAR_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Repeating Top N-Grams Filter', headerColor: 'bg-amber-600', description: 'Filter docs dominated by top n-grams', template: REPEATING_TOP_NGRAMS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Repeating Duplicate N-Grams Filter', headerColor: 'bg-amber-600', description: 'Filter docs dominated by duplicate n-grams', template: REPEATING_DUPLICATE_NGRAMS_FILTER_TEMPLATE, group: 'Filters' },
		{ type: 'transform', label: 'Boilerplate Modifier', headerColor: 'bg-teal-600', description: 'Remove boilerplate strings', template: BOILERPLATE_STRING_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Remove Quotation Marks', headerColor: 'bg-teal-600', description: 'Strip surrounding quotes', template: QUOTATION_REMOVER_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Strip Markdown', headerColor: 'bg-teal-600', description: 'Remove markdown formatting', template: MARKDOWN_REMOVER_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Newline Normalizer', headerColor: 'bg-teal-600', description: 'Normalize excessive newlines', template: NEWLINE_NORMALIZER_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Slicer', headerColor: 'bg-teal-600', description: 'Slice document by character index', template: SLICER_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Remove URLs', headerColor: 'bg-teal-600', description: 'Strip all URLs from document', template: URL_REMOVER_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Line Remover', headerColor: 'bg-teal-600', description: 'Remove lines matching patterns', template: LINE_REMOVER_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Unicode Reformatter', headerColor: 'bg-teal-600', description: 'Make Everything Unicode Characters', template: UNICODE_REFORMATTER_MODIFIER_TEMPLATE, group: 'Modifiers' },
		{ type: 'transform', label: 'Quality Classifier', headerColor: 'bg-purple-600', description: 'Score documents by quality', template: QUALITY_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'Domain Classifier', headerColor: 'bg-purple-600', description: 'Classify docs into content domains', template: DOMAIN_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'Multilingual Domain Classifier', headerColor: 'bg-purple-600', description: 'Domain classifier (52 languages)', template: MULTILINGUAL_DOMAIN_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'Content Type Classifier', headerColor: 'bg-purple-600', description: 'Classify into 11 speech/content types', template: CONTENT_TYPE_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'FineWeb Edu Classifier', headerColor: 'bg-purple-600', description: 'Score educational content quality (0–5)', template: FINEWEB_EDU_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'FineWeb Mixtral Edu Classifier', headerColor: 'bg-purple-600', description: 'Edu quality via Mixtral annotations', template: FINEWEB_MIXTRAL_EDU_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'FineWeb Nemotron Edu Classifier', headerColor: 'bg-purple-600', description: 'Edu quality via Nemotron-4 annotations', template: FINEWEB_NEMOTRON_EDU_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'Prompt Task & Complexity', headerColor: 'bg-purple-600', description: 'Score prompt complexity across 6 dimensions', template: PROMPT_TASK_COMPLEXITY_CLASSIFIER_TEMPLATE, group: 'Classifiers' },
		{ type: 'transform', label: 'Exact Dedup', headerColor: 'bg-cyan-700', description: 'Hash-based exact duplicate removal (GPU)', template: EXACT_DEDUP_TEMPLATE, group: 'Deduplication' },
		{ type: 'transform', label: 'Fuzzy Dedup', headerColor: 'bg-cyan-700', description: 'MinHash/LSH near-duplicate removal (GPU)', template: FUZZY_DEDUP_TEMPLATE, group: 'Deduplication' },
		{ type: 'transform', label: 'Python Comment/Code Ratio', headerColor: 'bg-violet-700', description: 'Filter Python files by comment-to-code ratio', template: PYTHON_COMMENT_TO_CODE_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'Comment/Code Ratio', headerColor: 'bg-violet-700', description: 'Filter code files by comment ratio (any language)', template: GENERAL_COMMENT_TO_CODE_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'Lines of Code', headerColor: 'bg-violet-700', description: 'Filter by number of lines of code', template: NUMBER_OF_LINES_OF_CODE_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'XML Header', headerColor: 'bg-violet-700', description: 'Remove files with XML headers (wrong extension)', template: XML_HEADER_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'Alpha Ratio', headerColor: 'bg-violet-700', description: 'Filter out files that are mostly non-alphabetic', template: ALPHA_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'HTML Boilerplate', headerColor: 'bg-violet-700', description: 'Remove HTML files that are mostly boilerplate', template: HTML_BOILERPLATE_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'Tokenizer Fertility', headerColor: 'bg-violet-700', description: 'Filter code by chars-per-token ratio (SentencePiece)', template: TOKENIZER_FERTILITY_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'Per-Extension Filter', headerColor: 'bg-violet-700', description: 'Apply language/extension-specific code quality rules', template: PER_EXTENSION_FILTER_TEMPLATE, group: 'Code Quality' },
		{ type: 'transform', label: 'FastText Quality', headerColor: 'bg-orange-600', description: 'Quality filter using FastText model score', template: FASTTEXT_QUALITY_FILTER_TEMPLATE, group: 'FastText' },
		{ type: 'transform', label: 'FastText Language ID', headerColor: 'bg-orange-600', description: 'Filter documents by detected language', template: FASTTEXT_LANG_ID_TEMPLATE, group: 'FastText' },
		{ type: 'transform', label: 'FastText Label', headerColor: 'bg-orange-600', description: 'Prepend a FastText label prefix to each document', template: FASTTEXT_LABEL_MODIFIER_TEMPLATE, group: 'FastText' },
		{ type: 'transform', label: 'Histogram Filter', headerColor: 'bg-indigo-600', description: 'Filter by character coverage histogram (multi-language)', template: HISTOGRAM_FILTER_TEMPLATE, group: 'Language Filters' },
		{ type: 'transform', label: 'Token Count', headerColor: 'bg-indigo-600', description: 'Filter by tokenized length using a HF tokenizer', template: TOKEN_COUNT_FILTER_TEMPLATE, group: 'Language Filters' },
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
	let collapsedGroups = new Set<string>(
		NODE_TYPES.map(nt => nt.group).filter((g): g is string => !!g)
	);
	let nodeSearch = '';

	$: filteredNodeTypes = nodeSearch.trim()
    	? NODE_TYPES.filter(nt =>
    	    nt.label.toLowerCase().includes(nodeSearch.toLowerCase()) ||
    	    (nt.group ?? '').toLowerCase().includes(nodeSearch.toLowerCase())
    	  )
    	: NODE_TYPES;


	let canvasEl: HTMLDivElement;
	let containerEl: HTMLDivElement;

	// Connection drawing state
	let draggingConnection: { nodeId: string; port: 'input' | 'output' } | null = null;
	let mousePos = { x: 0, y: 0 };
	let portPositions = new Map<string, { x: number; y: number }>();

	// Node Selected and ContextMenu State
	let selectedNodeId: string | null = null;
	let contextMenuNodeId: string | null = null;

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
		contextMenuNodeId = null;
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

	function toggleGroup(group: string) {
		if (collapsedGroups.has(group)) {
			collapsedGroups.delete(group);
		} else {
			collapsedGroups.add(group);
		}
		collapsedGroups = collapsedGroups;
	}

	function dismissContextMenu() {
		contextMenuVisible = false;
		contextMenuNodeId = null;
		nodeSearch = '';
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

	function deleteNode(id: string) {
		nodes = nodes.filter((n) => n.id !== id);
		connections = connections.filter((c) => c.fromId !== id && c.toId !== id);
		if (selectedNodeId === id) selectedNodeId = null;
		dispatch('configchange', { nodes, connections });
	}

	function handleNodeContextMenu(e: CustomEvent<{id: string; clientX: number; clientY: number;}>) {
		const rel = canvasRelative ({ clientX: e.detail.clientX, clientY: e.detail.clientY} as MouseEvent);
		contextMenuX = rel.x;
		contextMenuY = rel.y;
		selectedNodeId = e.detail.id;
		contextMenuNodeId = e.detail.id;
		contextMenuVisible = true;
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
			selectedNodeId = null;
		}
		if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNodeId) {
			const target = e.target as HTMLElement;
			if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA' && target.tagName !== 'SELECT') {
				deleteNode(selectedNodeId);
			}
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
		on:click={() => {dismissContextMenu(); selectedNodeId = null;}}
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
					selected={node.id === selectedNodeId}
					on:move={handleNodeMove}
					on:select={(e) => {selectedNodeId = e.detail.id;} }
					on:nodecontextmenu={handleNodeContextMenu}
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
			class="absolute z-50 min-w-[160px] rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 py-1 text-sm max-h-[70vh] overflow-y-auto"
			style="left: {contextMenuX}px; top: {contextMenuY}px;"
			on:click|stopPropagation
		>
			{#if contextMenuNodeId}
            <div class="px-3 py-1.5 text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Node</div>
            <button
                class="w-full flex items-center gap-2.5 px-3 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 transition text-left"
                on:click={() => { if (contextMenuNodeId) deleteNode(contextMenuNodeId); dismissContextMenu(); }}

            >
                Delete node
            </button>
        {:else}
			<div class="px-3 py-1.5 text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Add Node</div>
			<div class="px-2 pt-1.5 pb-1">
			    <input
			        type="text"
			        bind:value={nodeSearch}
			        placeholder="Search nodes…"
			        class="w-full rounded-lg px-2 py-1 text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 outline-none"
			        on:click|stopPropagation
			    />
			</div>
			{#each filteredNodeTypes as nt, i}
				{#if nt.group && (i === 0 || filteredNodeTypes[i - 1].group !== nt.group)}
				<button
						    class="w-full flex items-center gap-1.5 px-3 pt-2 pb-0.5 text-[10px] uppercase tracking-wider text-gray-400 font-semibold border-t border-gray-100 dark:border-gray-800 mt-1 hover:text-gray-600 dark:hover:text-gray-300 transition"
						    on:click|stopPropagation={() => toggleGroup(nt.group)}
						>
						   <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-2.5 transition-transform {collapsedGroups.has(nt.group) ? '' : 'rotate-90'}">
							<path fill-rule="evenodd" d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L9.19 8 6.22 5.03a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
						</svg>
						{nt.group}
					</button>
				{/if}
				{#if !collapsedGroups.has(nt.group ?? '')}
					<button
						class="w-full flex items-center gap-2.5 px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800 transition text-left"
						on:click={() => addNode(nt.type, nt.label, nt.headerColor, nt.template)}
					>
						<span class="w-2 h-2 rounded-full flex-shrink-0 {nt.headerColor}"></span>
						<span class="font-medium text-gray-700 dark:text-gray-200">{nt.label}</span>
						<span class="text-gray-400 text-[11px] truncate">{nt.description}</span>
				</button>
				{/if}	
			{/each}
		{/if}
		</div>
	{/if}
</div>
