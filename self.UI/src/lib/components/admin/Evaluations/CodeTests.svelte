<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		getCodeTestsSummary,
		getCodeTestsBenchmark,
		getModelRuns,
		getCodeTestDetails
	} from '$lib/apis/evaluations/codetests';

	const i18n = getContext('i18n');

	// ── Types ──────────────────────────────────────────────────────────
	type SummaryModel = {
		model: string;
		benchmarks: Record<string, number>;
		average: number;
		runs: number;
	};

	type BenchmarkRow = {
		model: string;
		result_id: string;
		q1: number;
		q2: number;
		q3: number;
		q4: number;
		total: number;
	};

	type RunSummary = {
		id: string;
		filename: string;
		model: string;
		tasks: string;
		scores: Record<string, Record<string, number>>;
		config: Record<string, any>;
		created_at: string | null;
	};

	type TaskDetail = {
		task_id: string;
		prompt: string;
		entry_point: string;
		canonical_solution: string;
		reference_test: string;
		samples: {
			completion_id: number;
			generation: string;
			completion: string;
			passed: boolean;
			result: string;
		}[];
	};

	// ── View state ─────────────────────────────────────────────────────
	// 'tabs' = main tabbed view, 'model-runs' = model run list, 'run-details' = single run detail
	type ViewMode = 'tabs' | 'model-runs' | 'run-details';
	let viewMode: ViewMode = 'tabs';

	// Tab state
	let activeTab = 'general';
	let benchmarkNames: string[] = [];

	// General tab
	let summaryModels: SummaryModel[] = [];
	let summaryLoading = true;
	let summarySortKey = 'model';
	let summarySortAsc = true;

	// Benchmark tabs
	let benchmarkRows: BenchmarkRow[] = [];
	let benchmarkLoading = false;
	let benchmarkSortKey = 'model';
	let benchmarkSortAsc = true;
	let loadedBenchmark = '';

	// Model runs view
	let selectedModelName = '';
	let modelRuns: RunSummary[] = [];
	let modelRunsLoading = false;

	// Run detail view
	let selectedRun: RunSummary | null = null;
	let details: TaskDetail[] = [];
	let detailsLoading = false;
	let expandedTask: string | null = null;
	let filterStatus: 'all' | 'passed' | 'failed' = 'all';

	// ── Derived ────────────────────────────────────────────────────────
	$: sortedSummary = [...summaryModels].sort((a, b) => {
		let va: any, vb: any;
		if (summarySortKey === 'model') {
			va = a.model.toLowerCase();
			vb = b.model.toLowerCase();
		} else if (summarySortKey === 'average') {
			va = a.average;
			vb = b.average;
		} else {
			va = a.benchmarks[summarySortKey] ?? -1;
			vb = b.benchmarks[summarySortKey] ?? -1;
		}
		if (va < vb) return summarySortAsc ? -1 : 1;
		if (va > vb) return summarySortAsc ? 1 : -1;
		return 0;
	});

	$: sortedBenchmarkRows = [...benchmarkRows].sort((a, b) => {
		const va = (a as any)[benchmarkSortKey] ?? '';
		const vb = (b as any)[benchmarkSortKey] ?? '';
		const aVal = typeof va === 'string' ? va.toLowerCase() : va;
		const bVal = typeof vb === 'string' ? vb.toLowerCase() : vb;
		if (aVal < bVal) return benchmarkSortAsc ? -1 : 1;
		if (aVal > bVal) return benchmarkSortAsc ? 1 : -1;
		return 0;
	});

	$: passedCount = details.filter((d) => d.samples.every((s) => s.passed)).length;
	$: failedCount = details.filter((d) => d.samples.some((s) => !s.passed)).length;
	$: totalCount = details.length;

	$: filteredDetails = details.filter((d) => {
		if (filterStatus === 'all') return true;
		if (filterStatus === 'passed') return d.samples.every((s) => s.passed);
		if (filterStatus === 'failed') return d.samples.some((s) => !s.passed);
		return true;
	});

	// ── Actions ────────────────────────────────────────────────────────
	async function loadSummary() {
		summaryLoading = true;
		try {
			const data = await getCodeTestsSummary(localStorage.token);
			if (data) {
				summaryModels = data.models ?? [];
				benchmarkNames = data.benchmark_names ?? [];
			}
		} catch (err) {
			toast.error(`Failed to load summary: ${err}`);
		}
		summaryLoading = false;
	}

	async function loadBenchmark(benchmark: string) {
		if (loadedBenchmark === benchmark && benchmarkRows.length > 0) return;
		benchmarkLoading = true;
		benchmarkSortKey = 'model';
		benchmarkSortAsc = true;
		try {
			const data = await getCodeTestsBenchmark(localStorage.token, benchmark);
			if (data) {
				benchmarkRows = data.rows ?? [];
				loadedBenchmark = benchmark;
			}
		} catch (err) {
			toast.error(`Failed to load benchmark data: ${err}`);
			benchmarkRows = [];
		}
		benchmarkLoading = false;
	}

	function selectTab(tab: string) {
		activeTab = tab;
		if (tab !== 'general') {
			loadBenchmark(tab);
		}
	}

	async function selectModel(modelName: string) {
		selectedModelName = modelName;
		viewMode = 'model-runs';
		modelRunsLoading = true;
		try {
			modelRuns = (await getModelRuns(localStorage.token, modelName)) ?? [];
		} catch (err) {
			toast.error(`Failed to load model runs: ${err}`);
			modelRuns = [];
		}
		modelRunsLoading = false;
	}

	async function selectRunDetail(run: RunSummary) {
		selectedRun = run;
		viewMode = 'run-details';
		detailsLoading = true;
		expandedTask = null;
		filterStatus = 'all';
		try {
			details = (await getCodeTestDetails(localStorage.token, run.id)) ?? [];
		} catch (err) {
			toast.error(`Failed to load details: ${err}`);
			details = [];
		}
		detailsLoading = false;
	}

	function goBackToTabs() {
		viewMode = 'tabs';
		selectedModelName = '';
		modelRuns = [];
	}

	function goBackToModelRuns() {
		viewMode = 'model-runs';
		selectedRun = null;
		details = [];
		expandedTask = null;
	}

	function toggleTask(taskId: string) {
		expandedTask = expandedTask === taskId ? null : taskId;
	}

	function toggleSummarySort(key: string) {
		if (summarySortKey === key) {
			summarySortAsc = !summarySortAsc;
		} else {
			summarySortKey = key;
			summarySortAsc = key === 'model';
		}
	}

	function toggleBenchmarkSort(key: string) {
		if (benchmarkSortKey === key) {
			benchmarkSortAsc = !benchmarkSortAsc;
		} else {
			benchmarkSortKey = key;
			benchmarkSortAsc = key === 'model';
		}
	}

	function scoreColor(score: number): string {
		if (score >= 70) return 'text-green-500';
		if (score >= 40) return 'text-yellow-500';
		return 'text-red-500';
	}

	function formatPassRate(scores: Record<string, Record<string, number>>): string {
		for (const [, metrics] of Object.entries(scores)) {
			if (metrics['pass@1'] !== undefined) {
				return `${(metrics['pass@1'] * 100).toFixed(1)}%`;
			}
		}
		return '-';
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		try {
			const d = new Date(dateStr);
			return d.toLocaleString();
		} catch {
			return dateStr;
		}
	}

	onMount(() => {
		loadSummary();
	});
