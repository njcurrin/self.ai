<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { BenchmarkConfig, BenchmarkConfigUpdate } from '$lib/apis/benchmarks';
	import { listBenchmarks, updateBenchmark } from '$lib/apis/benchmarks';

	const i18n: any = getContext('i18n');

	let items: BenchmarkConfig[] = [];
	let loading = true;

	// Track per-row edit state: id → draft value
	let edits: Record<string, { max_duration_minutes: number; notes: string }> = {};
	let saving: Record<string, boolean> = {};
	let errors: Record<string, string> = {};

	onMount(async () => {
		try {
			items = await listBenchmarks(localStorage.token);
			// Initialize edit state from loaded data
			edits = Object.fromEntries(
				items.map((b) => [b.id, { max_duration_minutes: b.max_duration_minutes, notes: b.notes ?? '' }])
			);
		} catch {
			// non-fatal
		}
		loading = false;
	});

	async function save(b: BenchmarkConfig) {
		const draft = edits[b.id];
		if (!draft) return;
		saving = { ...saving, [b.id]: true };
		errors = { ...errors, [b.id]: '' };
		try {
			const form: BenchmarkConfigUpdate = {
				max_duration_minutes: draft.max_duration_minutes,
				notes: draft.notes || undefined
			};
			const updated = await updateBenchmark(localStorage.token, b.id, form);
			items = items.map((x) => (x.id === b.id ? updated : x));
		} catch (e: any) {
			errors = { ...errors, [b.id]: typeof e === 'string' ? e : $i18n.t('Save failed') };
		}
		saving = { ...saving, [b.id]: false };
	}

	function isDirty(b: BenchmarkConfig): boolean {
		const d = edits[b.id];
		if (!d) return false;
		return d.max_duration_minutes !== b.max_duration_minutes || (d.notes || '') !== (b.notes ?? '');
	}

	// Group by eval_type
	$: grouped = items.reduce(
		(acc, b) => {
			(acc[b.eval_type] = acc[b.eval_type] ?? []).push(b);
			return acc;
		},
		{} as Record<string, BenchmarkConfig[]>
	);

	$: evalTypes = Object.keys(grouped).sort();

	const typeLabel = (t: string) =>
		({ 'lm-eval': 'LM Eval', bigcode: 'BigCode', curator: 'Curator' }[t] ?? t);
</script>

<div class="space-y-6">
	<div>
		<h3 class="text-sm font-semibold">{$i18n.t('Benchmark Durations')}</h3>
		<p class="text-xs text-gray-400 mt-0.5">
			{$i18n.t('Max runtime limits used by the dispatcher to decide if a benchmark fits in the remaining window time.')}
		</p>
	</div>

	{#if loading}
		<div class="text-sm text-gray-400 py-4 text-center">{$i18n.t('Loading…')}</div>
	{:else if items.length === 0}
		<div class="text-sm text-gray-400 py-4 text-center">
			{$i18n.t('No benchmarks configured. Run migrations to seed defaults.')}
		</div>
	{:else}
		{#each evalTypes as evalType}
			<div>
				<h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
					{typeLabel(evalType)}
				</h4>
				<div class="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
					<table class="w-full text-sm">
						<thead>
							<tr class="bg-gray-50 dark:bg-gray-850 text-xs text-gray-500 dark:text-gray-400">
								<th class="text-left px-4 py-2 font-medium">{$i18n.t('Benchmark')}</th>
								<th class="text-right px-4 py-2 font-medium w-36">{$i18n.t('Max minutes')}</th>
								<th class="text-left px-4 py-2 font-medium">{$i18n.t('Notes')}</th>
								<th class="w-16"></th>
							</tr>
						</thead>
						<tbody>
							{#each grouped[evalType] as b (b.id)}
								<tr class="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50/40 dark:hover:bg-gray-900/40">
									<td class="px-4 py-2 font-mono text-xs text-gray-700 dark:text-gray-300">
										{b.benchmark}
									</td>
									<td class="px-4 py-2 text-right">
										<input
											type="number"
											min="1"
											max="10080"
											class="w-24 text-sm text-right border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 bg-transparent outline-none focus:ring-1 focus:ring-blue-500"
											bind:value={edits[b.id].max_duration_minutes}
										/>
									</td>
									<td class="px-4 py-2">
										<input
											type="text"
											class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 bg-transparent outline-none focus:ring-1 focus:ring-blue-500"
											placeholder={$i18n.t('Optional note')}
											bind:value={edits[b.id].notes}
										/>
									</td>
									<td class="px-4 py-2 text-right">
										{#if errors[b.id]}
											<span class="text-[11px] text-red-500">{errors[b.id]}</span>
										{:else if isDirty(b)}
											<button
												type="button"
												class="text-xs px-2 py-1 rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90 disabled:opacity-50"
												disabled={saving[b.id]}
												on:click={() => save(b)}
											>
												{saving[b.id] ? $i18n.t('…') : $i18n.t('Save')}
											</button>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/each}
	{/if}
</div>
