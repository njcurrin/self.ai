<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let processData;
	export let sortBy: string = 'cpu_percent';

	let sortDirection = 'desc';

	function toggleSort(column) {
		if (sortBy === column) {
			sortDirection = sortDirection === 'desc' ? 'asc' : 'desc';
		} else {
			sortBy = column;
			sortDirection = 'desc';
		}
	}

	$: isNumericSort = !['name', 'container'].includes(sortBy);

	$: sortedProcesses = processData?.processes
		? [...processData.processes].sort((a, b) => {
				const aVal = a[sortBy] ?? (isNumericSort ? 0 : '');
				const bVal = b[sortBy] ?? (isNumericSort ? 0 : '');
				if (isNumericSort) {
					return sortDirection === 'desc' ? bVal - aVal : aVal - bVal;
				}
				const cmp = String(aVal).localeCompare(String(bVal));
				return sortDirection === 'desc' ? -cmp : cmp;
			})
		: [];

	function formatMb(mb) {
		if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
		if (mb >= 1) return `${mb.toFixed(1)} MB`;
		return `${(mb * 1024).toFixed(0)} KB`;
	}

	const columns = [
		{ key: 'container', label: 'Container', numeric: false },
		{ key: 'name', label: 'Name', numeric: false },
		{ key: 'pid', label: 'PID', numeric: true },
		{ key: 'cpu_percent', label: 'CPU %', numeric: true },
		{ key: 'memory_mb', label: 'Memory', numeric: true },
		{ key: 'vram_mb', label: 'VRAM', numeric: true }
	];
</script>

<div class="overflow-x-auto">
	<table class="w-full text-sm text-left">
		<thead class="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
			<tr>
				{#each columns as col}
					<th class="px-3 py-2">
						<button
							class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200 transition"
							on:click={() => toggleSort(col.key)}
						>
							{$i18n.t(col.label)}
							{#if sortBy === col.key}
								<span class="text-xs">
									{sortDirection === 'desc' ? '▼' : '▲'}
								</span>
							{/if}
						</button>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each sortedProcesses as proc (proc.pid)}
				<tr class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition">
					<td class="px-3 py-2 text-gray-500 dark:text-gray-400 text-xs max-w-[150px] truncate">
						{proc.container}
					</td>
					<td class="px-3 py-2 text-gray-700 dark:text-gray-300 font-medium max-w-[200px] truncate">
						{proc.name}
					</td>
					<td class="px-3 py-2 text-gray-500 dark:text-gray-400 font-mono text-xs">
						{proc.pid}
					</td>
					<td class="px-3 py-2 text-gray-700 dark:text-gray-300">
						{proc.cpu_percent.toFixed(1)}%
					</td>
					<td class="px-3 py-2 text-gray-700 dark:text-gray-300">
						{formatMb(proc.memory_mb)}
					</td>
					<td class="px-3 py-2 text-gray-700 dark:text-gray-300">
						{#if proc.vram_mb > 0}
							{formatMb(proc.vram_mb)}
						{:else}
							<span class="text-gray-400 dark:text-gray-600">—</span>
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>

	{#if sortedProcesses.length === 0}
		<div class="text-center text-gray-500 dark:text-gray-400 py-8">
			{$i18n.t('No processes found')}
		</div>
	{/if}
</div>
