<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import dayjs from 'dayjs';
	import { toast } from 'svelte-sonner';
	const i18n = getContext('i18n');

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import {
		getJobs,
		approveJob,
		rejectJob,
		cancelJob,
		deleteJob,
		syncJobStatus,
		type TrainingJob
	} from '$lib/apis/training';
	import {
		getLlamolotlTrainingJobLogs,
		getLlamolotlTrainingOutputs,
		type TrainingOutput
	} from '$lib/apis/llamolotl';

	const POLL_MS = 8000;
	const LOG_TAIL = 200;

	const getToken = () => localStorage.getItem('token') ?? '';

	let loading = true;
	let refreshing = false;
	let pageError = '';

	let jobs: TrainingJob[] = [];
	let selectedJobId = '';
	let selectedJobLogs: string[] = [];
	let outputs: TrainingOutput[] = [];

	let actionInProgress: Record<string, boolean> = {};
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	// ── Derived ──────────────────────────────────────────────────────────
	$: selectedJob = jobs.find((j) => j.id === selectedJobId) ?? null;
	$: pendingCount = jobs.filter((j) => j.status === 'pending').length;
	$: runningCount = jobs.filter((j) => j.status === 'running').length;
	$: queuedCount = jobs.filter((j) => j.status === 'queued').length;

	// ── Helpers ──────────────────────────────────────────────────────────
	const formatDateTime = (ts: number | null | undefined) => {
		if (!ts) return '—';
		return dayjs(ts * 1000).format('YYYY-MM-DD HH:mm');
	};

	const statusClasses = (status: TrainingJob['status']) => {
		const map: Record<string, string> = {
			pending:   'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
			scheduled: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
			queued:    'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300',
			running:   'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
			completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
			failed:    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
			cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
		};
		return map[status] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
	};

	const statusLabel = (status: TrainingJob['status']) => {
		const map: Record<string, string> = {
			pending: 'Pending Approval',
			scheduled: 'Scheduled',
			queued: 'Queued',
			running: 'Running',
			completed: 'Completed',
			failed: 'Failed',
			cancelled: 'Cancelled'
		};
		return map[status] ?? status;
	};

	const formatBytes = (bytes: number) => {
		if (!bytes) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		let v = bytes, i = 0;
		while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
		return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
	};

	// ── Data loading ─────────────────────────────────────────────────────
	const loadLogs = async (job: TrainingJob) => {
		if (!job.llamolotl_job_id || job.llamolotl_url_idx === null) {
			selectedJobLogs = [];
			return;
		}
		try {
			selectedJobLogs = await getLlamolotlTrainingJobLogs(
				getToken(),
				job.llamolotl_job_id,
				LOG_TAIL,
				job.llamolotl_url_idx
			);
		} catch {
			selectedJobLogs = [];
		}
	};

	const loadOutputs = async () => {
		try {
			outputs = await getLlamolotlTrainingOutputs(getToken(), 0);
		} catch {
			outputs = [];
		}
	};

	const refresh = async (quiet = false) => {
		if (!quiet) refreshing = true;
		try {
			jobs = await getJobs(getToken());

			// Auto-select first job if nothing selected or selection vanished
			if (!selectedJobId || !jobs.some((j) => j.id === selectedJobId)) {
				selectedJobId = jobs[0]?.id ?? '';
			}

			const job = jobs.find((j) => j.id === selectedJobId);
			if (job) await loadLogs(job);

			await loadOutputs();
			pageError = '';
		} catch (e: any) {
			if (!quiet) pageError = e?.detail ?? e?.message ?? 'Failed to load training jobs';
		} finally {
			refreshing = false;
		}
	};

	const selectJob = async (id: string) => {
		selectedJobId = id;
		const job = jobs.find((j) => j.id === id);
		if (job) await loadLogs(job);
	};

	// ── Actions ──────────────────────────────────────────────────────────
	const withAction = async (id: string, fn: () => Promise<void>) => {
		actionInProgress = { ...actionInProgress, [id]: true };
		try {
			await fn();
			await refresh(true);
		} catch (e: any) {
			toast.error(typeof e === 'string' ? e : e?.detail ?? 'Action failed');
		} finally {
			const next = { ...actionInProgress };
			delete next[id];
			actionInProgress = next;
		}
	};

	const handleApprove = (id: string) =>
		withAction(id, async () => {
			await approveJob(getToken(), id);
			toast.success($i18n.t('Job approved and dispatched to Llamolotl.'));
		});

	const handleReject = (id: string) =>
		withAction(id, async () => {
			await rejectJob(getToken(), id);
			toast.success($i18n.t('Job rejected.'));
		});

	const handleCancel = (id: string) =>
		withAction(id, async () => {
			await cancelJob(getToken(), id);
			toast.success($i18n.t('Job cancelled.'));
		});

	const handleSync = (id: string) =>
		withAction(id, async () => {
			await syncJobStatus(getToken(), id);
			toast.success($i18n.t('Status synced from Llamolotl.'));
		});

	const handleDelete = (id: string) =>
		withAction(id, async () => {
			await deleteJob(getToken(), id);
			if (selectedJobId === id) selectedJobId = '';
			toast.success($i18n.t('Job deleted.'));
		});

	// ── Lifecycle ────────────────────────────────────────────────────────
	onMount(async () => {
		loading = true;
		await refresh();
		loading = false;
		pollTimer = setInterval(() => refresh(true), POLL_MS);
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
	});