</script>

<!-- ── Header / Breadcrumbs ──────────────────────────────────────── -->
<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5 shrink-0 items-center">
		{#if viewMode === 'run-details' && selectedRun}
			<button
				class="flex items-center gap-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mr-2"
				on:click={goBackToModelRuns}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
					<path fill-rule="evenodd" d="M9.78 4.22a.75.75 0 0 1 0 1.06L7.06 8l2.72 2.72a.75.75 0 1 1-1.06 1.06L5.47 8.53a.75.75 0 0 1 0-1.06l3.25-3.25a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd" />
				</svg>
			</button>
			<div class="gap-1">
				{selectedRun.model}
				<span class="text-sm text-gray-500 ml-1">({selectedRun.tasks} &mdash; {selectedRun.id})</span>
			</div>
		{:else if viewMode === 'model-runs'}
			<button
				class="flex items-center gap-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mr-2"
				on:click={goBackToTabs}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
					<path fill-rule="evenodd" d="M9.78 4.22a.75.75 0 0 1 0 1.06L7.06 8l2.72 2.72a.75.75 0 1 1-1.06 1.06L5.47 8.53a.75.75 0 0 1 0-1.06l3.25-3.25a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd" />
				</svg>
			</button>
			<div class="gap-1">
				{selectedModelName}
				<span class="text-sm text-gray-500 ml-1">(Runs)</span>
			</div>
		{:else}
			<div class="gap-1">
				{$i18n.t('Code Tests')}
			</div>
		{/if}

		{#if viewMode === 'run-details' && !detailsLoading}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
			<div class="flex items-center gap-3 text-sm">
				<span class="text-green-500 font-medium">{passedCount} passed</span>
				<span class="text-red-500 font-medium">{failedCount} failed</span>
				<span class="text-gray-500">{totalCount} total</span>
			</div>
		{/if}
	</div>

	{#if viewMode === 'run-details' && !detailsLoading}
		<div class="flex items-center gap-1.5 text-sm">
			<button
				class="px-2 py-0.5 rounded {filterStatus === 'all'
					? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
					: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
				on:click={() => (filterStatus = 'all')}
			>
				All
			</button>
			<button
				class="px-2 py-0.5 rounded {filterStatus === 'passed'
					? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
					: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
				on:click={() => (filterStatus = 'passed')}
			>
				Passed
			</button>
			<button
				class="px-2 py-0.5 rounded {filterStatus === 'failed'
					? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400'
					: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}"
				on:click={() => (filterStatus = 'failed')}
			>
				Failed
			</button>
		</div>
	{/if}
</div>

<!-- ── Main content ──────────────────────────────────────────────── -->
{#if viewMode === 'tabs'}
	<!-- Tab bar -->
	<div class="flex border-b border-gray-200 dark:border-gray-700 mb-3 overflow-x-auto scrollbar-hidden">
		<button
			class="px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors
				{activeTab === 'general'
					? 'border-blue-500 text-blue-600 dark:text-blue-400'
					: 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'}"
			on:click={() => selectTab('general')}
		>
			General
		</button>
		{#each benchmarkNames as bm}
			<button
				class="px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors capitalize
					{activeTab === bm
						? 'border-blue-500 text-blue-600 dark:text-blue-400'
						: 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'}"
				on:click={() => selectTab(bm)}
			>
				{bm}
			</button>
		{/each}
	</div>

	{#if activeTab === 'general'}
		<!-- ── General Tab ────────────────────────────────────────── -->
		{#if summaryLoading}
			<div class="flex justify-center py-8"><Spinner /></div>
		{:else if summaryModels.length === 0}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-6">
				{$i18n.t('No code test results found. Run a bigcode evaluation to see results here.')}
			</div>
		{:else}
			<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
				<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
					<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
						<tr>
							<th
								scope="col"
								class="px-3 py-1.5 cursor-pointer select-none hover:text-gray-900 dark:hover:text-white"
								on:click={() => toggleSummarySort('model')}
							>
								<div class="flex items-center gap-1">
									Model
									{#if summarySortKey === 'model'}
										<span class="text-blue-500">{summarySortAsc ? '▲' : '▼'}</span>
									{/if}
								</div>
							</th>
							{#each benchmarkNames as bm}
								<th
									scope="col"
									class="px-3 py-1.5 text-right cursor-pointer select-none hover:text-gray-900 dark:hover:text-white capitalize"
									on:click={() => toggleSummarySort(bm)}
								>
									<div class="flex items-center justify-end gap-1">
										{bm}
										{#if summarySortKey === bm}
											<span class="text-blue-500">{summarySortAsc ? '▲' : '▼'}</span>
										{/if}
									</div>
								</th>
							{/each}
							<th
								scope="col"
								class="px-3 py-1.5 text-right cursor-pointer select-none hover:text-gray-900 dark:hover:text-white"
								on:click={() => toggleSummarySort('average')}
							>
								<div class="flex items-center justify-end gap-1">
									Average
									{#if summarySortKey === 'average'}
										<span class="text-blue-500">{summarySortAsc ? '▲' : '▼'}</span>
									{/if}
								</div>
							</th>
						</tr>
					</thead>
					<tbody>
						{#each sortedSummary as row (row.model)}
							<tr
								class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50 cursor-pointer"
								on:click={() => selectModel(row.model)}
							>
								<td class="px-3 py-2 font-medium text-gray-900 dark:text-white">
									{row.model}
								</td>
								{#each benchmarkNames as bm}
									<td class="px-3 py-2 text-right font-semibold">
										{#if row.benchmarks[bm] !== undefined}
											<span class={scoreColor(row.benchmarks[bm])}>
												{row.benchmarks[bm].toFixed(1)}%
											</span>
										{:else}
											<span class="text-gray-400">-</span>
										{/if}
									</td>
								{/each}
								<td class="px-3 py-2 text-right font-bold">
									<span class={scoreColor(row.average)}>
										{row.average.toFixed(1)}%
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{:else}
		<!-- ── Benchmark Tab (quartiles) ─────────────────────────── -->
		{#if benchmarkLoading}
			<div class="flex justify-center py-8"><Spinner /></div>
		{:else if benchmarkRows.length === 0}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-6">
				No results for this benchmark.
			</div>
		{:else}
			<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
				<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
					<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
						<tr>
							<th
								scope="col"
								class="px-3 py-1.5 cursor-pointer select-none hover:text-gray-900 dark:hover:text-white"
								on:click={() => toggleBenchmarkSort('model')}
							>
								<div class="flex items-center gap-1">
									Model
									{#if benchmarkSortKey === 'model'}
										<span class="text-blue-500">{benchmarkSortAsc ? '▲' : '▼'}</span>
									{/if}
								</div>
							</th>
							{#each ['q1', 'q2', 'q3', 'q4'] as q}
								<th
									scope="col"
									class="px-3 py-1.5 text-right cursor-pointer select-none hover:text-gray-900 dark:hover:text-white uppercase"
									on:click={() => toggleBenchmarkSort(q)}
								>
									<div class="flex items-center justify-end gap-1">
										{q}
										{#if benchmarkSortKey === q}
											<span class="text-blue-500">{benchmarkSortAsc ? '▲' : '▼'}</span>
										{/if}
									</div>
								</th>
							{/each}
							<th
								scope="col"
								class="px-3 py-1.5 text-right cursor-pointer select-none hover:text-gray-900 dark:hover:text-white"
								on:click={() => toggleBenchmarkSort('total')}
							>
								<div class="flex items-center justify-end gap-1">
									Total
									{#if benchmarkSortKey === 'total'}
										<span class="text-blue-500">{benchmarkSortAsc ? '▲' : '▼'}</span>
									{/if}
								</div>
							</th>
						</tr>
					</thead>
					<tbody>
						{#each sortedBenchmarkRows as row (row.model)}
							<tr
								class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50 cursor-pointer"
								on:click={() => selectModel(row.model)}
							>
								<td class="px-3 py-2 font-medium text-gray-900 dark:text-white">
									{row.model}
								</td>
								{#each ['q1', 'q2', 'q3', 'q4'] as q}
									<td class="px-3 py-2 text-right font-semibold">
										<span class={scoreColor(row[q])}>
											{row[q].toFixed(1)}%
										</span>
									</td>
								{/each}
								<td class="px-3 py-2 text-right font-bold">
									<span class={scoreColor(row.total)}>
										{row.total.toFixed(1)}%
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}

{:else if viewMode === 'model-runs'}
	<!-- ── Model Runs List ────────────────────────────────────────── -->
	{#if modelRunsLoading}
		<div class="flex justify-center py-8"><Spinner /></div>
	{:else if modelRuns.length === 0}
		<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-6">
			No runs found for this model.
		</div>
	{:else}
		<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
			<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
				<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
					<tr>
						<th scope="col" class="px-3 py-1.5">Run ID</th>
						<th scope="col" class="px-3 py-1.5">Benchmark</th>
						<th scope="col" class="px-3 py-1.5 text-right">pass@1</th>
						<th scope="col" class="px-3 py-1.5">Date</th>
						<th scope="col" class="px-3 py-1.5 text-right">Details</th>
					</tr>
				</thead>
				<tbody>
					{#each modelRuns as run (run.id)}
						<tr
							class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50 cursor-pointer"
							on:click={() => selectRunDetail(run)}
						>
							<td class="px-3 py-2 font-mono text-gray-900 dark:text-white">
								{run.id}
							</td>
							<td class="px-3 py-2 capitalize">{run.tasks}</td>
							<td class="px-3 py-2 text-right font-semibold">
								<span class={parseFloat(formatPassRate(run.scores)) >= 50 ? 'text-green-500' : 'text-red-500'}>
									{formatPassRate(run.scores)}
								</span>
							</td>
							<td class="px-3 py-2 text-gray-500">
								{formatDate(run.created_at)}
							</td>
							<td class="px-3 py-2 text-right">
								<button class="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300">
									View
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

{:else if viewMode === 'run-details'}
	<!-- ── Run Detail View ────────────────────────────────────────── -->
	{#if detailsLoading}
		<div class="flex justify-center py-8"><Spinner /></div>
	{:else}
		<div class="space-y-1 max-h-[calc(100vh-16rem)] overflow-y-auto">
			{#each filteredDetails as task (task.task_id)}
				{@const allPassed = task.samples.every((s) => s.passed)}
				<div class="rounded border border-gray-100 dark:border-gray-800">
					<button
						class="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-850/50"
						on:click={() => toggleTask(task.task_id)}
					>
						<div class="flex items-center gap-2 text-xs">
							<span
								class="inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold {allPassed
									? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
									: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'}"
							>
								{allPassed ? '✓' : '✗'}
							</span>
							<span class="font-mono font-medium text-gray-900 dark:text-white">
								{task.task_id}
							</span>
							<span class="text-gray-500">
								{task.entry_point}
							</span>
						</div>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-3 text-gray-400 transition-transform {expandedTask === task.task_id ? 'rotate-180' : ''}"
						>
							<path fill-rule="evenodd" d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
						</svg>
					</button>

					{#if expandedTask === task.task_id}
						<div class="border-t border-gray-100 dark:border-gray-800 px-3 py-2 space-y-3">
							<!-- Prompt -->
							<div>
								<div class="text-[10px] uppercase font-semibold text-gray-500 mb-1">Prompt</div>
								<pre class="text-xs bg-gray-50 dark:bg-gray-850 rounded p-2 overflow-x-auto whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">{task.prompt}</pre>
							</div>

							<!-- Entry Point -->
							<div>
								<div class="text-[10px] uppercase font-semibold text-gray-500 mb-1">Entry Point</div>
								<code class="text-xs font-mono bg-gray-50 dark:bg-gray-850 rounded px-2 py-1">{task.entry_point}</code>
							</div>

							<!-- Samples / Completions -->
							{#each task.samples as sample, idx}
								<div>
									<div class="flex items-center gap-2 mb-1">
										<span class="text-[10px] uppercase font-semibold text-gray-500">Sample {idx + 1}</span>
										<span
											class="text-[10px] px-1.5 py-0.5 rounded font-medium {sample.passed
												? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
												: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'}"
										>
											{sample.result}
										</span>
									</div>
									{#if sample.completion}
										<div class="text-[10px] uppercase font-semibold text-gray-400 mb-0.5 mt-1">Completion</div>
										<pre class="text-xs bg-gray-50 dark:bg-gray-850 rounded p-2 overflow-x-auto whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">{sample.completion}</pre>
									{/if}
									<div class="text-[10px] uppercase font-semibold text-gray-400 mb-0.5 mt-1">Full Generation</div>
									<pre class="text-xs bg-gray-50 dark:bg-gray-850 rounded p-2 overflow-x-auto whitespace-pre-wrap font-mono max-h-64 overflow-y-auto">{sample.generation}</pre>
								</div>
							{/each}

							<!-- Canonical solution -->
							<div>
								<div class="text-[10px] uppercase font-semibold text-gray-500 mb-1">Reference Solution</div>
								<pre class="text-xs bg-gray-50 dark:bg-gray-850 rounded p-2 overflow-x-auto whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">{task.canonical_solution}</pre>
							</div>

							<!-- Reference test -->
							{#if task.reference_test}
								<div>
									<div class="text-[10px] uppercase font-semibold text-gray-500 mb-1">Reference Test</div>
									<pre class="text-xs bg-gray-50 dark:bg-gray-850 rounded p-2 overflow-x-auto whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">{task.reference_test}</pre>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{/if}
