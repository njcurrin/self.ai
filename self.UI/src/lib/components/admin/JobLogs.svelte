<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Schedule from './Schedule.svelte';
	import CalendarView from './JobLogs/CalendarView.svelte';
	import WindowsView from './JobLogs/WindowsView.svelte';
	import QueueMonitor from './JobLogs/QueueMonitor.svelte';
	import { getAllScheduledJobs, type ScheduledJob } from '$lib/apis/schedule';

	const i18n: any = getContext('i18n');

	let selectedTab = 'schedule';

	let loaded = false;
	let jobs: ScheduledJob[] = [];

	onMount(async () => {
		try {
			jobs = await getAllScheduledJobs(localStorage.token);
		} catch (e) {
			// non-fatal — calendar will be empty
		}
		loaded = true;

		const containerElement = document.getElementById('job-logs-tabs-container');
		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) containerElement.scrollLeft += event.deltaY;
			});
		}
	});
</script>

{#if loaded}
<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
	<!-- Left sidebar tabs -->
	<div
		id="job-logs-tabs-container"
		class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
	>
		<button
			class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab === 'schedule'
				? ''
				: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => { selectedTab = 'schedule'; }}
		>
			<div class="self-center mr-2">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
					<path fill-rule="evenodd" d="M4 1.75a.75.75 0 0 1 1.5 0V3h5V1.75a.75.75 0 0 1 1.5 0V3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2V1.75ZM4.5 6a1 1 0 0 0-1 1v4.5a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-7Z" clip-rule="evenodd" />
				</svg>
			</div>
			<div class="self-center">{$i18n.t('Schedule')}</div>
		</button>

		<button
			class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab === 'windows'
				? ''
				: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => { selectedTab = 'windows'; }}
		>
			<div class="self-center mr-2">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
					<path d="M2 2.75A.75.75 0 0 1 2.75 2h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 2.75ZM2 8a.75.75 0 0 1 .75-.75h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 8Zm.75 4.5a.75.75 0 0 0 0 1.5h10.5a.75.75 0 0 0 0-1.5H2.75Z" />
				</svg>
			</div>
			<div class="self-center">{$i18n.t('Windows')}</div>
		</button>

		<button
			class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab === 'queue'
				? ''
				: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => { selectedTab = 'queue'; }}
		>
			<div class="self-center mr-2">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
					<path d="M3 4.75a1 1 0 1 0 0-2 1 1 0 0 0 0 2ZM6.25 3a.75.75 0 0 0 0 1.5h7a.75.75 0 0 0 0-1.5h-7ZM6.25 7.25a.75.75 0 0 0 0 1.5h7a.75.75 0 0 0 0-1.5h-7ZM6.25 11.5a.75.75 0 0 0 0 1.5h7a.75.75 0 0 0 0-1.5h-7ZM4 8a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM3 13.25a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" />
				</svg>
			</div>
			<div class="self-center">{$i18n.t('Queue')}</div>
		</button>

		<button
			class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab === 'job-logs'
				? ''
				: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
			on:click={() => { selectedTab = 'job-logs'; }}
		>
			<div class="self-center mr-2">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
					<path fill-rule="evenodd" d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm2 1.5a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1H4Zm0 2.5a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1H4Zm0 2.5a.5.5 0 0 0 0 1h4a.5.5 0 0 0 0-1H4Z" clip-rule="evenodd" />
				</svg>
			</div>
			<div class="self-center">{$i18n.t('GPU Job Logs')}</div>
		</button>
	</div>

	<!-- Content area -->
	<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">
		{#if selectedTab === 'job-logs'}
			<Schedule />
		{:else if selectedTab === 'schedule'}
			<CalendarView {jobs} />
		{:else if selectedTab === 'windows'}
			<WindowsView />
		{:else if selectedTab === 'queue'}
			<QueueMonitor />
		{/if}
	</div>
</div>
{/if}
