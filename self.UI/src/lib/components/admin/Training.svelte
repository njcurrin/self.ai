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

	let selectedTab = 'jobs';

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
		selectedJobId = selectedJobId === id ? '' : id;
		if (selectedJobId) {
			const job = jobs.find((j) => j.id === selectedJobId);
			if (job) await loadLogs(job);
		}
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
	<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">

		<!-- Sidebar tab nav -->
		<div
			id="training-tabs-container"
			class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
		>
			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab === 'jobs' ? '' : 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => (selectedTab = 'jobs')}
			>
				<div class="self-center mr-2">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
						<path fill-rule="evenodd" d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm1 8.25a.75.75 0 0 1 .75-.75h4.5a.75.75 0 0 1 0 1.5h-4.5a.75.75 0 0 1-.75-.75Zm.75-3.25a.75.75 0 0 0 0 1.5H8a.75.75 0 0 0 0-1.5H5.75Z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="self-center">{$i18n.t('Jobs')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab === 'outputs' ? '' : 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => (selectedTab = 'outputs')}
			>
				<div class="self-center mr-2">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
						<path d="M2 3.5A1.5 1.5 0 0 1 3.5 2h2.879a1.5 1.5 0 0 1 1.06.44l1.122 1.12A1.5 1.5 0 0 0 9.62 4H12.5A1.5 1.5 0 0 1 14 5.5v1.401a2.986 2.986 0 0 0-1.5-.401h-9c-.546 0-1.059.146-1.5.401V3.5Z" />
						<path d="M1 9.5A2.5 2.5 0 0 1 3.5 7h9A2.5 2.5 0 0 1 15 9.5v2a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 1 11.5v-2Z" />
					</svg>
				</div>
				<div class="self-center">{$i18n.t('Outputs')}</div>
			</button>
		</div>

		<!-- Main content -->
		<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">

			{#if selectedTab === 'jobs'}
				<!-- Header -->
				<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
					<div class="flex md:self-center text-lg font-medium px-0.5 shrink-0 items-center">
						{$i18n.t('Training Jobs')}
						<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
						<span class="text-sm font-normal text-gray-500">{jobs.length} {$i18n.t('jobs')}</span>

						{#if pendingCount > 0}
							<span class="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
								{pendingCount} pending
							</span>
						{/if}
						{#if queuedCount > 0}
							<span class="ml-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
								{queuedCount} queued
							</span>
						{/if}
						{#if runningCount > 0}
							<span class="ml-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
								{runningCount} running
							</span>
						{/if}
					</div>

					<button
						class="px-2 py-1.5 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 transition text-sm flex items-center self-start"
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
					<div class="rounded-xl border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300 mb-3">
						{pageError}
					</div>
				{/if}

				{#if jobs.length === 0}
					<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-10 text-sm text-center text-gray-500 dark:text-gray-400">
						{$i18n.t('No training jobs yet. Users can submit jobs from the Training workspace.')}
					</div>
				{:else}
					<!-- Jobs table -->
					<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
						<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
							<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
								<tr>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Status')}</th>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Course')}</th>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Model')}</th>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('User')}</th>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Submitted')}</th>
									<th scope="col" class="px-3 py-1.5 text-right">{$i18n.t('Actions')}</th>
								</tr>
							</thead>
							<tbody>
								{#each jobs as job (job.id)}
									<tr
										class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50 cursor-pointer {selectedJobId === job.id ? 'bg-gray-50 dark:bg-gray-850/50' : ''}"
										on:click={() => selectJob(job.id)}
									>
										<td class="px-3 py-2">
											<span class="px-2 py-0.5 rounded-lg text-[11px] font-medium {statusClasses(job.status)}">
												{$i18n.t(statusLabel(job.status))}
											</span>
										</td>
										<td class="px-3 py-2 font-medium text-gray-900 dark:text-white">
											{job.course?.name ?? $i18n.t('Unknown Course')}
										</td>
										<td class="px-3 py-2 font-mono">{job.model_id}</td>
										<td class="px-3 py-2">{job.user?.name ?? job.user_id}</td>
										<td class="px-3 py-2 text-gray-500">{formatDateTime(job.created_at)}</td>
										<!-- svelte-ignore a11y-click-events-have-key-events -->
										<td class="px-3 py-2 text-right" on:click|stopPropagation>
											<div class="flex items-center justify-end gap-1">
												{#if actionInProgress[job.id]}
													<Spinner className="size-3.5" />
												{:else if job.status === 'pending'}
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
												{:else if job.status === 'queued' || job.status === 'running'}
													{#if job.llamolotl_job_id}
														<Tooltip content={$i18n.t('Sync Status')}>
															<button class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => handleSync(job.id)}>
																<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
																	<path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.598a.75.75 0 00-.75.75v3.634a.75.75 0 001.5 0v-2.134l.228.228a7 7 0 0011.709-3.133.75.75 0 00-1.473-.278zM4.688 8.576a5.5 5.5 0 019.201-2.466l.312.311H11.77a.75.75 0 000 1.5h3.634a.75.75 0 00.75-.75V3.537a.75.75 0 00-1.5 0v2.134l-.228-.228A7 7 0 002.717 8.576a.75.75 0 001.473.278z" clip-rule="evenodd" />
																</svg>
															</button>
														</Tooltip>
													{/if}
													<Tooltip content={$i18n.t('Cancel')}>
														<button class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => handleCancel(job.id)}>
															<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-500 hover:text-red-500">
																<path fill-rule="evenodd" d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" clip-rule="evenodd" />
															</svg>
														</button>
													</Tooltip>
												{:else}
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

							<!-- Logs -->
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

			{:else if selectedTab === 'outputs'}
				<!-- Outputs header -->
				<div class="mt-0.5 mb-2 flex md:self-center text-lg font-medium px-0.5 items-center">
					{$i18n.t('Training Outputs')}
					<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
					<span class="text-sm font-normal text-gray-500">{outputs.length}</span>
				</div>

				{#if outputs.length === 0}
					<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-10 text-sm text-center text-gray-500 dark:text-gray-400">
						{$i18n.t('No training outputs yet.')}
					</div>
				{:else}
					<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
						<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded">
							<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5">
								<tr>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Name')}</th>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Path')}</th>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Size')}</th>
									<th scope="col" class="px-3 py-1.5">{$i18n.t('Contents')}</th>
								</tr>
							</thead>
							<tbody>
								{#each outputs as output}
									<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50">
										<td class="px-3 py-2 font-medium text-gray-900 dark:text-white">{output.name}</td>
										<td class="px-3 py-2 font-mono text-gray-500 dark:text-gray-400">{output.path}</td>
										<td class="px-3 py-2 text-gray-500">{formatBytes(output.size_bytes)}</td>
										<td class="px-3 py-2">
											<div class="flex gap-1">
												{#if output.has_model}
													<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">model</span>
												{/if}
												{#if output.has_config}
													<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">config</span>
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

		</div>
	</div>
{/if}
