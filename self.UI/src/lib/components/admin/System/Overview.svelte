<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import CpuCard from './CpuCard.svelte';
	import GpuCard from './GpuCard.svelte';
	import MemoryCard from './MemoryCard.svelte';
	import GpuTotalCard from './GpuTotalCard.svelte';
	const i18n = getContext('i18n');

	export let resources;
	export let onViewProcesses: (sortBy: string) => void;

	let clockDisplay = '';
	let clockInterval: ReturnType<typeof setInterval> | null = null;
	let serverTimeOffset = 0; // difference between server time and local clock
	let tzAbbr = '';

	function syncClock(containerTime: string) {
		// Parse "YYYY-MM-DD HH:MM:SS TZ" from server
		const match = containerTime.match(/^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) (.+)$/);
		if (!match) return;
		const [, datePart, timePart, tz] = match;
		tzAbbr = tz;
		// Parse as a point in time (treat as UTC for offset calc — the offset handles the rest)
		const serverMs = new Date(`${datePart}T${timePart}Z`).getTime();
		serverTimeOffset = serverMs - Date.now();
	}

	function tickClock() {
		const now = new Date(Date.now() + serverTimeOffset);
		const pad = (n: number) => String(n).padStart(2, '0');
		clockDisplay = `${now.getUTCFullYear()}-${pad(now.getUTCMonth() + 1)}-${pad(now.getUTCDate())} ${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())}:${pad(now.getUTCSeconds())} ${tzAbbr}`;
	}

	onMount(() => {
		if (resources?.container_time) {
			syncClock(resources.container_time);
		}
		tickClock();
		clockInterval = setInterval(tickClock, 1000);
	});

	onDestroy(() => {
		if (clockInterval) clearInterval(clockInterval);
	});

	// Re-sync when resources update with new server time
	$: if (resources?.container_time) {
		syncClock(resources.container_time);
	}
</script>

{#if resources}
	<div class="flex flex-col gap-6">
		<!-- Container Clock -->
		{#if clockDisplay}
			<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
					<path fill-rule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm.75-13a.75.75 0 0 0-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 0 0 0-1.5h-3.25V5Z" clip-rule="evenodd" />
				</svg>
				<span class="font-mono">{clockDisplay}</span>
			</div>
		{/if}

		<!-- CPU Section -->
		{#if resources.cpus && resources.cpus.length > 0}
			<div>
				<h3 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
					{$i18n.t('CPU')}
				</h3>
				<div class="grid grid-cols-1 {resources.cpus.length > 1 ? 'lg:grid-cols-2' : ''} gap-4">
					{#each resources.cpus as cpu (cpu.index)}
						<CpuCard {cpu} {onViewProcesses} />
					{/each}
				</div>
			</div>
		{/if}

		<!-- GPU Section -->
		{#if resources.gpus && resources.gpus.length > 0}
			<div>
				<h3 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
					{$i18n.t('GPU')}
				</h3>
				<div class="grid grid-cols-1 {resources.gpus.length > 1 ? 'lg:grid-cols-2' : ''} gap-4">
					{#each resources.gpus as gpu (gpu.index)}
						<GpuCard {gpu} {onViewProcesses} />
					{/each}
				</div>
			</div>
		{/if}

		<!-- Memory Section -->
		{#if resources.memory}
			<div>
				<h3 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
					{$i18n.t('Memory')}
				</h3>
				<div class="grid grid-cols-1 gap-4">
					<MemoryCard memory={resources.memory} {onViewProcesses} />
				</div>
			</div>
		{/if}

		<!-- All GPU VRAM Section -->
		{#if resources.gpus && resources.gpus.length > 0}
			<div>
				<h3 class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">
					{$i18n.t('All GPU Memory')}
				</h3>
				<div class="grid grid-cols-1 gap-4">
					<GpuTotalCard
						vramUsedMb={resources.gpu_vram_used_mb}
						vramTotalMb={resources.gpu_vram_total_mb}
						{onViewProcesses}
					/>
				</div>
			</div>
		{/if}

	</div>
{:else}
	<div class="text-gray-500 dark:text-gray-400 text-center py-8">
		{$i18n.t('No system data available')}
	</div>
{/if}
