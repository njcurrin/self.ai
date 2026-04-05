<script>
	import { onMount, onDestroy, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getSystemResources, getSystemProcesses } from '$lib/apis/system';
	import { getLlamolotlModelStatus, unloadAllLlamolotlModels } from '$lib/apis/llamolotl';
	import { modelLoadStatus, models } from '$lib/stores';
	import Overview from './System/Overview.svelte';
	import Processes from './System/Processes.svelte';

	const i18n = getContext('i18n');

	let selectedTab = 'overview';
	let processesSortBy = 'cpu_percent';
	let prevTab = selectedTab;

	let resources = null;
	let processes = null;
	let loading = true;
	let unloadingAll = false;
	let pollInterval = null;
	let mounted = false;

	function switchToProcesses(sortBy) {
		processesSortBy = sortBy;
		selectedTab = 'processes';
	}

	async function fetchResources() {
		try {
			resources = await getSystemResources(localStorage.token);
		} catch (err) {
			console.error('Failed to fetch system resources:', err);
		}
	}

	async function fetchProcesses() {
		try {
			processes = await getSystemProcesses(localStorage.token);
		} catch (err) {
			console.error('Failed to fetch system processes:', err);
		}
	}

	async function fetchModelStatus() {
		try {
			const statusMap = await getLlamolotlModelStatus(localStorage.token);
			// Propagate base model status to custom models
			const fullStatusMap = { ...statusMap };
			for (const model of $models) {
				const baseId = model?.info?.base_model_id;
				if (baseId && statusMap[baseId]) {
					fullStatusMap[model.id] = statusMap[baseId];
				}
			}
			modelLoadStatus.set(fullStatusMap);
		} catch (err) {
			// Silently ignore — llamolotl may not be configured
		}
	}

	async function handleUnloadAll() {
		unloadingAll = true;
		try {
			const result = await unloadAllLlamolotlModels(localStorage.token);
			const count = result?.unloaded?.length ?? 0;
			if (count > 0) {
				toast.success($i18n.t(`Unloaded ${count} model(s)`));
			} else {
				toast.info($i18n.t('No models were loaded'));
			}
			await fetchModelStatus();
		} catch (err) {
			toast.error(err?.toString() ?? 'Failed to unload models');
		} finally {
			unloadingAll = false;
		}
	}

	function poll() {
		fetchModelStatus();
		if (selectedTab === 'overview') {
			fetchResources();
		} else {
			fetchProcesses();
		}
	}

	function startPolling() {
		if (pollInterval) clearInterval(pollInterval);
		pollInterval = setInterval(poll, 5000);
	}

	onMount(async () => {
		await Promise.all([fetchResources(), fetchModelStatus()]);
		loading = false;
		mounted = true;
		startPolling();
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});

	// When tab changes after mount, fetch immediately and restart polling
	$: if (mounted && selectedTab !== prevTab) {
		prevTab = selectedTab;
		poll();
		startPolling();
	}

	$: hasLoadedModels = Object.values($modelLoadStatus).some(
		(s) => s === 'loaded' || s === 'loading'
	);
</script>

<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
	<div
		class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
	>
		<button
			class="px-0.5 py-1 min-w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
			'overview'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				selectedTab = 'overview';
			}}
		>
			<div class="self-center mr-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						d="M15.5 2A1.5 1.5 0 0 0 14 3.5v13a1.5 1.5 0 0 0 1.5 1.5h1a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 16.5 2h-1ZM9.5 6A1.5 1.5 0 0 0 8 7.5v9A1.5 1.5 0 0 0 9.5 18h1a1.5 1.5 0 0 0 1.5-1.5v-9A1.5 1.5 0 0 0 10.5 6h-1ZM3.5 10A1.5 1.5 0 0 0 2 11.5v5A1.5 1.5 0 0 0 3.5 18h1A1.5 1.5 0 0 0 6 16.5v-5A1.5 1.5 0 0 0 4.5 10h-1Z"
					/>
				</svg>
			</div>
			<div class="self-center">{$i18n.t('Overview')}</div>
		</button>

		<button
			class="px-0.5 py-1 min-w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
			'processes'
				? ''
				: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => {
				selectedTab = 'processes';
			}}
		>
			<div class="self-center mr-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						fill-rule="evenodd"
						d="M.99 5.24A2.25 2.25 0 0 1 3.25 3h13.5A2.25 2.25 0 0 1 19 5.25l.01 9.5A2.25 2.25 0 0 1 16.76 17H3.26A2.25 2.25 0 0 1 1 14.75l-.01-9.51Zm1.5.01v9.5c0 .414.336.75.75.75h13.5a.75.75 0 0 0 .75-.75v-9.5a.75.75 0 0 0-.75-.75H3.25a.75.75 0 0 0-.75.75ZM6 9.25a.75.75 0 0 1 .75-.75h6.5a.75.75 0 0 1 0 1.5h-6.5A.75.75 0 0 1 6 9.25ZM6.75 12a.75.75 0 0 0 0 1.5h4.5a.75.75 0 0 0 0-1.5h-4.5Z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div class="self-center">{$i18n.t('Processes')}</div>
		</button>

		{#if hasLoadedModels}
			<div class="lg:mt-auto lg:pt-4 lg:border-t dark:border-gray-800">
				<button
					class="px-2 py-1.5 min-w-fit rounded-lg flex items-center gap-2 text-xs font-medium transition
						text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
						disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={handleUnloadAll}
					disabled={unloadingAll}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75Zm0 10.5a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75ZM2 10a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 2 10Z"
							clip-rule="evenodd"
						/>
					</svg>
					{#if unloadingAll}
						{$i18n.t('Unloading...')}
					{:else}
						{$i18n.t('Unload All Models')}
					{/if}
				</button>
			</div>
		{/if}
	</div>

	<div class="flex-1 mt-3 lg:mt-0 overflow-y-scroll pr-1 scrollbar-hidden">
		{#if loading}
			<div class="flex justify-center items-center h-full">
				<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
			</div>
		{:else if selectedTab === 'overview'}
			<Overview {resources} onViewProcesses={switchToProcesses} />
		{:else if selectedTab === 'processes'}
			<Processes processData={processes} sortBy={processesSortBy} />
		{/if}
	</div>
</div>
