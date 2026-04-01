<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import {
		getAllScheduledJobs,
		scheduleJob,
		unscheduleJob,
		approveJobNow,
		cancelScheduledJob,
		type ScheduledJob,
		type ScheduledJobType
	} from '$lib/apis/schedule';

	const i18n = getContext('i18n');
	const POLL_MS = 8000;
	const getToken = () => localStorage.getItem('token') ?? '';

	let loading = true;
	let jobs: ScheduledJob[] = [];
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let actionInProgress: Record<string, boolean> = {};

	// Schedule dialog
	let showScheduleDialog = false;
	let scheduleTarget: { id: string; type: ScheduledJobType } | null = null;
	let scheduleDatetime = '';

	// Filter
	let filterType: 'all' | 'training' | 'eval' = 'all';
	let filterStatus: 'all' | 'active' | 'scheduled' | 'completed' = 'active';

	// ── Derived ──────────────────────────────────────────────────────
	$: filteredJobs = jobs.filter((j) => {
		if (filterType !== 'all' && j.type !== filterType) return false;
		if (filterStatus === 'active')
			return ['pending', 'scheduled', 'queued', 'running'].includes(j.status);
		if (filterStatus === 'scheduled') return j.status === 'scheduled';
		if (filterStatus === 'completed')
			return ['completed', 'failed', 'cancelled'].includes(j.status);
		return true;
	});

	$: sortedJobs = [...filteredJobs].sort((a, b) => {
		// Scheduled jobs sorted by scheduled_for, others by created_at
		const statusOrder: Record<string, number> = {
			running: 0,
			queued: 1,
			scheduled: 2,
			pending: 3,
			failed: 4,
			completed: 5,
			cancelled: 6
		};
		const oa = statusOrder[a.status] ?? 9;
		const ob = statusOrder[b.status] ?? 9;
		if (oa !== ob) return oa - ob;
		if (a.status === 'scheduled' && b.status === 'scheduled') {
			return (a.scheduled_for ?? 0) - (b.scheduled_for ?? 0);
		}
		return b.created_at - a.created_at;
	});

	$: scheduledCount = jobs.filter((j) => j.status === 'scheduled').length;
	$: runningCount = jobs.filter((j) => j.status === 'running').length;
	$: queuedCount = jobs.filter((j) => j.status === 'queued').length;
	$: pendingCount = jobs.filter((j) => j.status === 'pending').length;

	// ── Helpers ──────────────────────────────────────────────────────
	const statusClasses = (status: string) => {
		const map: Record<string, string> = {
			pending: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
			scheduled: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
			queued: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300',
			running: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
			completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
			failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
			cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
		};
		return map[status] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
	};

	const typeClasses = (type: ScheduledJobType) => {
		return type === 'training'
			? 'bg-orange-50 text-orange-700 dark:bg-orange-900/20 dark:text-orange-300'
			: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300';
	};

	const jobLabel = (job: ScheduledJob) => {
		if (job.type === 'training') return job.course_name ?? 'Training';
		return job.benchmark ?? 'Evaluation';
	};

	const formatDateTime = (ts: number | null | undefined) => {
		if (!ts) return '';
		return dayjs(ts * 1000).format('YYYY-MM-DD HH:mm');
	};

	// ── Data ─────────────────────────────────────────────────────────
	const refresh = async (quiet = false) => {
		try {
			jobs = await getAllScheduledJobs(getToken());
		} catch (e: any) {
			if (!quiet) toast.error(e?.detail ?? e?.message ?? 'Failed to load jobs');
		} finally {
			loading = false;
		}
	};

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

	// ── Actions ──────────────────────────────────────────────────────
	const openScheduleDialog = (id: string, type: ScheduledJobType, existingTs?: number | null) => {
		scheduleTarget = { id, type };
		// Default to tonight at 10 PM local time
		if (existingTs) {
			scheduleDatetime = dayjs(existingTs * 1000).format('YYYY-MM-DDTHH:mm');
		} else {
			const tonight = dayjs().hour(22).minute(0).second(0);
			const target = tonight.isAfter(dayjs()) ? tonight : tonight.add(1, 'day');
			scheduleDatetime = target.format('YYYY-MM-DDTHH:mm');
		}
		showScheduleDialog = true;
	};

	const confirmSchedule = () => {
		if (!scheduleTarget || !scheduleDatetime) return;
		const ts = Math.floor(new Date(scheduleDatetime).getTime() / 1000);
		const { id, type } = scheduleTarget;
		showScheduleDialog = false;
		withAction(id, async () => {
			await scheduleJob(getToken(), type, id, ts);
			toast.success($i18n.t('Job scheduled.'));
		});
	};

	const handleUnschedule = (job: ScheduledJob) =>
		withAction(job.id, async () => {
			await unscheduleJob(getToken(), job.type, job.id);
			toast.success($i18n.t('Schedule removed.'));
		});

	const handleApproveNow = (job: ScheduledJob) =>
		withAction(job.id, async () => {
			await approveJobNow(getToken(), job.type, job.id);
			toast.success($i18n.t('Job approved and dispatched.'));
		});

	const handleCancel = (job: ScheduledJob) =>
		withAction(job.id, async () => {
			await cancelScheduledJob(getToken(), job.type, job.id);
			toast.success($i18n.t('Job cancelled.'));
		});

	// ── Lifecycle ────────────────────────────────────────────────────
	onMount(async () => {
		await refresh();
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
		<div class="flex justify-between items-center flex-wrap gap-2">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center gap-2">
				{$i18n.t('GPU Job Schedule')}

				{#if runningCount > 0}
					<span
						class="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
					>
						{runningCount} running
					</span>
				{/if}
				{#if queuedCount > 0}
					<span
						class="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"
					>
						{queuedCount} queued
					</span>
				{/if}
				{#if scheduledCount > 0}
					<span
						class="px-2 py-0.5 rounded-full text-xs font-medium bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300"
					>
						{scheduledCount} scheduled
					</span>
				{/if}
				{#if pendingCount > 0}
					<span
						class="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
					>
						{pendingCount} pending
					</span>
				{/if}
			</div>
		</div>

		<!-- Filters -->
		<div class="flex flex-wrap gap-2 mt-2 text-sm">
			<div class="flex rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
				{#each [{ v: 'all', l: 'All Types' }, { v: 'training', l: 'Training' }, { v: 'eval', l: 'Eval' }] as opt}
					<button
						class="px-3 py-1 text-xs font-medium transition {filterType === opt.v
							? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
							: 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850'}"
						on:click={() => {
							filterType = opt.v;
						}}
					>
						{$i18n.t(opt.l)}
					</button>
				{/each}
			</div>
			<div class="flex rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
				{#each [{ v: 'active', l: 'Active' }, { v: 'scheduled', l: 'Scheduled' }, { v: 'completed', l: 'History' }, { v: 'all', l: 'All' }] as opt}
					<button
						class="px-3 py-1 text-xs font-medium transition {filterStatus === opt.v
							? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
							: 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850'}"
						on:click={() => {
							filterStatus = opt.v;
						}}
					>
						{$i18n.t(opt.l)}
					</button>
				{/each}
			</div>
		</div>

		<!-- Job table -->
		<div class="mt-3">
			{#if sortedJobs.length === 0}
				<div
					class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-10 text-sm text-center text-gray-500 dark:text-gray-400"
				>
					{$i18n.t('No jobs match the current filter.')}
				</div>
			{:else}
				<div
					class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5"
				>
					<table
						class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded"
					>
						<thead
							class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
						>
							<tr>
								<th scope="col" class="px-3 py-1.5">Status</th>
								<th scope="col" class="px-3 py-1.5">Type</th>
								<th scope="col" class="px-3 py-1.5">Job</th>
								<th scope="col" class="px-3 py-1.5">Model</th>
								<th scope="col" class="px-3 py-1.5">Scheduled For</th>
								<th scope="col" class="px-3 py-1.5">Submitted</th>
								<th scope="col" class="px-3 py-1.5 text-right">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each sortedJobs as job (job.id)}
								<tr
									class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50"
								>
									<td class="px-3 py-2">
										<span
											class="px-2 py-0.5 rounded-lg text-[11px] font-medium {statusClasses(
												job.status
											)}"
										>
											{job.status}
										</span>
									</td>
									<td class="px-3 py-2">
										<span
											class="px-1.5 py-0.5 rounded text-[10px] font-medium {typeClasses(
												job.type
											)}"
										>
											{job.type === 'training' ? 'Train' : 'Eval'}
										</span>
									</td>
									<td class="px-3 py-2 font-medium text-gray-900 dark:text-white">
										{jobLabel(job)}
									</td>
									<td class="px-3 py-2 font-mono max-w-[200px] truncate">
										{job.model_id}
									</td>
									<td class="px-3 py-2">
										{#if job.scheduled_for}
											<div class="flex flex-col">
												<span class="text-violet-600 dark:text-violet-400 font-medium">
													{formatDateTime(job.scheduled_for)}
												</span>
												<span class="text-[10px] text-gray-400">
													{dayjs(job.scheduled_for * 1000).fromNow()}
												</span>
											</div>
										{:else}
											<span class="text-gray-400">—</span>
										{/if}
									</td>
									<td class="px-3 py-2 text-gray-500">
										<Tooltip content={formatDateTime(job.created_at)}>
											{dayjs(job.created_at * 1000).fromNow()}
										</Tooltip>
									</td>
									<td class="px-3 py-2 text-right">
										<div class="flex items-center justify-end gap-1">
											{#if job.status === 'pending'}
												<Tooltip content={$i18n.t('Schedule')}>
													<button
														class="px-2 py-1 rounded-lg text-[11px] font-medium bg-violet-100 hover:bg-violet-200 text-violet-700 dark:bg-violet-900/30 dark:hover:bg-violet-900/50 dark:text-violet-300 transition disabled:opacity-50"
														on:click={() =>
															openScheduleDialog(job.id, job.type)}
														disabled={!!actionInProgress[job.id]}
													>
														{$i18n.t('Schedule')}
													</button>
												</Tooltip>
												<Tooltip content={$i18n.t('Run Now')}>
													<button
														class="px-2 py-1 rounded-lg text-[11px] font-medium bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-900/30 dark:hover:bg-green-900/50 dark:text-green-300 transition disabled:opacity-50"
														on:click={() => handleApproveNow(job)}
														disabled={!!actionInProgress[job.id]}
													>
														{$i18n.t('Run Now')}
													</button>
												</Tooltip>
											{:else if job.status === 'scheduled'}
												<Tooltip content={$i18n.t('Reschedule')}>
													<button
														class="px-2 py-1 rounded-lg text-[11px] font-medium bg-violet-100 hover:bg-violet-200 text-violet-700 dark:bg-violet-900/30 dark:hover:bg-violet-900/50 dark:text-violet-300 transition disabled:opacity-50"
														on:click={() =>
															openScheduleDialog(
																job.id,
																job.type,
																job.scheduled_for
															)}
														disabled={!!actionInProgress[job.id]}
													>
														{$i18n.t('Reschedule')}
													</button>
												</Tooltip>
												<Tooltip content={$i18n.t('Unschedule')}>
													<button
														class="px-2 py-1 rounded-lg text-[11px] font-medium bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-300 transition disabled:opacity-50"
														on:click={() => handleUnschedule(job)}
														disabled={!!actionInProgress[job.id]}
													>
														{$i18n.t('Unschedule')}
													</button>
												</Tooltip>
												<Tooltip content={$i18n.t('Run Now')}>
													<button
														class="px-2 py-1 rounded-lg text-[11px] font-medium bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-900/30 dark:hover:bg-green-900/50 dark:text-green-300 transition disabled:opacity-50"
														on:click={() => handleApproveNow(job)}
														disabled={!!actionInProgress[job.id]}
													>
														{$i18n.t('Run Now')}
													</button>
												</Tooltip>
											{:else if ['queued', 'running'].includes(job.status)}
												<Tooltip content={$i18n.t('Cancel')}>
													<button
														class="px-2 py-1 rounded-lg text-[11px] font-medium bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900/30 dark:hover:bg-red-900/50 dark:text-red-300 transition disabled:opacity-50"
														on:click={() => handleCancel(job)}
														disabled={!!actionInProgress[job.id]}
													>
														{$i18n.t('Cancel')}
													</button>
												</Tooltip>
											{/if}
											{#if job.error_message}
												<Tooltip content={job.error_message}>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="size-3.5 text-red-500"
													>
														<path
															fill-rule="evenodd"
															d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
															clip-rule="evenodd"
														/>
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
		</div>
	</div>

	<!-- Schedule dialog -->
	{#if showScheduleDialog && scheduleTarget}
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
			on:click|self={() => {
				showScheduleDialog = false;
			}}
		>
			<div
				class="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-xl p-5 w-full max-w-sm mx-4"
			>
				<div class="text-base font-semibold mb-4">{$i18n.t('Schedule Job')}</div>
				<div class="space-y-3">
					<div>
						<label
							class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
							for="schedule-datetime">{$i18n.t('Run at')}</label
						>
						<input
							id="schedule-datetime"
							type="datetime-local"
							bind:value={scheduleDatetime}
							class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-850 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800"
						/>
					</div>
					{#if scheduleDatetime}
						<div class="text-xs text-gray-500 dark:text-gray-400">
							{dayjs(scheduleDatetime).fromNow()}
						</div>
					{/if}
					<div class="flex justify-end gap-2 pt-2">
						<button
							class="px-3 py-1.5 rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => {
								showScheduleDialog = false;
							}}
						>
							{$i18n.t('Cancel')}
						</button>
						<button
							class="px-4 py-1.5 rounded-xl text-sm font-medium bg-violet-600 hover:bg-violet-700 text-white transition"
							on:click={confirmSchedule}
						>
							{$i18n.t('Confirm')}
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
{/if}
