<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import dayjs from 'dayjs';
	import type { QueueItem } from '$lib/apis/queue';
	import { getQueue, runNow, promoteJob } from '$lib/apis/queue';

	const i18n = getContext<any>('i18n');

	const POLL_INTERVAL_MS = 15_000;

	let items: QueueItem[] = [];
	let loading = true;
	let actionInFlight: string | null = null; // item id being acted on
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	async function load() {
		try {
			items = await getQueue(localStorage.token);
		} catch {
			// non-fatal
		}
		loading = false;
	}

	onMount(() => {
		load();
		pollTimer = setInterval(load, POLL_INTERVAL_MS);
	});

	onDestroy(() => {
		if (pollTimer !== null) clearInterval(pollTimer);
	});

	async function handleRunNow(item: QueueItem) {
		actionInFlight = item.id;
		try {
			await runNow(localStorage.token, item.job_type, item.id);
			await load();
		} catch (e: any) {
			alert(typeof e === 'string' ? e : $i18n.t('Failed to promote job'));
		}
		actionInFlight = null;
	}

	async function handlePromote(item: QueueItem) {
		actionInFlight = item.id;
		try {
			await promoteJob(localStorage.token, item.job_type, item.id);
			await load();
		} catch (e: any) {
			alert(typeof e === 'string' ? e : $i18n.t('Failed to promote job'));
		}
		actionInFlight = null;
	}

	function formatAge(ts: number): string {
		const secs = Math.floor(Date.now() / 1000) - ts;
		if (secs < 60) return `${secs}s`;
		if (secs < 3600) return `${Math.floor(secs / 60)}m`;
		return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
	}

	const priorityBadge = (p: string) =>
		p === 'run_now'
			? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
			: p === 'high'
			? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
			: 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400';

	const priorityLabel = (p: string) =>
		p === 'run_now' ? $i18n.t('Run now') : p === 'high' ? $i18n.t('High') : $i18n.t('Normal');

	const statusDot = (s: string) =>
		({
			pending: 'bg-amber-400',
			scheduled: 'bg-violet-500',
			queued: 'bg-blue-400',
			running: 'bg-indigo-500',
			paused: 'bg-orange-400'
		}[s] ?? 'bg-gray-400');

	const statusLabel = (s: string) =>
		({
			pending: $i18n.t('Pending'),
			scheduled: $i18n.t('Scheduled'),
			queued: $i18n.t('Queued'),
			running: $i18n.t('Running'),
			paused: $i18n.t('Paused')
		}[s] ?? s);

	const typeLabel = (t: string) =>
		({
			training: $i18n.t('Training'),
			'lm-eval': $i18n.t('LM Eval'),
			bigcode: $i18n.t('BigCode'),
			curator: $i18n.t('Curation')
		}[t] ?? t);

	$: running = items.filter((i) => i.status === 'running');
	$: queued = items.filter((i) => i.status === 'queued');
	$: pending = items.filter((i) => i.status !== 'running' && i.status !== 'queued');
</script>

