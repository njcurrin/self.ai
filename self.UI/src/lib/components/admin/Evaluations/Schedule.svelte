<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LiveEvalView from '$lib/components/admin/Evaluations/LiveEvalView.svelte';
	import {
		getEvalJobs,
		createEvalJob,
		approveEvalJob,
		rejectEvalJob,
		cancelEvalJob,
		deleteEvalJob,
		type EvalJob
	} from '$lib/apis/evaluations/jobs';
	import { getModels } from '$lib/apis/index';

	const i18n = getContext('i18n');

	let loaded = false;
	let submitting = false;
	let jobs: EvalJob[] = [];
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	let modelItems: { value: string; label: string }[] = [];
	let activeJob: EvalJob | null = null;

	// Ad-hoc run form
	let showRunForm = false;
	let runEvalType: 'bigcode' | 'lm-eval' = 'bigcode';
	let runBenchmark = 'humaneval';
	let runModelId = '';
	let modelSearch = '';
	let showModelDropdown = false;
	let runDryRun = false;

	$: filteredModels = modelSearch
		? modelItems.filter(
				(m) =>
					m.label.toLowerCase().includes(modelSearch.toLowerCase()) ||
					m.value.toLowerCase().includes(modelSearch.toLowerCase())
		  )
		: modelItems;

	const loadModels = async () => {
		try {
			const allModels = await getModels(localStorage.token);
			modelItems = (allModels ?? []).map((m: any) => ({
				value: m.id,
				label: m.name ?? m.id
			}));
		} catch (e) {
			console.error('Failed to load models:', e);
		}
	};

	const bigcodeBenchmarkOptions = [
		// HumanEval
		{ id: 'humaneval', name: 'HumanEval' },
		{ id: 'humanevalplus', name: 'HumanEval+' },
		// MBPP
		{ id: 'mbpp', name: 'MBPP' },
		{ id: 'mbppplus', name: 'MBPP+' },
		// APPS
		{ id: 'apps-introductory', name: 'APPS Introductory' },
		{ id: 'apps-interview', name: 'APPS Interview' },
		{ id: 'apps-competition', name: 'APPS Competition' },
		// DS-1000
		{ id: 'ds1000-all-completion', name: 'DS-1000 (All)' },
		{ id: 'ds1000-numpy-completion', name: 'DS-1000 NumPy' },
		{ id: 'ds1000-pandas-completion', name: 'DS-1000 Pandas' },
		{ id: 'ds1000-scipy-completion', name: 'DS-1000 SciPy' },
		{ id: 'ds1000-matplotlib-completion', name: 'DS-1000 Matplotlib' },
		{ id: 'ds1000-sklearn-completion', name: 'DS-1000 Sklearn' },
		{ id: 'ds1000-tensorflow-completion', name: 'DS-1000 TensorFlow' },
		{ id: 'ds1000-pytorch-completion', name: 'DS-1000 PyTorch' },
		// MultiPL-E
		{ id: 'multiple-py', name: 'MultiPL-E Python' },
		{ id: 'multiple-js', name: 'MultiPL-E JavaScript' },
		{ id: 'multiple-ts', name: 'MultiPL-E TypeScript' },
		{ id: 'multiple-java', name: 'MultiPL-E Java' },
		{ id: 'multiple-cpp', name: 'MultiPL-E C++' },
		{ id: 'multiple-cs', name: 'MultiPL-E C#' },
		{ id: 'multiple-go', name: 'MultiPL-E Go' },
		{ id: 'multiple-rs', name: 'MultiPL-E Rust' },
		{ id: 'multiple-rb', name: 'MultiPL-E Ruby' },
		{ id: 'multiple-php', name: 'MultiPL-E PHP' },
		{ id: 'multiple-sh', name: 'MultiPL-E Bash' },
		{ id: 'multiple-swift', name: 'MultiPL-E Swift' },
		{ id: 'multiple-scala', name: 'MultiPL-E Scala' },
		{ id: 'multiple-hs', name: 'MultiPL-E Haskell' },
		{ id: 'multiple-lua', name: 'MultiPL-E Lua' },
		{ id: 'multiple-r', name: 'MultiPL-E R' },
		{ id: 'multiple-jl', name: 'MultiPL-E Julia' },
		{ id: 'multiple-clj', name: 'MultiPL-E Clojure' },
		{ id: 'multiple-ml', name: 'MultiPL-E OCaml' },
		{ id: 'multiple-pl', name: 'MultiPL-E Perl' },
		{ id: 'multiple-d', name: 'MultiPL-E D' },
		{ id: 'multiple-dart', name: 'MultiPL-E Dart' },
		{ id: 'multiple-elixir', name: 'MultiPL-E Elixir' },
		{ id: 'multiple-rkt', name: 'MultiPL-E Racket' }
	];

	const lmEvalBenchmarkOptions = [
		// Leaderboard v2
		{ id: 'leaderboard', name: 'Leaderboard v2 (Full Suite)' },
		{ id: 'leaderboard_ifeval', name: 'IFEval' },
		{ id: 'bbh_cot_zeroshot', name: 'BBH (CoT Zero-shot)' },
		{ id: 'bbh_cot_fewshot', name: 'BBH (CoT Few-shot)' },
		{ id: 'leaderboard_math_hard', name: 'MATH Hard' },
		{ id: 'leaderboard_gpqa', name: 'GPQA' },
		{ id: 'leaderboard_musr', name: 'MUSR' },
		{ id: 'leaderboard_mmlu_pro', name: 'MMLU-PRO' },
		// Classic benchmarks
		{ id: 'arc_challenge', name: 'ARC Challenge' },
		{ id: 'hellaswag', name: 'HellaSwag' },
		{ id: 'mmlu', name: 'MMLU' },
		{ id: 'truthfulqa_mc2', name: 'TruthfulQA MC2' },
		{ id: 'winogrande', name: 'Winogrande' },
		{ id: 'gsm8k', name: 'GSM8K' },
	];

	$: benchmarkOptions = runEvalType === 'lm-eval' ? lmEvalBenchmarkOptions : bigcodeBenchmarkOptions;

	const statusColor = (s: string) => {
		switch (s) {
			case 'completed': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'running': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			case 'queued': return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
			case 'scheduled': return 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400';
			case 'pending': return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
			case 'failed': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
			case 'cancelled': return 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500';
			default: return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
		}
	};

	const GROUP_NAMES: Record<string, string> = {
		'humaneval': 'HumanEval',
		'mbpp': 'MBPP',
		'apps': 'APPS',
		'ds1000': 'DS-1000',
		'multiple': 'MultiPL-E',
	};

	const getBenchmarkName = (id: string) => {
		if (!id.includes(',')) {
			const allOptions = [...bigcodeBenchmarkOptions, ...lmEvalBenchmarkOptions];
			return allOptions.find((b) => b.id === id)?.name ?? id;
		}
		// Comma-separated list — resolve to group name
		const first = id.split(',')[0].trim();
		for (const [prefix, label] of Object.entries(GROUP_NAMES)) {
			if (first === prefix || first.startsWith(prefix + '-')) return label;
		}
		return id;
	};

	const handleStartRun = async () => {
		if (!runDryRun && !runModelId.trim()) {
			toast.error($i18n.t('Please enter a model ID.'));
			return;
		}
		submitting = true;
		try {
			const effectiveModelId = runDryRun ? 'dry_run' : runModelId.trim();
		await createEvalJob(localStorage.token, runBenchmark, effectiveModelId, runEvalType, undefined, runDryRun);
			toast.success($i18n.t('Evaluation job created.'));
			showRunForm = false;
			runModelId = '';
			jobs = await getEvalJobs(localStorage.token);
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to create evaluation job.'));
		} finally {
			submitting = false;
		}
	};

	const handleApprove = async (id: string) => {
		try {
			await approveEvalJob(localStorage.token, id);
			jobs = await getEvalJobs(localStorage.token);
			toast.success($i18n.t('Job approved and dispatched.'));
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to approve job.'));
		}
	};

	const handleReject = async (id: string) => {
		try {
			await rejectEvalJob(localStorage.token, id);
			jobs = await getEvalJobs(localStorage.token);
			toast.success($i18n.t('Job rejected.'));
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to reject job.'));
		}
	};

	const handleCancel = async (id: string) => {
		try {
			await cancelEvalJob(localStorage.token, id);
			jobs = await getEvalJobs(localStorage.token);
			toast.success($i18n.t('Job cancelled.'));
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to cancel job.'));
		}
	};

	const handleDelete = async (id: string) => {
		try {
			await deleteEvalJob(localStorage.token, id);
			jobs = jobs.filter((j) => j.id !== id);
			toast.success($i18n.t('Job deleted.'));
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to delete job.'));
		}
	};

	const refreshJobs = async () => {
		try {
			jobs = await getEvalJobs(localStorage.token);
		} catch (e) {
			console.error('Failed to refresh jobs:', e);
		}
	};

	onMount(async () => {
		await refreshJobs();
		loaded = true;

		pollInterval = setInterval(refreshJobs, 8000);
		return () => {
			if (pollInterval) clearInterval(pollInterval);
		};
	});
