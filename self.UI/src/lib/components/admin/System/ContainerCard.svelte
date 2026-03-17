<script lang="ts">
	import { getContext } from 'svelte';
	import ArcGauge from './ArcGauge.svelte';

	const i18n = getContext('i18n');

	export let container;

	$: memPercent =
		container.memory_limit_mb > 0
			? (container.memory_used_mb / container.memory_limit_mb) * 100
			: 0;

	function formatMb(mb) {
		if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
		return `${Math.round(mb)} MB`;
	}
</script>

<div class="bg-gray-50 dark:bg-gray-900 rounded-2xl p-4 flex flex-col items-center gap-2">
	<div class="text-sm font-medium text-gray-700 dark:text-gray-300 text-center">
		{container.name}
	</div>
	<div class="text-xs text-gray-400 dark:text-gray-500 truncate max-w-full text-center">
		{container.image}
	</div>

	<div class="flex flex-wrap justify-center gap-4 mt-1">
		<div class="flex flex-col items-center">
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('CPU')}</div>
			<ArcGauge percent={container.cpu_percent} label="" size={110} />
		</div>

		<div class="flex flex-col items-center">
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Memory')}</div>
			<ArcGauge
				percent={memPercent}
				label="{formatMb(container.memory_used_mb)} / {formatMb(container.memory_limit_mb)}"
				size={110}
			/>
		</div>
	</div>

	<div class="flex items-center gap-1.5 mt-1">
		<span
			class="w-2 h-2 rounded-full {container.status === 'running'
				? 'bg-green-500'
				: 'bg-yellow-500'}"
		></span>
		<span class="text-xs text-gray-500 dark:text-gray-400">{container.status}</span>
	</div>
</div>
