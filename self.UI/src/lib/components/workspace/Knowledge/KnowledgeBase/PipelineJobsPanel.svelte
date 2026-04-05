<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { listCuratorJobs, getCuratorJobLogs } from '$lib/apis/curator';

	export let pipelineName: string;
	export let token: string;

	const POLL_MS = 5000;
	const MAX_JOBS = 10;

	let expanded = false;
	let jobs: any[] = [];
	let expandedJobId: string | null = null;
	let logsByJobId: Record<string, string[]> = {};
	let loadingLogs: Record<string, boolean> = {};
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	const statusClasses = (status: string) => {
		const map: Record<string, string> = {
			pending:   'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
			scheduled: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
			running:   'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
			completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
			failed:    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
			cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
		};
		return map[status] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
	};

	const hasActiveJobs = () =>
		jobs.some(j => ['pending', 'scheduled', 'running'].includes(j.status));

	const refresh = async () => {
		if (!pipelineName || pipelineName === 'Untitled') return;
		try {
			const all: any[] = await listCuratorJobs(token);
			jobs = all
				.filter(j => j.name.startsWith(pipelineName))
				.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
				.slice(0, MAX_JOBS);
		} catch (_) {
			// curator not available — silently ignore
		}
	};

	const toggleExpand = async (jobId: string) => {
		if (expandedJobId === jobId) {
			expandedJobId = null;
			return;
		}
		expandedJobId = jobId;
		if (!logsByJobId[jobId]) {
			loadingLogs = { ...loadingLogs, [jobId]: true };
			try {
				const res = await getCuratorJobLogs(token, jobId, 50);
				logsByJobId = { ...logsByJobId, [jobId]: res.lines };
			} catch (_) {
				logsByJobId = { ...logsByJobId, [jobId]: ['(logs unavailable)'] };
			} finally {
				loadingLogs = { ...loadingLogs, [jobId]: false };
			}
		}
	};

	const startPolling = () => {
		if (pollTimer) return;
		pollTimer = setInterval(async () => {
			await refresh();
			if (!hasActiveJobs()) {
				clearInterval(pollTimer!);
				pollTimer = null;
			}
		}, POLL_MS);
	};

	onMount(async () => {
		await refresh();
		if (hasActiveJobs()) startPolling();
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
	});

	// Re-refresh + restart poll when pipelineName changes
	$: if (pipelineName && pipelineName !== 'Untitled') {
		refresh().then(() => { if (hasActiveJobs()) startPolling(); });
	}
</script>

<div class="mt-2 border-t border-gray-100 dark:border-gray-800">
	<!-- Collapsible header -->
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="flex items-center gap-1.5 px-1 py-1.5 cursor-pointer select-none text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
		on:click={() => { expanded = !expanded; if (expanded) refresh(); }}
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 16 16"
			fill="currentColor"
			class="size-3 transition-transform {expanded ? 'rotate-90' : ''}"
		>
			<path fill-rule="evenodd" d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L9.19 8 6.22 5.03a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
		</svg>
		<span class="font-medium">Job History</span>
		{#if jobs.length > 0}
			<span class="ml-1 px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-[10px]">
				{jobs.length}
			</span>
		{/if}
		{#if hasActiveJobs()}
			<span class="ml-1 px-1.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-[10px] font-medium">
				active
			</span>
		{/if}
	</div>

	{#if expanded}
		<div class="pb-2">
			{#if pipelineName === 'Untitled'}
				<p class="px-2 py-2 text-xs text-gray-400 dark:text-gray-500">Save the pipeline first to see job history.</p>
			{:else if jobs.length === 0}
				<p class="px-2 py-2 text-xs text-gray-400 dark:text-gray-500">No jobs yet for this pipeline.</p>
			{:else}
				{#each jobs as job (job.job_id)}
					<div class="rounded-lg border border-gray-100 dark:border-gray-800 mb-1.5 overflow-hidden">
						<!-- Job row -->
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<!-- svelte-ignore a11y-no-static-element-interactions -->
						<div
							class="flex items-center gap-2 px-2 py-1.5 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-850 transition text-xs"
							on:click={() => toggleExpand(job.job_id)}
						>
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium {statusClasses(job.status)}">
								{job.status}
							</span>
							<span class="flex-1 font-mono truncate text-gray-700 dark:text-gray-300">{job.name}</span>
							<span class="text-gray-400 flex-shrink-0">{dayjs(job.created_at).fromNow()}</span>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-3 text-gray-400 flex-shrink-0 transition-transform {expandedJobId === job.job_id ? 'rotate-90' : ''}"
							>
								<path fill-rule="evenodd" d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L9.19 8 6.22 5.03a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
							</svg>
						</div>

						<!-- Log tail -->
						{#if expandedJobId === job.job_id}
							<div class="border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 px-2 py-1.5">
								{#if loadingLogs[job.job_id]}
									<p class="text-[10px] text-gray-400">Loading logs…</p>
								{:else if logsByJobId[job.job_id]?.length}
									<pre class="text-[10px] text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-all max-h-40 overflow-y-auto font-mono leading-relaxed">{logsByJobId[job.job_id].join('\n')}</pre>
								{:else}
									<p class="text-[10px] text-gray-400">No logs yet.</p>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>
