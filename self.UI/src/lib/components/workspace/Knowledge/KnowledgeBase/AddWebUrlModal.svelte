<script lang="ts">
	import { afterUpdate } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { isValidHttpUrl } from '$lib/utils';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let loading = false;
	export let title = 'Scrape a webpage';
	export let managedClose = false; // when true, parent controls closing after submit
	export let showLimitInput = false;
	export let showMaxDepthInput = false;
	export let showPollIntervalInput = false;
	export let showMax403Input = false;
	export let showIncludePathsInput = false;
	export let showExcludePathsInput = false;
	export let showRegexOnFullUrlInput = false;
	export let showCrawlEntireDomainInput = false;
	export let showBatchSizeInput = false;
	export let viewOnly = false; // when true, show logs only (no form)
	export let crawlProgress: { completed: number; total: number; savedCount?: number } | null = null;
	export let crawlLogs: string[] = [];

	let url = '';
	let limit = 10;
	let maxDepth = 3;
	let crawlDelay = 2;
	let max403s = 5;
	let includePaths = '';
	let excludePaths = '';
	let regexOnFullUrl = false;
	let crawlEntireDomain = false;
	let batchSize = 10;
	let logEl: HTMLDivElement | null = null;

	// Auto-scroll log to bottom after every DOM update
	afterUpdate(() => {
		if (logEl) logEl.scrollTop = logEl.scrollHeight;
	});

	const closeModal = () => {
		show = false;
		url = '';
		limit = 10;
		maxDepth = 3;
		crawlDelay = 2;
		max403s = 5;
		includePaths = '';
		excludePaths = '';
		regexOnFullUrl = false;
		crawlEntireDomain = false;
		batchSize = 10;
	};

	const submitHandler = () => {
		const trimmedUrl = url.trim();

		if (!isValidHttpUrl(trimmedUrl)) {
			toast.error($i18n.t('URL invalid. Please try again.'));
			return;
		}

		dispatch('submit', {
			url: trimmedUrl, limit, maxDepth, crawlDelay, max403s,
			includePaths: includePaths.split(',').map((s) => s.trim()).filter(Boolean),
			excludePaths: excludePaths.split(',').map((s) => s.trim()).filter(Boolean),
			regexOnFullUrl,
			crawlEntireDomain,
			batchSize,
		});
		if (!managedClose) closeModal();
	};

	const cancelHandler = () => {
		if (viewOnly) {
			closeModal();
		} else if (loading && managedClose) {
			dispatch('cancel');
		} else {
			closeModal();
		}
	};
</script>

