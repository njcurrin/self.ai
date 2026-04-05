<script>
	import { getContext, tick, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Leaderboard from './Evaluations/Leaderboard.svelte';
	import Feedbacks from './Evaluations/Feedbacks.svelte';
	import CodeTests from './Evaluations/CodeTests.svelte';
	import LanguageTests from './Evaluations/LanguageTests.svelte';
	import Schedule from './Evaluations/Schedule.svelte';

	import { getAllFeedbacks } from '$lib/apis/evaluations';

	const i18n = getContext('i18n');

	let selectedTab = 'leaderboard';

	let loaded = false;
	let feedbacks = [];

	onMount(async () => {
		feedbacks = await getAllFeedbacks(localStorage.token);
		loaded = true;

		const containerElement = document.getElementById('users-tabs-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}
	});
</script>

{#if loaded}
	<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
		<div
			id="users-tabs-container"
			class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
		>
			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'leaderboard'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'leaderboard';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm6 5.75a.75.75 0 0 1 1.5 0v3.5a.75.75 0 0 1-1.5 0v-3.5Zm-2.75 1.5a.75.75 0 0 1 1.5 0v2a.75.75 0 0 1-1.5 0v-2Zm-2 .75a.75.75 0 0 0-.75.75v.5a.75.75 0 0 0 1.5 0v-.5a.75.75 0 0 0-.75-.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Leaderboard')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'feedbacks'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'feedbacks';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M5.25 2A2.25 2.25 0 0 0 3 4.25v9a.75.75 0 0 0 1.183.613l1.692-1.195 1.692 1.195a.75.75 0 0 0 .866 0l1.692-1.195 1.693 1.195A.75.75 0 0 0 13 13.25v-9A2.25 2.25 0 0 0 10.75 2h-5.5Zm3.03 3.28a.75.75 0 0 0-1.06-1.06L4.97 6.47a.75.75 0 0 0 0 1.06l2.25 2.25a.75.75 0 0 0 1.06-1.06l-.97-.97h1.315c.76 0 1.375.616 1.375 1.375a.75.75 0 0 0 1.5 0A2.875 2.875 0 0 0 8.625 6.25H7.311l.97-.97Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Feedbacks')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'codetests'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'codetests';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm4.78 1.97a.75.75 0 0 1 0 1.06L5.81 8l.97.97a.75.75 0 1 1-1.06 1.06l-1.5-1.5a.75.75 0 0 1 0-1.06l1.5-1.5a.75.75 0 0 1 1.06 0Zm2.44 1.06a.75.75 0 0 1 1.06-1.06l1.5 1.5a.75.75 0 0 1 0 1.06l-1.5 1.5a.75.75 0 1 1-1.06-1.06l.97-.97-.97-.97Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Code Tests')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'langtests'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'langtests';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M11 5a.75.75 0 0 1 .688.452l3.25 7.5a.75.75 0 1 1-1.376.596L12.89 12H9.109l-.672 1.548a.75.75 0 1 1-1.376-.596l3.25-7.5A.75.75 0 0 1 11 5Zm-1.24 5.5h2.48L11 7.636 9.76 10.5ZM1.75 6a.75.75 0 0 1 .75.75v2.5h2.5v-2.5a.75.75 0 0 1 1.5 0v6.5a.75.75 0 0 1-1.5 0v-2.5H2.5v2.5a.75.75 0 0 1-1.5 0v-6.5A.75.75 0 0 1 1.75 6Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Language Tests')}</div>
			</button>

			<button
				class="px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition {selectedTab ===
				'schedule'
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					selectedTab = 'schedule';
				}}
			>
				<div class=" self-center mr-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 1.75a.75.75 0 0 1 1.5 0V3h5V1.75a.75.75 0 0 1 1.5 0V3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2V1.75ZM4.5 6a1 1 0 0 0-1 1v4.5a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-7Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center">{$i18n.t('Schedule')}</div>
			</button>
		</div>

		<div class="flex-1 mt-1 lg:mt-0 overflow-y-scroll">
			{#if selectedTab === 'leaderboard'}
				<Leaderboard {feedbacks} />
			{:else if selectedTab === 'feedbacks'}
				<Feedbacks {feedbacks} />
			{:else if selectedTab === 'codetests'}
				<CodeTests />
			{:else if selectedTab === 'langtests'}
				<LanguageTests />
			{:else if selectedTab === 'schedule'}
				<Schedule />
			{/if}
		</div>
	</div>
{/if}