</script>

{#if loading}
	<div class="flex justify-center items-center h-full py-16">
		<Spinner />
	</div>
{:else}
	<div class="flex flex-col gap-1 my-1.5">

		<!-- Header -->
		<div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center gap-2">
				{$i18n.t('Training Jobs')}
				<div class="flex self-center w-[1px] h-6 mx-0.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{jobs.length}</span>

				{#if pendingCount > 0}
					<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
						{pendingCount} pending
					</span>
				{/if}
				{#if queuedCount > 0}
					<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
						{queuedCount} queued
					</span>
				{/if}
				{#if runningCount > 0}
					<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
						{runningCount} running
					</span>
				{/if}
			</div>

			<button
				class="px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 transition text-sm flex items-center"
				on:click={() => refresh()}
				disabled={refreshing}
				aria-label={$i18n.t('Refresh')}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 {refreshing ? 'animate-spin' : ''}">
					<path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.598a.75.75 0 00-.75.75v3.634a.75.75 0 001.5 0v-2.134l.228.228a7 7 0 0011.709-3.133.75.75 0 00-1.473-.278zM4.688 8.576a5.5 5.5 0 019.201-2.466l.312.311H11.77a.75.75 0 000 1.5h3.634a.75.75 0 00.75-.75V3.537a.75.75 0 00-1.5 0v2.134l-.228-.228A7 7 0 002.717 8.576a.75.75 0 001.473.278z" clip-rule="evenodd" />
				</svg>
			</button>
		</div>

		{#if pageError}
			<div class="rounded-xl border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300 mt-2">
				{pageError}
			</div>
		{/if}

		<!-- Job list -->
		<div class="mt-2 mb-3">
			{#if jobs.length === 0}
				<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-10 text-sm text-center text-gray-500 dark:text-gray-400">
					{$i18n.t('No training jobs yet. Users can submit jobs from the Training workspace.')}
				</div>
			{:else}
				<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-2">
					{#each jobs as job}
						<button
							class="flex flex-col text-left w-full px-3 py-2.5 rounded-xl transition {selectedJobId === job.id
								? 'bg-gray-100 dark:bg-gray-850'
								: 'hover:bg-gray-50 dark:hover:bg-gray-850'}"
							on:click={() => selectJob(job.id)}
						>
							<div class="flex items-center justify-between gap-2 w-full">
								<div class="font-medium text-sm truncate">
									{job.course?.name ?? $i18n.t('Unknown Course')}
								</div>
								<span class="px-2 py-0.5 rounded-full text-[11px] font-medium shrink-0 {statusClasses(job.status)}">
									{$i18n.t(statusLabel(job.status))}
								</span>
							</div>
							<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 truncate">
								{$i18n.t('Model')}: {job.model_id}
							</div>
							<div class="mt-0.5 text-xs text-gray-400 dark:text-gray-500 truncate">
								{$i18n.t('By')} {job.user?.name ?? job.user_id} · {formatDateTime(job.created_at)}
							</div>
						</button>
					{/each}
				</div>

				<!-- Selected job detail panel -->
				{#if selectedJob}
					<div class="mt-4 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<div class="flex items-center gap-2 flex-wrap">
									<div class="text-base font-semibold">
										{selectedJob.course?.name ?? $i18n.t('Unknown Course')}
									</div>
									<span class="px-2 py-0.5 rounded-full text-xs font-medium capitalize {statusClasses(selectedJob.status)}">
										{$i18n.t(statusLabel(selectedJob.status))}
									</span>
								</div>
								<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">
									{$i18n.t('Model')}: <span class="font-medium text-gray-700 dark:text-gray-200">{selectedJob.model_id}</span>
								</div>
								{#if selectedJob.course?.description}
									<div class="mt-0.5 text-xs text-gray-400 dark:text-gray-500">
										{selectedJob.course.description}
									</div>
								{/if}
							</div>

							<!-- Action buttons -->
							<div class="flex flex-wrap gap-2">
								{#if selectedJob.status === 'pending'}
									<button
										class="px-3 py-1.5 rounded-xl text-sm bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-950/40 dark:hover:bg-green-950/60 dark:text-green-300 transition disabled:opacity-50"
										on:click={() => handleApprove(selectedJob.id)}
										disabled={!!actionInProgress[selectedJob.id]}
									>
										{actionInProgress[selectedJob.id] ? $i18n.t('Approving...') : $i18n.t('Approve')}
									</button>
									<button
										class="px-3 py-1.5 rounded-xl text-sm bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-950/40 dark:hover:bg-red-950/60 dark:text-red-300 transition disabled:opacity-50"
										on:click={() => handleReject(selectedJob.id)}
										disabled={!!actionInProgress[selectedJob.id]}
									>
										{actionInProgress[selectedJob.id] ? $i18n.t('Rejecting...') : $i18n.t('Reject')}
									</button>
								{:else if selectedJob.status === 'queued' || selectedJob.status === 'running'}
									{#if selectedJob.llamolotl_job_id}
										<button
											class="px-3 py-1.5 rounded-xl text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-300 transition disabled:opacity-50"
											on:click={() => handleSync(selectedJob.id)}
											disabled={!!actionInProgress[selectedJob.id]}
										>
											{actionInProgress[selectedJob.id] ? $i18n.t('Syncing...') : $i18n.t('Sync Status')}
										</button>
									{/if}
									<button
										class="px-3 py-1.5 rounded-xl text-sm bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-950/40 dark:hover:bg-red-950/60 dark:text-red-300 transition disabled:opacity-50"
										on:click={() => handleCancel(selectedJob.id)}
										disabled={!!actionInProgress[selectedJob.id]}
									>
										{actionInProgress[selectedJob.id] ? $i18n.t('Cancelling...') : $i18n.t('Cancel')}
									</button>
								{:else}
									<button
										class="px-3 py-1.5 rounded-xl text-sm bg-gray-100 hover:bg-red-100 text-gray-600 hover:text-red-700 dark:bg-gray-800 dark:hover:bg-red-950/40 dark:text-gray-400 dark:hover:text-red-300 transition disabled:opacity-50"
										on:click={() => handleDelete(selectedJob.id)}
										disabled={!!actionInProgress[selectedJob.id]}
									>
										{actionInProgress[selectedJob.id] ? $i18n.t('Deleting...') : $i18n.t('Delete')}
									</button>
								{/if}
							</div>
						</div>

						<!-- Metadata grid -->
						<div class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
							<div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Submitted by')}</div>
								<div>{selectedJob.user?.name ?? selectedJob.user_id}</div>
							</div>
							<div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Created')}</div>
								<div>{formatDateTime(selectedJob.created_at)}</div>
							</div>
							<div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Updated')}</div>
								<div>{formatDateTime(selectedJob.updated_at)}</div>
							</div>
							{#if selectedJob.llamolotl_job_id}
								<div>
									<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Llamolotl Job')}</div>
									<div class="font-mono text-xs">{selectedJob.llamolotl_job_id}</div>
								</div>
							{/if}
						</div>

						<!-- Course data tags -->
						{#if selectedJob.course?.data}
							{@const d = selectedJob.course.data}
							<div class="mt-3 flex flex-wrap gap-1.5">
								{#if d.base_config}
									<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
										{d.base_config.split('/').pop()}
									</span>
								{/if}
								{#each (d.knowledge_ids ?? []) as kid}
									<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300">KB: {kid}</span>
								{/each}
								{#each (d.dataset_ids ?? []) as did}
									<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">DS: {did}</span>
								{/each}
								{#if d.advanced_config}
									<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
										{$i18n.t('Custom params')}
									</span>
								{/if}
							</div>
						{/if}

						<!-- Error message -->
						{#if selectedJob.error_message}
							<div class="mt-3 rounded-xl border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-950/30 px-3 py-2 text-sm text-red-700 dark:text-red-300">
								{selectedJob.error_message}
							</div>
						{/if}

						<!-- Logs (only when dispatched) -->
						{#if selectedJob.llamolotl_job_id}
							<div class="mt-4">
								<div class="text-xs text-gray-500 dark:text-gray-400 mb-1.5">{$i18n.t('Logs')}</div>
								<pre class="rounded-xl bg-gray-950 text-gray-100 text-xs p-3 overflow-auto max-h-[280px] whitespace-pre-wrap break-words">{selectedJobLogs.length > 0
									? selectedJobLogs.join('\n')
									: $i18n.t('No logs available yet.')}</pre>
							</div>
						{/if}
					</div>
				{/if}
			{/if}
		</div>

		<!-- Outputs section -->
		{#if outputs.length > 0}
			<div class="mb-5">
				<div class="flex items-center mb-2 px-0.5">
					<div class="text-sm font-medium">{$i18n.t('Training Outputs')}</div>
					<div class="flex self-center w-[1px] h-4 mx-2 bg-gray-50 dark:bg-gray-850" />
					<span class="text-sm text-gray-500 dark:text-gray-300">{outputs.length}</span>
				</div>
				<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-2">
					{#each outputs as output}
						<div class="flex flex-col px-3 py-2.5 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition">
							<div class="flex items-start justify-between gap-2">
								<div class="font-medium text-sm truncate">{output.name}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400 shrink-0">{formatBytes(output.size_bytes)}</div>
							</div>
							<div class="mt-1 text-xs text-gray-500 dark:text-gray-400 truncate">{output.path}</div>
							<div class="mt-2 flex gap-1.5">
								{#if output.has_model}
									<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">model</span>
								{/if}
								{#if output.has_config}
									<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">config</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

	</div>
{/if}
