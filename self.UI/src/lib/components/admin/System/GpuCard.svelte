<script lang="ts">
	import { getContext } from 'svelte';
	import ArcGauge from './ArcGauge.svelte';

	const i18n = getContext('i18n');

	export let gpu;
	export let onViewProcesses: (sortBy: string) => void;

	$: vramPercent =
		gpu.vram_total_mb > 0 ? (gpu.vram_used_mb / gpu.vram_total_mb) * 100 : 0;

	function formatMb(mb) {
		if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
		return `${Math.round(mb)} MB`;
	}
</script>

<div class="bg-gray-50 dark:bg-gray-900 rounded-2xl p-4 flex flex-col items-center gap-2">
	<div class="text-sm font-medium text-gray-700 dark:text-gray-300 text-center">
		{gpu.name}
	</div>

	<div class="flex flex-wrap justify-center gap-4">
		<div class="flex flex-col items-center">
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Utilization')}</div>
			<ArcGauge percent={gpu.utilization} label="" size={120} />
		</div>

		<div class="flex flex-col items-center">
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('VRAM')}</div>
			<ArcGauge
				percent={vramPercent}
				label="{formatMb(gpu.vram_used_mb)} / {formatMb(gpu.vram_total_mb)}"
				size={120}
			/>
		</div>
	</div>

	<button
		class="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 transition"
		on:click={() => onViewProcesses('vram_mb')}
	>
		{$i18n.t('View Processes')} &rarr;
	</button>
</div>
