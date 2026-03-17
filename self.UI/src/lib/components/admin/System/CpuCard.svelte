<script lang="ts">
	import { getContext } from 'svelte';
	import ArcGauge from './ArcGauge.svelte';

	const i18n = getContext('i18n');

	export let cpu;
	export let onViewProcesses: (sortBy: string) => void;
</script>

<div class="bg-gray-50 dark:bg-gray-900 rounded-2xl p-4 flex flex-col items-center gap-2">
	<div class="text-sm font-medium text-gray-700 dark:text-gray-300 text-center">
		{cpu.model}
	</div>

	<ArcGauge percent={cpu.usage_percent} label="{cpu.cores} Cores" />

	<button
		class="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 transition"
		on:click={() => onViewProcesses('cpu_percent')}
	>
		{$i18n.t('View Processes')} &rarr;
	</button>
</div>
