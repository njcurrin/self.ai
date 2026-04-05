<script lang="ts">
	import { onMount, onDestroy, getContext, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		streamEvalJobLive,
		getEvalJobEvents,
		type LiveEvalEvent,
		type EvalJob
	} from '$lib/apis/evaluations/jobs';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let job: EvalJob;

	let events: LiveEvalEvent[] = [];
	let benchmarks: Record<string, number> = {};
	let status: 'loading' | 'streaming' | 'done' | 'error' = 'loading';
	let errorMessage = '';
	let stopStream: (() => void) | null = null;
	let listEl: HTMLDivElement;
	let autoScroll = true;
	let expandedIndex: number | null = null;

	$: isRunning = job.status === 'running';
	$: isLmEval = job.eval_type === 'lm-eval';
	$: totalTasks = events.length > 0 ? (events[events.length - 1].total ?? events.length) : 0;
	$: hasBenchmarks = Object.keys(benchmarks).length > 0;

	// Title changes based on job state
	$: title = isRunning ? $i18n.t('Live Evaluation') : $i18n.t('Evaluation Details');

	// Helpers to normalize event fields across both formats
	const getEventLabel = (event: LiveEvalEvent) =>
		event.task_name ?? event.task_id ?? `#${event.index + 1}`;

	const getEventPreview = (event: LiveEvalEvent) => {
		const parts: string[] = [];
		if (event.thinking) parts.push(`[thinking: ${event.thinking.length} chars]`);
		const resp = event.scored_response ?? event.response;
		if (resp) parts.push(resp.slice(0, 120));
		else if (event.completions?.length) parts.push(event.completions[0]?.slice(0, 120) ?? '');
		return parts.join(' ') || '';
	};

	const scoreColor = (score: number): string => {
		if (score >= 70) return 'text-green-500';
		if (score >= 40) return 'text-yellow-500';
		return 'text-red-500';
	};

	const formatBenchmarkName = (name: string): string =>
		name.replace('leaderboard_', '').replace(/_/g, ' ');

	const formatMetricValue = (v: unknown): string => {
		if (typeof v === 'number') return v % 1 === 0 ? String(v) : v.toFixed(4);
		return String(v ?? '');
	};

	function toggleExpand(index: number) {
		expandedIndex = expandedIndex === index ? null : index;
	}

	async function loadEvents() {
		status = 'loading';
		try {
			const data = await getEvalJobEvents(localStorage.token, job.id);
			events = data.events ?? [];
			benchmarks = data.benchmarks ?? {};
			status = 'done';
		} catch (e) {
			status = 'error';
			errorMessage = e instanceof Error ? e.message : String(e);
		}
	}

	onMount(() => {
		if (isRunning) {
			// Stream live events
			status = 'streaming';
			stopStream = streamEvalJobLive(
				localStorage.token,
				job.id,
				(event) => {
					events = [...events, event];
					if (autoScroll) {
						requestAnimationFrame(() => {
							listEl?.scrollTo({ top: listEl.scrollHeight, behavior: 'smooth' });
						});
					}
				},
				(doneStatus) => {
					status = 'done';
					toast.success($i18n.t('Evaluation finished: ') + doneStatus);
				},
				(error) => {
					status = 'error';
					errorMessage = error;
				}
			);
		} else {
			// Load all events at once for completed/failed/cancelled jobs
			loadEvents();
		}
	});

	onDestroy(() => {
		if (stopStream) stopStream();
	});
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center gap-3 mb-3">
		<button
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
			on:click={() => dispatch('back')}
			title={$i18n.t('Back to Schedule')}
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
				<path fill-rule="evenodd" d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z" clip-rule="evenodd" />
			</svg>
		</button>
		<div class="flex-1">
			<div class="text-lg font-medium flex items-center gap-2">
				{title}
				{#if status === 'streaming'}
					<span class="relative flex h-2.5 w-2.5">
						<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
						<span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
					</span>
				{/if}
			</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{job.model_id} &middot; {job.benchmark}
				{#if events.length > 0}
					&middot; {events.length}/{totalTasks} {$i18n.t('tasks')}
				{/if}
			</div>
		</div>
		{#if isRunning}
			<label class="flex items-center gap-1.5 text-xs text-gray-500">
				<input type="checkbox" bind:checked={autoScroll} class="rounded" />
				{$i18n.t('Auto-scroll')}
			</label>
		{/if}
	</div>

	<!-- Progress bar -->
	{#if events.length > 0 && totalTasks > 0}
		{@const pct = Math.round((events.length / totalTasks) * 100)}
		<div class="mb-3">
			<div class="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-1.5">
				<div
					class="h-1.5 rounded-full transition-all duration-300 {status === 'done' ? 'bg-green-500' : status === 'error' ? 'bg-red-500' : 'bg-blue-500'}"
					style="width: {pct}%"
				></div>
			</div>
		</div>
	{/if}

	<!-- Benchmark scores (shown for completed jobs with results) -->
	{#if hasBenchmarks}
		<div class="mb-3 flex flex-wrap gap-3 text-xs">
			{#each Object.entries(benchmarks) as [bench, score]}
				<div class="px-2 py-1 rounded bg-gray-50 dark:bg-gray-850">
					<span class="text-gray-500 capitalize">{formatBenchmarkName(bench)}:</span>
					<span class="font-semibold ml-1 {scoreColor(score)}">{score.toFixed(1)}%</span>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Status messages -->
	{#if status === 'error'}
		<div class="mb-3 px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
			{errorMessage}
		</div>
	{/if}

	<!-- Events list -->
	<div
		bind:this={listEl}
		class="flex-1 overflow-y-auto space-y-2 min-h-0"
		on:scroll={() => {
			if (listEl) {
				const atBottom = listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight < 50;
				autoScroll = atBottom;
			}
		}}
	>
		{#if events.length === 0 && (status === 'streaming' || status === 'loading')}
			<div class="flex flex-col items-center justify-center py-12 text-gray-400">
				<Spinner />
				<div class="mt-3 text-sm">
					{status === 'streaming' ? $i18n.t('Waiting for first task...') : $i18n.t('Loading events...')}
				</div>
			</div>
		{:else if events.length === 0 && status === 'done'}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-6">
				{$i18n.t('No event data recorded for this job.')}
			</div>
		{/if}

		{#each events as event, i (event.index)}
			<button
				class="w-full text-left rounded-xl border transition
					{expandedIndex === i
						? 'border-blue-300 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/10'
						: 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'}
					p-3"
				on:click={() => toggleExpand(i)}
			>
				<!-- Task header -->
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<span class="text-xs font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
							{event.index + 1}/{totalTasks}
						</span>
						<span class="text-sm font-medium text-gray-900 dark:text-white">
							{getEventLabel(event)}
						</span>
						{#if event.metrics}
							{#each Object.entries(event.metrics) as [key, val]}
								<span class="px-1.5 py-0.5 rounded text-[10px] font-medium {Number(val) >= 0.5 ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-orange-50 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400'}">
									{key}: {formatMetricValue(val)}
								</span>
							{/each}
						{/if}
					</div>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-4 text-gray-400 transition-transform {expandedIndex === i ? 'rotate-180' : ''}"
					>
						<path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clip-rule="evenodd" />
					</svg>
				</div>

				<!-- Preview (collapsed) -->
				{#if expandedIndex !== i}
					<div class="mt-1.5 text-xs text-gray-500 dark:text-gray-400 truncate font-mono">
						{getEventPreview(event)}
					</div>
				{/if}

				<!-- Expanded content -->
				{#if expandedIndex === i}
					<div class="mt-3 space-y-3">
						{#if event.prompt}
							<div>
								<div class="text-[11px] uppercase font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Prompt')}
								</div>
								<pre class="text-xs bg-gray-50 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-64 overflow-y-auto font-mono text-gray-800 dark:text-gray-200">{event.prompt}</pre>
							</div>
						{/if}
						{#if event.thinking}
							<div>
								<div class="text-[11px] uppercase font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Thinking')}
								</div>
								<pre class="text-xs bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/30 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-48 overflow-y-auto font-mono text-amber-800 dark:text-amber-200">{event.thinking}</pre>
							</div>
						{/if}
						{#if event.target}
							<div>
								<div class="text-[11px] uppercase font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Expected')}
								</div>
								<pre class="text-xs bg-gray-50 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-40 overflow-y-auto font-mono text-gray-800 dark:text-gray-200">{event.target}</pre>
							</div>
						{/if}
						{#if event.scored_response || event.response}
							<div>
								<div class="text-[11px] uppercase font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Response')}
								</div>
								<pre class="text-xs bg-gray-50 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-64 overflow-y-auto font-mono text-gray-800 dark:text-gray-200">{event.scored_response ?? event.response}</pre>
							</div>
						{/if}
						{#if event.completions}
							{#each event.completions as completion, ci}
								<div>
									<div class="text-[11px] uppercase font-medium text-gray-500 dark:text-gray-400 mb-1">
										{$i18n.t('Response')}{event.completions.length > 1 ? ` #${ci + 1}` : ''}
									</div>
									<pre class="text-xs bg-gray-50 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-64 overflow-y-auto font-mono text-gray-800 dark:text-gray-200">{completion}</pre>
								</div>
							{/each}
						{/if}
						{#if event.metrics && Object.keys(event.metrics).length > 0}
							<div>
								<div class="text-[11px] uppercase font-medium text-gray-500 dark:text-gray-400 mb-1">
									{$i18n.t('Metrics')}
								</div>
								<div class="flex flex-wrap gap-2">
									{#each Object.entries(event.metrics) as [key, val]}
										<span class="px-2 py-1 rounded-lg text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300">
											{key}: {formatMetricValue(val)}
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Done footer -->
	{#if status === 'done' && events.length > 0}
		<div class="mt-3 text-center text-sm text-green-600 dark:text-green-400 font-medium py-2">
			{$i18n.t('Evaluation complete')} &mdash; {events.length} {$i18n.t('tasks')}
		</div>
	{/if}
</div>
