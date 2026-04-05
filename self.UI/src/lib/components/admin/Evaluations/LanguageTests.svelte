<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import LiveEvalView from '$lib/components/admin/Evaluations/LiveEvalView.svelte';
	import {
		getLangTestsSummary,
		getLangModelRuns,
	} from '$lib/apis/evaluations/langtests';
	import type { EvalJob } from '$lib/apis/evaluations/jobs';

	const i18n = getContext('i18n');

	// ── Types ──────────────────────────────────────────────────────────
	type SummaryModel = {
		model: string;
		benchmarks: Record<string, number>;
		average: number;
		runs: number;
	};

	type RunSummary = {
		id: string;
		model: string;
		benchmarks: Record<string, number>;
		total_samples: number;
		eval_time: string | null;
		created_at: string | null;
		config: Record<string, any>;
		results_file: string;
	};

	// ── View state ─────────────────────────────────────────────────────
	type ViewMode = 'summary' | 'model-runs' | 'run-details';
	let viewMode: ViewMode = 'summary';

	// Summary
	let summaryModels: SummaryModel[] = [];
	let benchmarkNames: string[] = [];
	let summaryLoading = true;
	let summarySortKey = 'model';
	let summarySortAsc = true;

	// Model runs view
	let selectedModelName = '';
	let modelRuns: RunSummary[] = [];
	let modelRunsLoading = false;

	// Run detail view — uses LiveEvalView
	let selectedRun: RunSummary | null = null;
	let activeDetailJob: EvalJob | null = null;

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

	// ── Actions ────────────────────────────────────────────────────────
	async function loadSummary() {
		summaryLoading = true;
		try {
			const data = await getLangTestsSummary(localStorage.token);
			if (data) {
				summaryModels = data.models ?? [];
				benchmarkNames = data.benchmark_names ?? [];
			}
		} catch (err) {
			toast.error(`Failed to load language test summary: ${err}`);
		}
		summaryLoading = false;
	}

	async function selectModel(modelName: string) {
		selectedModelName = modelName;
		viewMode = 'model-runs';
		modelRunsLoading = true;
		try {
			modelRuns = (await getLangModelRuns(localStorage.token, modelName)) ?? [];
		} catch (err) {
			toast.error(`Failed to load model runs: ${err}`);
			modelRuns = [];
		}
		modelRunsLoading = false;
	}

	function selectRunDetail(run: RunSummary) {
		selectedRun = run;
		// Construct a minimal EvalJob-like object for LiveEvalView
		activeDetailJob = {
			id: run.id,
			user_id: '',
			eval_type: 'lm-eval',
			benchmark: Object.keys(run.benchmarks).join(', '),
			model_id: run.model,
			status: 'completed',
			error_message: null,
			meta: { total_samples: run.total_samples },
			created_at: run.created_at ? new Date(run.created_at).getTime() / 1000 : 0,
			updated_at: 0,
			user: null,
		};
		viewMode = 'run-details';
	}

	function goBackToSummary() {
		viewMode = 'summary';
		selectedModelName = '';
		modelRuns = [];
	}

	function goBackToModelRuns() {
		viewMode = 'model-runs';
		selectedRun = null;
		activeDetailJob = null;
	}

	function toggleSummarySort(key: string) {
		if (summarySortKey === key) {
			summarySortAsc = !summarySortAsc;
		} else {
			summarySortKey = key;
			summarySortAsc = key === 'model';
		}
	}

	function scoreColor(score: number): string {
		if (score >= 70) return 'text-green-500';
		if (score >= 40) return 'text-yellow-500';
		return 'text-red-500';
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

	function formatEvalTime(seconds: string | null): string {
		if (!seconds) return '-';
		const s = parseFloat(seconds);
		if (isNaN(s)) return '-';
		if (s < 60) return `${s.toFixed(0)}s`;
		if (s < 3600) return `${(s / 60).toFixed(1)}m`;
		return `${(s / 3600).toFixed(1)}h`;
	}

	function formatBenchmarkScores(benchmarks: Record<string, number>): string {
		return Object.entries(benchmarks)
			.map(([k, v]) => `${k}: ${v.toFixed(1)}%`)
			.join(', ');
	}

	function formatBenchmarkName(name: string): string {
		return name.replace('leaderboard_', '').replace(/_/g, ' ');
	}

	onMount(() => {
		loadSummary();
	});
</script>

<!-- ── Header / Breadcrumbs (hidden in run-details since LiveEvalView has its own) ── -->
{#if viewMode !== 'run-details'}
<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5 shrink-0 items-center">
		{#if viewMode === 'model-runs'}
			<button
				class="flex items-center gap-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 mr-2"
				on:click={goBackToSummary}
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
				{$i18n.t('Language Tests')}
			</div>
		{/if}
	</div>
</div>
{/if}

<!-- ── Main content ──────────────────────────────────────────────── -->
{#if viewMode === 'summary'}
	{#if summaryLoading}
		<div class="flex justify-center py-8"><Spinner /></div>
	{:else if summaryModels.length === 0}
		<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-6">
			{$i18n.t('No language test results found. Run an lm-eval benchmark to see results here.')}
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
									{formatBenchmarkName(bm)}
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
						<th scope="col" class="px-3 py-1.5">Job ID</th>
						<th scope="col" class="px-3 py-1.5">Benchmarks</th>
						<th scope="col" class="px-3 py-1.5 text-right">Samples</th>
						<th scope="col" class="px-3 py-1.5 text-right">Duration</th>
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
							<td class="px-3 py-2">
								{formatBenchmarkScores(run.benchmarks)}
							</td>
							<td class="px-3 py-2 text-right">{run.total_samples}</td>
							<td class="px-3 py-2 text-right">{formatEvalTime(run.eval_time)}</td>
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
	<!-- ── Run Detail View — uses unified LiveEvalView ────────── -->
	{#if activeDetailJob}
		<LiveEvalView job={activeDetailJob} on:back={goBackToModelRuns} />
	{/if}
{/if}
