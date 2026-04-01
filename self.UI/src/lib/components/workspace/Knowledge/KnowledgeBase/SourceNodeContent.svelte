<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let config: Record<string, any> = {};

	const ALL_EXTENSIONS = [
		{ ext: '.txt', label: 'TXT' },
		{ ext: '.md', label: 'Markdown' },
		{ ext: '.rst', label: 'RST' },
		{ ext: '.tex', label: 'TeX' },
		{ ext: '.docx', label: 'DOCX' },
		{ ext: '.doc', label: 'DOC' },
		{ ext: '.rtf', label: 'RTF' },
		{ ext: '.csv', label: 'CSV' },
		{ ext: '.tsv', label: 'TSV' },
		{ ext: '.json', label: 'JSON' },
		{ ext: '.jsonl', label: 'JSONL' },
		{ ext: '.xml', label: 'XML' },
		{ ext: '.html', label: 'HTML' },
		{ ext: '.yaml', label: 'YAML' },
		{ ext: '.log', label: 'LOG' },
		{ ext: '.pdf', label: 'PDF' },
	];

	$: selectedExtensions = (config.extensions as string[]) ?? ['.txt', '.md'];

	function toggleExtension(ext: string) {
		const current = [...selectedExtensions];
		const idx = current.indexOf(ext);
		if (idx >= 0) {
			current.splice(idx, 1);
		} else {
			current.push(ext);
		}
		dispatch('configchange', { ...config, extensions: current });
	}
</script>

<div class="text-gray-600 dark:text-gray-400 space-y-2">
	<div class="font-medium text-gray-800 dark:text-gray-200 text-[11px] uppercase tracking-wide">
		File Types
	</div>
	<div class="flex flex-wrap gap-1">
		{#each ALL_EXTENSIONS as { ext, label }}
			<button
				class="px-1.5 py-0.5 rounded text-[10px] font-medium transition border"
				class:bg-emerald-100={selectedExtensions.includes(ext)}
				class:dark:bg-emerald-900={selectedExtensions.includes(ext)}
				class:text-emerald-700={selectedExtensions.includes(ext)}
				class:dark:text-emerald-300={selectedExtensions.includes(ext)}
				class:border-emerald-300={selectedExtensions.includes(ext)}
				class:dark:border-emerald-700={selectedExtensions.includes(ext)}
				class:bg-gray-50={!selectedExtensions.includes(ext)}
				class:dark:bg-gray-800={!selectedExtensions.includes(ext)}
				class:text-gray-400={!selectedExtensions.includes(ext)}
				class:border-gray-200={!selectedExtensions.includes(ext)}
				class:dark:border-gray-700={!selectedExtensions.includes(ext)}
				on:click={() => toggleExtension(ext)}
			>
				{label}
			</button>
		{/each}
	</div>
	<div class="pt-1 border-t border-gray-100 dark:border-gray-800">
		<div class="mb-0.5 text-[10px] text-gray-500">Text Field</div>
		<input
			type="text"
			value={config.text_field ?? 'text'}
			on:input={(e) => dispatch('configchange', { ...config, text_field: e.currentTarget.value })}
			class="w-full rounded bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-2 py-1 text-[11px] text-gray-700 dark:text-gray-300 outline-none"
			placeholder="text"
		/>
	</div>
	<div class="text-[10px] text-gray-400 pt-1 border-t border-gray-100 dark:border-gray-800">
		{selectedExtensions.length} type{selectedExtensions.length !== 1 ? 's' : ''} selected &middot; filters files in this KB
	</div>
</div>