<div class="space-y-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h3 class="text-sm font-semibold">{$i18n.t('GPU Queue')}</h3>
			<p class="text-xs text-gray-400 mt-0.5">{$i18n.t('Refreshes every 15 seconds')}</p>
		</div>
		<button
			type="button"
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
			title={$i18n.t('Refresh')}
			on:click={load}
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
				<path
					fill-rule="evenodd"
					d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.37l-.84-.841a4.5 4.5 0 0 0-7.08 1.011.75.75 0 1 1-1.32-.711 6 6 0 0 1 9.45-1.35l.84.84V3.227a.75.75 0 0 1 .762-.75Zm-.911 7.5A.75.75 0 0 1 13.199 11a6 6 0 0 1-9.45 1.35l-.84-.84v1.371a.75.75 0 0 1-1.5 0V9.698a.75.75 0 0 1 .75-.75h3.182a.75.75 0 0 1 0 1.5H4.013l.841.841a4.5 4.5 0 0 0 7.08-1.011.75.75 0 0 1 1.41.699Z"
					clip-rule="evenodd"
				/>
			</svg>
		</button>
	</div>

	{#if loading}
		<div class="text-sm text-gray-400 py-8 text-center">{$i18n.t('Loading…')}</div>
	{:else if items.length === 0}
		<div class="text-sm text-gray-400 py-8 text-center rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
			{$i18n.t('Queue is empty')}
		</div>
	{:else}
		<!-- Running -->
		{#if running.length > 0}
			<section>
				<p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
					{$i18n.t('Running')} ({running.length})
				</p>
				<div class="space-y-1.5">
					{#each running as item (item.id)}
						<div class="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-800 px-4 py-2.5 bg-white dark:bg-gray-900">
							<span class="size-2 rounded-full flex-none {statusDot(item.status)} animate-pulse"></span>
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<span class="text-sm font-medium truncate">{item.label}</span>
									<span class="text-[11px] text-gray-400">{typeLabel(item.job_type)}</span>
								</div>
								{#if item.model_id}
									<div class="text-xs text-gray-400 truncate">{item.model_id}</div>
								{/if}
							</div>
							<span class="text-[11px] text-gray-400 flex-none">{formatAge(item.created_at)}</span>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Queued (dispatched, waiting for worker pick-up) -->
		{#if queued.length > 0}
			<section>
				<p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
					{$i18n.t('Queued')} ({queued.length})
				</p>
				<div class="space-y-1.5">
					{#each queued as item (item.id)}
						<div class="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-800 px-4 py-2.5 bg-white dark:bg-gray-900">
							<span class="size-2 rounded-full flex-none {statusDot(item.status)}"></span>
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<span class="text-sm font-medium truncate">{item.label}</span>
									<span class="text-[11px] text-gray-400">{typeLabel(item.job_type)}</span>
									<span class="text-[11px] px-1.5 py-0.5 rounded-full font-medium {priorityBadge(item.priority)}">
										{priorityLabel(item.priority)}
									</span>
								</div>
								{#if item.model_id}
									<div class="text-xs text-gray-400 truncate">{item.model_id}</div>
								{/if}
							</div>
							<span class="text-[11px] text-gray-400 flex-none">{formatAge(item.created_at)}</span>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Pending / scheduled -->
		{#if pending.length > 0}
			<section>
				<p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
					{$i18n.t('Waiting')} ({pending.length})
				</p>
				<div class="space-y-1.5">
					{#each pending as item (item.id)}
						<div class="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-800 px-4 py-2.5 bg-white dark:bg-gray-900">
							<span class="size-2 rounded-full flex-none {statusDot(item.status)}"></span>
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<span class="text-sm font-medium truncate">{item.label}</span>
									<span class="text-[11px] text-gray-400">{typeLabel(item.job_type)}</span>
									<span class="text-[11px] text-gray-500">{statusLabel(item.status)}</span>
									{#if item.priority !== 'normal'}
										<span class="text-[11px] px-1.5 py-0.5 rounded-full font-medium {priorityBadge(item.priority)}">
											{priorityLabel(item.priority)}
										</span>
									{/if}
								</div>
								{#if item.model_id}
									<div class="text-xs text-gray-400 truncate">{item.model_id}</div>
								{/if}
							</div>
							<div class="flex items-center gap-1 flex-none">
								<span class="text-[11px] text-gray-400 mr-1">{formatAge(item.created_at)}</span>
								<!-- Promote to high (only if currently normal) -->
								{#if item.priority === 'normal'}
									<button
										type="button"
										class="p-1 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/20 text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 transition disabled:opacity-40"
										title={$i18n.t('Promote to high priority')}
										disabled={actionInFlight === item.id}
										on:click={() => handlePromote(item)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
											<path fill-rule="evenodd" d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" clip-rule="evenodd" />
										</svg>
									</button>
								{/if}
								<!-- Run now (bypass windows) -->
								{#if item.priority !== 'run_now'}
									<button
										type="button"
										class="p-1 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition disabled:opacity-40"
										title={$i18n.t('Run now (bypass windows)')}
										disabled={actionInFlight === item.id}
										on:click={() => handleRunNow(item)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
											<path d="M3 3.732a1.5 1.5 0 0 1 2.305-1.265l6.706 4.267a1.5 1.5 0 0 1 0 2.531l-6.706 4.268A1.5 1.5 0 0 1 3 12.267V3.732Z" />
										</svg>
									</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</div>
