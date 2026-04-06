<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import dayjs from 'dayjs';
	import type { JobWindow } from '$lib/apis/windows';
	import { listWindows, deleteWindow } from '$lib/apis/windows';
	import WindowModal from './WindowModal.svelte';

	const i18n = getContext<any>('i18n');

	let windows: JobWindow[] = [];
	let loading = true;
	let showCompleted = false;
	let showModal = false;
	let editingWindow: JobWindow | null = null;
	let deletingId: string | null = null;

	async function load() {
		try {
			windows = await listWindows(localStorage.token);
		} catch {
			// non-fatal
		}
		loading = false;
	}

	onMount(load);

	// Sort: active → upcoming → disabled → completed
	const ORDER: Record<string, number> = { active: 0, upcoming: 1, completed: 2 };
	$: current = windows
		.filter((w) => w.status !== 'completed')
		.sort((a, b) => {
			if (a.status === b.status) return a.start_at - b.start_at;
			const ao = a.enabled ? ORDER[a.status] ?? 1 : 1.5;
			const bo = b.enabled ? ORDER[b.status] ?? 1 : 1.5;
			return ao - bo;
		});
	$: completed = windows.filter((w) => w.status === 'completed');

	function openCreate() {
		editingWindow = null;
		showModal = true;
	}

	function openEdit(w: JobWindow) {
		editingWindow = w;
		showModal = true;
	}

	async function handleDelete(w: JobWindow) {
		if (!confirm($i18n.t('Delete window "{{name}}"?', { name: w.name }))) return;
		deletingId = w.id;
		try {
			await deleteWindow(localStorage.token, w.id);
			windows = windows.filter((x) => x.id !== w.id);
		} catch (e: any) {
			alert(typeof e === 'string' ? e : $i18n.t('Failed to delete window'));
		}
		deletingId = null;
	}

	function handleSaved(event: CustomEvent<JobWindow>) {
		const saved = event.detail;
		const idx = windows.findIndex((w) => w.id === saved.id);
		if (idx >= 0) {
			windows = windows.map((w) => (w.id === saved.id ? saved : w));
		} else {
			windows = [saved, ...windows];
		}
	}

	function formatTs(ts: number) {
		return dayjs(ts * 1000).format('MMM D, YYYY h:mm A');
	}

	function durationLabel(w: JobWindow): string {
		const mins = Math.round((w.end_at - w.start_at) / 60);
		if (mins < 60) return `${mins}m`;
		return `${Math.floor(mins / 60)}h ${mins % 60 > 0 ? ` ${mins % 60}m` : ''}`.trim();
	}

	function statusBadgeClass(w: JobWindow): string {
		if (w.status === 'active')
			return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
		if (w.status === 'upcoming' && w.enabled)
			return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
		if (w.status === 'completed')
			return 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500';
		return 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400';
	}

	function statusLabel(w: JobWindow): string {
		if (w.status === 'active') return $i18n.t('Active');
		if (!w.enabled) return $i18n.t('Disabled');
		if (w.status === 'upcoming') return $i18n.t('Upcoming');
		return $i18n.t('Completed');
	}
</script>