<Modal size="sm" bind:show>
	<div class="px-5 pt-4 pb-5 dark:text-gray-200">
		<div class="flex items-center justify-between pb-3">
			<div class="text-lg font-medium">
				{$i18n.t(viewOnly ? 'Crawl logs' : title)}
			</div>

			<button
				type="button"
				class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
				on:click={cancelHandler}
			>
				{$i18n.t('Cancel')}
			</button>
		</div>

		{#if viewOnly}
			<div class="flex flex-col gap-4">
				{#if crawlLogs.length > 0}
					<div
						bind:this={logEl}
						class="text-xs font-mono bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-2 h-48 overflow-y-auto flex flex-col gap-0.5"
					>
						{#each crawlLogs as entry}
							<div class="text-gray-500 dark:text-gray-400 leading-tight">{entry}</div>
						{/each}
					</div>
				{:else}
					<div class="text-xs text-gray-400 text-center py-4">{$i18n.t('No logs available.')}</div>
				{/if}
				<div class="flex justify-end text-sm font-medium">
					<button
						type="button"
						class="px-3.5 py-2 rounded-full bg-black text-white dark:bg-white dark:text-black"
						on:click={closeModal}
					>
						{$i18n.t('Close')}
					</button>
				</div>
			</div>
		{:else}
			<form class="flex flex-col gap-4" on:submit|preventDefault={submitHandler}>
				<div>
					<div class="mb-1 text-xs text-gray-500">{$i18n.t('URL')}</div>
					<input
						type="url"
						bind:value={url}
						placeholder="https://example.com"
						class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
						autocomplete="off"
						disabled={loading}
					/>
				</div>

				{#if showLimitInput}
					<div>
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Max pages')}</div>
						<input
							type="number"
							bind:value={limit}
							min="1"
							max="500"
							class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
							disabled={loading}
						/>
					</div>
				{/if}

				{#if showMaxDepthInput}
					<div>
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Max depth')}</div>
						<input
							type="number"
							bind:value={maxDepth}
							min="1"
							max="10"
							class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
							disabled={loading}
						/>
					</div>
				{/if}

				{#if showPollIntervalInput}
					<div>
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Crawl delay (seconds)')}</div>
						<input
							type="number"
							bind:value={crawlDelay}
							min="1"
							class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
							disabled={loading}
						/>
					</div>
				{/if}

				{#if showMax403Input}
					<div>
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Cancel after n consecutive 403s (0 = disabled)')}</div>
						<input
							type="number"
							bind:value={max403s}
							min="0"
							class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
							disabled={loading}
						/>
					</div>
				{/if}

				{#if showIncludePathsInput}
					<div>
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Include paths (comma-separated regex, e.g. /docs/.*, /blog/.*)')}</div>
						<input
							type="text"
							bind:value={includePaths}
							placeholder="/docs/.*"
							class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
							disabled={loading}
						/>
					</div>
				{/if}

				{#if showExcludePathsInput}
					<div>
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Exclude paths (comma-separated regex, e.g. /admin/.*, /login)')}</div>
						<input
							type="text"
							bind:value={excludePaths}
							placeholder="/admin/.*"
							class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
							disabled={loading}
						/>
					</div>
				{/if}

				{#if showRegexOnFullUrlInput}
					<label class="flex items-center gap-2 cursor-pointer select-none">
						<input
							type="checkbox"
							bind:checked={regexOnFullUrl}
							disabled={loading}
							class="rounded border-gray-300 dark:border-gray-600 disabled:opacity-50"
						/>
						<span class="text-sm text-gray-700 dark:text-gray-300">{$i18n.t('Match patterns against full URL (including query params)')}</span>
					</label>
				{/if}

				{#if showCrawlEntireDomainInput}
					<label class="flex items-center gap-2 cursor-pointer select-none">
						<input
							type="checkbox"
							bind:checked={crawlEntireDomain}
							disabled={loading}
							class="rounded border-gray-300 dark:border-gray-600 disabled:opacity-50"
						/>
						<span class="text-sm text-gray-700 dark:text-gray-300">{$i18n.t('Crawl entire domain (follow parent/sibling links)')}</span>
					</label>
				{/if}

				{#if showBatchSizeInput}
					<div>
						<div class="mb-1 text-xs text-gray-500">{$i18n.t('Pages per embedding batch')}</div>
						<input
							type="number"
							bind:value={batchSize}
							min="1"
							max="100"
							class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
							disabled={loading}
						/>
					</div>
				{/if}

				{#if loading}
					<div class="text-xs text-gray-400 text-center py-1">
						{#if crawlProgress && crawlProgress.savedCount !== undefined && crawlProgress.completed > 0 && crawlProgress.completed >= crawlProgress.total && crawlProgress.total > 0}
							{$i18n.t('Saving…')} {crawlProgress.savedCount} / {crawlProgress.completed} {$i18n.t('pages embedded')}
						{:else if crawlProgress && crawlProgress.total > 0}
							{crawlProgress.completed} / {crawlProgress.total} {$i18n.t('pages scraped')}
						{:else}
							{$i18n.t('Starting crawl…')}
						{/if}
					</div>

					{#if crawlLogs.length > 0}
						<div
							bind:this={logEl}
							class="text-xs font-mono bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-2 h-36 overflow-y-auto flex flex-col gap-0.5"
						>
							{#each crawlLogs as entry}
								<div class="text-gray-500 dark:text-gray-400 leading-tight">{entry}</div>
							{/each}
						</div>
					{/if}
				{/if}

				<div class="flex justify-end gap-2 text-sm font-medium">
					<button
						type="button"
						class="px-3.5 py-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={closeModal}
					>
						{$i18n.t('Close')}
					</button>

					<button
						type="submit"
						class="px-3.5 py-2 rounded-full bg-black text-white dark:bg-white dark:text-black disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
						disabled={loading}
					>
						{#if loading}
							<svg class="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
							</svg>
							{$i18n.t('Crawling…')}
						{:else}
							{$i18n.t('Save')}
						{/if}
					</button>
				</div>
			</form>
		{/if}
	</div>
</Modal>
