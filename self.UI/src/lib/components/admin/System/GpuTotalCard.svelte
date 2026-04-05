<script lang="ts">
	import { getContext } from 'svelte';
	import ArcGauge from './ArcGauge.svelte';

	const i18n = getContext('i18n');

	export let vramUsedMb: number;
	export let vramTotalMb: number;
	export let onViewProcesses: (sortBy: string) => void;

	$: vramPercent = vramTotalMb > 0 ? (vramUsedMb / vramTotalMb) * 100 : 0;

	function formatMb(mb) {
		if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
		return `${Math.round(mb)} MB`;
	}
</script>

<div class="bg-gray-50 dark:bg-gray-900 rounded-2xl p-4 flex flex-col items-center gap-2">
	<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
		{$i18n.t('All GPU Memory')}
	</div>

	<ArcGauge
		percent={vramPercent}
		label="{formatMb(vramUsedMb)} / {formatMb(vramTotalMb)}"
	/>

	<button
		class="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 transition"
		on:click={() => onViewProcesses('vram_mb')}
	>
		{$i18n.t('View Processes')} &rarr;
	</button>
</div>