<div class="space-y-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h3 class="text-sm font-semibold">{$i18n.t('GPU Windows')}</h3>
			<p class="text-xs text-gray-400 mt-0.5">
				{$i18n.t('Time ranges when GPU jobs are dispatched')}
			</p>
		</div>
		<button
			type="button"
			class="px-3 py-1.5 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90"
			on:click={openCreate}
		>
			+ {$i18n.t('New Window')}
		</button>
	</div>

	{#if loading}
		<div class="text-sm text-gray-400 py-8 text-center">{$i18n.t('Loading…')}</div>
	{:else if current.length === 0 && completed.length === 0}
		<div class="text-sm text-gray-400 py-8 text-center rounded-xl border border-dashed border-gray-200 dark:border-gray-700">
			{$i18n.t('No windows yet. Create one to schedule GPU job dispatch.')}
		</div>
	{:else}
		<!-- Active / upcoming / disabled windows -->
		{#if current.length > 0}
			<div class="space-y-2">
				{#each current as w (w.id)}
					<div class="rounded-xl border border-gray-200 dark:border-gray-800 px-4 py-3 bg-white dark:bg-gray-900 {w.status === 'active' ? 'ring-1 ring-green-400/50' : ''}">
						<div class="flex items-start justify-between gap-2">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<span class="text-sm font-medium truncate">{w.name}</span>
									<span class="text-[11px] px-1.5 py-0.5 rounded-full font-medium {statusBadgeClass(w)}">
										{statusLabel(w)}
									</span>
									{#if w.status === 'active'}
										<span class="inline-flex items-center gap-1 text-[11px] text-green-600 dark:text-green-400">
											<span class="size-1.5 rounded-full bg-green-500 animate-pulse"></span>
											{$i18n.t('Running now')}
										</span>
									{/if}
								</div>
								<div class="mt-1 text-xs text-gray-400 dark:text-gray-500 space-y-0.5">
									<div>{formatTs(w.start_at)} → {formatTs(w.end_at)} <span class="text-gray-300 dark:text-gray-600">({durationLabel(w)})</span></div>
									<div class="flex items-center gap-3 flex-wrap">
										<span>{$i18n.t('Preferred')}: <span class="text-gray-600 dark:text-gray-300">{w.preferred_job_type}</span></span>
										{#if w.slots.length > 0}
											<span>{w.slots.map((s) => `${s.job_type}×${s.max_concurrent}`).join(', ')}</span>
										{:else}
											<span class="text-amber-500">{$i18n.t('No slots — jobs will not run')}</span>
										{/if}
									</div>
									{#if w.notes}
										<div class="italic text-gray-400">{w.notes}</div>
									{/if}
								</div>
							</div>
							<div class="flex items-center gap-1 flex-none">
								<button
									type="button"
									class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
									title={$i18n.t('Edit')}
									on:click={() => openEdit(w)}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
										<path d="M13.488 2.513a1.75 1.75 0 0 0-2.475 0L6.75 6.774a2.75 2.75 0 0 0-.596.892l-.848 2.047a.75.75 0 0 0 .98.98l2.047-.848a2.75 2.75 0 0 0 .892-.596l4.261-4.263a1.75 1.75 0 0 0 0-2.474ZM4.75 3.5A2.25 2.25 0 0 0 2.5 5.75v5.5A2.25 2.25 0 0 0 4.75 13.5h5.5A2.25 2.25 0 0 0 12.5 11.25V9a.75.75 0 0 0-1.5 0v2.25a.75.75 0 0 1-.75.75h-5.5a.75.75 0 0 1-.75-.75v-5.5a.75.75 0 0 1 .75-.75H7a.75.75 0 0 0 0-1.5H4.75Z" />
									</svg>
								</button>
								<button
									type="button"
									class="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition disabled:opacity-50"
									title={$i18n.t('Delete')}
									disabled={deletingId === w.id}
									on:click={() => handleDelete(w)}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
										<path fill-rule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clip-rule="evenodd" />
									</svg>
								</button>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Completed (collapsible) -->
		{#if completed.length > 0}
			<div>
				<button
					type="button"
					class="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 hover:text-gray-700 dark:hover:text-gray-200 transition"
					on:click={() => (showCompleted = !showCompleted)}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-3 transition-transform {showCompleted ? 'rotate-90' : ''}"
					>
						<path
							fill-rule="evenodd"
							d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06L7.28 11.78a.75.75 0 0 1-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z"
							clip-rule="evenodd"
						/>
					</svg>
					{$i18n.t('Completed')} ({completed.length})
				</button>

				{#if showCompleted}
					<div class="space-y-2">
						{#each completed as w (w.id)}
							<div class="rounded-xl border border-gray-100 dark:border-gray-800 px-4 py-3 bg-gray-50/50 dark:bg-gray-900/50 opacity-70">
								<div class="flex items-start justify-between gap-2">
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 flex-wrap">
											<span class="text-sm font-medium truncate text-gray-500 dark:text-gray-400">{w.name}</span>
											<span class="text-[11px] px-1.5 py-0.5 rounded-full font-medium {statusBadgeClass(w)}">
												{statusLabel(w)}
											</span>
										</div>
										<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
											{formatTs(w.start_at)} → {formatTs(w.end_at)} ({durationLabel(w)})
										</div>
									</div>
									<div class="flex items-center gap-1 flex-none">
										<button
											type="button"
											class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
											title={$i18n.t('Edit')}
											on:click={() => openEdit(w)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
												<path d="M13.488 2.513a1.75 1.75 0 0 0-2.475 0L6.75 6.774a2.75 2.75 0 0 0-.596.892l-.848 2.047a.75.75 0 0 0 .98.98l2.047-.848a2.75 2.75 0 0 0 .892-.596l4.261-4.263a1.75 1.75 0 0 0 0-2.474ZM4.75 3.5A2.25 2.25 0 0 0 2.5 5.75v5.5A2.25 2.25 0 0 0 4.75 13.5h5.5A2.25 2.25 0 0 0 12.5 11.25V9a.75.75 0 0 0-1.5 0v2.25a.75.75 0 0 1-.75.75h-5.5a.75.75 0 0 1-.75-.75v-5.5a.75.75 0 0 1 .75-.75H7a.75.75 0 0 0 0-1.5H4.75Z" />
											</svg>
										</button>
										<button
											type="button"
											class="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition disabled:opacity-50"
											title={$i18n.t('Delete')}
											disabled={deletingId === w.id}
											on:click={() => handleDelete(w)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
												<path fill-rule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clip-rule="evenodd" />
											</svg>
										</button>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>

<WindowModal bind:show={showModal} window={editingWindow} on:saved={handleSaved} />