</script>

{#if activeJob}
	<LiveEvalView job={activeJob} on:back={() => { activeJob = null; }} />
{:else}
<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5 shrink-0 items-center">
		{$i18n.t('Schedule')}
		{#if loaded}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
			<span class="text-sm font-normal text-gray-500">{jobs.length} {$i18n.t('jobs')}</span>
		{/if}
	</div>
	<button
		class="px-3 py-1.5 rounded-xl text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition"
		on:click={async () => { showRunForm = !showRunForm; if (showRunForm && modelItems.length === 0) await loadModels(); }}
	>
		{$i18n.t('Run Evaluation')}
	</button>
</div>

{#if showRunForm}
	<div class="mb-4 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
		<div class="flex items-center justify-between mb-3">
			<div class="font-medium text-sm">{$i18n.t('Start Ad-hoc Evaluation')}</div>
			<button class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition" on:click={() => { showRunForm = false; }}>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-gray-500">
					<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
				</svg>
			</button>
		</div>

		<div class="space-y-3">
			<div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Eval Type')}</div>
				<div class="flex gap-2">
					<button
						type="button"
						class="flex-1 px-3 py-1.5 rounded-xl text-sm font-medium border transition {runEvalType === 'bigcode' ? 'bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-900/20 dark:border-blue-700 dark:text-blue-300' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-900 dark:border-gray-800 dark:text-gray-400 hover:border-gray-300'}"
						on:click={() => { runEvalType = 'bigcode'; runBenchmark = 'humaneval'; }}
					>
						{$i18n.t('Code')}
					</button>
					<button
						type="button"
						class="flex-1 px-3 py-1.5 rounded-xl text-sm font-medium border transition {runEvalType === 'lm-eval' ? 'bg-purple-50 border-purple-300 text-purple-700 dark:bg-purple-900/20 dark:border-purple-700 dark:text-purple-300' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-900 dark:border-gray-800 dark:text-gray-400 hover:border-gray-300'}"
						on:click={() => { runEvalType = 'lm-eval'; runBenchmark = 'leaderboard'; }}
					>
						{$i18n.t('Leaderboard')}
					</button>
				</div>
			</div>

			<div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Benchmark')}</div>
				<select class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800"
					bind:value={runBenchmark}>
					{#each benchmarkOptions as bm}
						<option value={bm.id}>{bm.name}</option>
					{/each}
				</select>
			</div>

			<div class="relative">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Model')}</div>
				{#if runDryRun}
					<div
						class="w-full rounded-xl px-3 py-2 text-sm text-left bg-gray-100 dark:bg-gray-850 text-gray-400 dark:text-gray-500 border border-gray-200 dark:border-gray-800 cursor-not-allowed italic"
					>
						dry_run
					</div>
				{:else}
					<button
						type="button"
						class="w-full rounded-xl px-3 py-2 text-sm text-left bg-gray-50 dark:bg-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-800 flex items-center justify-between"
						on:click={() => { showModelDropdown = !showModelDropdown; modelSearch = ''; }}
					>
						<span class={runModelId ? '' : 'text-gray-400'}>
							{runModelId ? (modelItems.find((m) => m.value === runModelId)?.label ?? runModelId) : $i18n.t('Select a model')}
						</span>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-gray-400">
							<path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clip-rule="evenodd" />
						</svg>
					</button>

					{#if showModelDropdown}
						<div class="absolute z-10 mt-1 w-full rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-lg">
							<div class="p-2">
								<input
									class="w-full rounded-lg px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800"
									bind:value={modelSearch}
									placeholder={$i18n.t('Search models...')}
								/>
							</div>
							<div class="max-h-48 overflow-y-auto px-1 pb-1">
								{#each filteredModels as model}
									<button
										type="button"
										class="w-full text-left px-3 py-1.5 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition {runModelId === model.value ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}"
										on:click={() => { runModelId = model.value; showModelDropdown = false; }}
									>
										{model.label}
									</button>
								{:else}
									<div class="px-3 py-2 text-sm text-gray-400">{$i18n.t('No models found')}</div>
								{/each}
							</div>
						</div>
					{/if}
				{/if}
			</div>

			<div class="flex items-center gap-2 pt-1">
				<label class="flex items-center gap-2 cursor-pointer select-none">
					<input
						type="checkbox"
						bind:checked={runDryRun}
						on:change={() => { if (runDryRun) showModelDropdown = false; }}
						class="rounded border-gray-300 dark:border-gray-700 text-orange-500 focus:ring-orange-500 dark:bg-gray-900"
					/>
					<span class="text-xs font-medium {runDryRun ? 'text-orange-600 dark:text-orange-400' : 'text-gray-500 dark:text-gray-400'}">
						{$i18n.t('Test Mode')}
					</span>
				</label>
				{#if runDryRun}
					<span class="text-[10px] text-orange-500 dark:text-orange-400">
						Synthetic data — no model inference
					</span>
				{/if}
			</div>

			<div class="flex justify-end gap-2 pt-1">
				<button class="px-3 py-1.5 rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-gray-850 transition" on:click={() => { showRunForm = false; }}>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-4 py-1.5 rounded-xl text-sm font-medium {runDryRun ? 'bg-orange-500 hover:bg-orange-600' : 'bg-blue-600 hover:bg-blue-700'} text-white transition disabled:opacity-50"
					on:click={handleStartRun} disabled={submitting || (!runDryRun && !runModelId.trim())}
				>
					{submitting ? $i18n.t('Starting...') : runDryRun ? $i18n.t('Start Test') : $i18n.t('Start')}
				</button>
			</div>
		</div>
	</div>
{/if}

{#if !loaded}
	<div class="flex justify-center py-8"><Spinner /></div>
{:else if jobs.length === 0}
	<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-6">
		{$i18n.t('No evaluation jobs yet. Click "Run Evaluation" to start one.')}
	</div>
{:else}
	<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
		<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
			<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
				<tr>
					<th scope="col" class="px-3 py-1.5">Status</th>
					<th scope="col" class="px-3 py-1.5">Type</th>
					<th scope="col" class="px-3 py-1.5">Benchmark</th>
					<th scope="col" class="px-3 py-1.5">Model</th>
					<th scope="col" class="px-3 py-1.5">User</th>
					<th scope="col" class="px-3 py-1.5">Submitted</th>
					<th scope="col" class="px-3 py-1.5 text-right">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each jobs as job (job.id)}
					<tr
						class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50 {['running', 'completed', 'failed', 'cancelled'].includes(job.status) ? 'cursor-pointer' : ''}"
						on:click={() => { if (['running', 'completed', 'failed', 'cancelled'].includes(job.status)) activeJob = job; }}
					>
						<td class="px-3 py-2">
							<span class="px-2 py-0.5 rounded-lg text-[11px] font-medium {statusColor(job.status)}">
								{job.status}
							</span>
							{#if ['running', 'completed', 'failed', 'cancelled'].includes(job.status)}
								<span class="ml-1 text-[10px] text-blue-500 dark:text-blue-400">{$i18n.t('click to view')}</span>
							{/if}
						</td>
						<td class="px-3 py-2">
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium {job.eval_type === 'lm-eval' ? 'bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-300' : 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'}">
								{job.eval_type === 'lm-eval' ? 'LLM' : 'Code'}
							</span>
						</td>
						<td class="px-3 py-2 font-medium text-gray-900 dark:text-white">
							{getBenchmarkName(job.benchmark)}
						</td>
						<td class="px-3 py-2 font-mono">{job.model_id}</td>
						<td class="px-3 py-2">{job.user?.name ?? job.user_id}</td>
						<td class="px-3 py-2 text-gray-500">
							{dayjs(job.created_at * 1000).fromNow()}
						</td>
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<td class="px-3 py-2 text-right" on:click|stopPropagation>
							<div class="flex items-center justify-end gap-1">
								{#if job.status === 'pending'}
									<Tooltip content={$i18n.t('Approve')}>
										<button class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => handleApprove(job.id)}>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-green-500 hover:text-green-600">
												<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
											</svg>
										</button>
									</Tooltip>
									<Tooltip content={$i18n.t('Reject')}>
										<button class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => handleReject(job.id)}>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-red-400 hover:text-red-500">
												<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
											</svg>
										</button>
									</Tooltip>
								{/if}
								{#if ['queued', 'running'].includes(job.status)}
									<Tooltip content={$i18n.t('Cancel')}>
										<button class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => handleCancel(job.id)}>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-500 hover:text-red-500">
												<path fill-rule="evenodd" d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" clip-rule="evenodd" />
											</svg>
										</button>
									</Tooltip>
								{/if}
								{#if ['completed', 'failed', 'cancelled'].includes(job.status)}
									<Tooltip content={$i18n.t('Delete')}>
										<button class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => handleDelete(job.id)}>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-500 hover:text-red-500 transition">
												<path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022 1.005 11.36A2.75 2.75 0 007.77 20h4.46a2.75 2.75 0 002.751-2.689l1.005-11.36.149.022a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 01.7.797l-.5 5.5a.75.75 0 01-1.494-.136l.5-5.5a.75.75 0 01.794-.66zm2.84 0a.75.75 0 01.794.66l.5 5.5a.75.75 0 01-1.494.137l-.5-5.5a.75.75 0 01.7-.798z" clip-rule="evenodd" />
											</svg>
										</button>
									</Tooltip>
								{/if}
								{#if job.error_message}
									<Tooltip content={job.error_message}>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-red-500">
											<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
										</svg>
									</Tooltip>
								{/if}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
{/if}
