<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { WindowForm, WindowSlot, JobWindow } from '$lib/apis/windows';
	import { createWindow, updateWindow } from '$lib/apis/windows';

	const i18n = getContext<any>('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let window: JobWindow | null = null; // null = create mode

	const JOB_TYPES = ['training', 'lm-eval', 'bigcode', 'curator'];

	// Form state
	let name = '';
	let notes = '';
	let startDate = '';
	let startTime = '';
	let endDate = '';
	let endTime = '';
	let preferredJobType = 'training';
	let enabled = true;
	let slots: WindowSlot[] = [];
	let error = '';
	let saving = false;

	function toLocalInputs(ts: number): { date: string; time: string } {
		const d = new Date(ts * 1000);
		const date = d.toLocaleDateString('sv');
		const time = d.toTimeString().slice(0, 5);
		return { date, time };
	}

	function fromLocalInputs(date: string, time: string): number {
		return Math.floor(new Date(`${date}T${time}`).getTime() / 1000);
	}

	function computedDuration(): string {
		try {
			const s = fromLocalInputs(startDate, startTime);
			const e = fromLocalInputs(endDate, endTime);
			const mins = Math.round((e - s) / 60);
			if (mins <= 0) return '';
			if (mins < 60) return `${mins}m`;
			return `${Math.floor(mins / 60)}h ${mins % 60}m`;
		} catch {
			return '';
		}
	}
	let _lastInitKey = ''
	$: if (show) {
		const key = `${show}::${window?.id ?? `new`}`
		if (key !== _lastInitKey) {
			_lastInitKey = key
			if (window) {
				name = window.name;
				notes = window.notes ?? '';
				preferredJobType = window.preferred_job_type;
				enabled = window.enabled;
				slots = window.slots.map((s) => ({ ...s }));
				const s = toLocalInputs(window.start_at);
				const e = toLocalInputs(window.end_at);
				startDate = s.date;
				startTime = s.time;
				endDate = e.date;
				endTime = e.time;
			} else {
				name = '';
				notes = '';
				preferredJobType = 'training';
				enabled = true;
				slots = [];
				const now = new Date();
				startDate = now.toLocaleDateString('sv');
				startTime = now.toTimeString().slice(0, 5);
				const later = new Date(now.getTime() + 2 * 3600 * 1000);
				endDate = later.toLocaleDateString('sv');
				endTime = later.toTimeString().slice(0, 5);
			}
		}
		error = '';
	}
	$: if (!show) _lastInitKey = '';

	async function save() {
		error = '';
		const start_at = fromLocalInputs(startDate, startTime);
		const end_at = fromLocalInputs(endDate, endTime);
		if (end_at <= start_at) {
			error = $i18n.t('End time must be after start time');
			return;
		}
		const form: WindowForm = {
			name,
			notes: notes || undefined,
			start_at,
			end_at,
			preferred_job_type: preferredJobType,
			enabled,
			slots
		};
		saving = true;
		try {
			const result = window
				? await updateWindow(localStorage.token, window.id, form)
				: await createWindow(localStorage.token, form);
			dispatch('saved', result);
			show = false;
		} catch (e: any) {
			error = typeof e === 'string' ? e : $i18n.t('Failed to save window');
		} finally {
			saving = false;
		}
	}

	function addSlot() {
		const usedTypes = new Set(slots.map((s) => s.job_type));
		const nextType = JOB_TYPES.find((t) => !usedTypes.has(t)) ?? 'training';
		slots = [...slots, { job_type: nextType, max_concurrent: 1, min_remaining_minutes: 0 }];
	}

	function removeSlot(i: number) {
		slots = slots.filter((_, idx) => idx !== i);
	}
</script>

{#if show}
	<div
		class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
		role="dialog"
		aria-modal="true"
	>
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden">
			<div class="px-6 pt-5 pb-4 border-b border-gray-100 dark:border-gray-800">
				<h2 class="text-base font-semibold">
					{window ? $i18n.t('Edit Window') : $i18n.t('Create Window')}
				</h2>
			</div>

			<div class="px-6 py-4 space-y-4 overflow-y-auto max-h-[70vh]">
				<!-- Name -->
				<div>
					<label class="block text-xs font-medium mb-1">{$i18n.t('Name')}</label>
					<input
						class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-transparent outline-none focus:ring-1 focus:ring-blue-500"
						bind:value={name}
						placeholder={$i18n.t('e.g. Evening GPU Window')}
					/>
				</div>

				<!-- Start / End -->
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label class="block text-xs font-medium mb-1">{$i18n.t('Start')}</label>
						<input type="date" bind:value={startDate} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-transparent outline-none" />
						<input type="time" bind:value={startTime} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-transparent outline-none mt-1" />
					</div>
					<div>
						<label class="block text-xs font-medium mb-1">
							{$i18n.t('End')}
							{#if computedDuration()}
								<span class="text-gray-400 font-normal ml-1">({computedDuration()})</span>
							{/if}
						</label>
						<input type="date" bind:value={endDate} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-transparent outline-none" />
						<input type="time" bind:value={endTime} class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-transparent outline-none mt-1" />
					</div>
				</div>

				<!-- Preferred job type -->
				<div>
					<label class="block text-xs font-medium mb-1">{$i18n.t('Preferred job type')}</label>
					<select
						bind:value={preferredJobType}
						class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-transparent outline-none"
					>
						{#each JOB_TYPES as t}
							<option value={t}>{t}</option>
						{/each}
					</select>
				</div>

				<!-- Slots -->
				<div>
					<div class="flex justify-between items-center mb-1">
						<label class="text-xs font-medium">{$i18n.t('Allowed job types')}</label>
						<button type="button" class="text-xs text-blue-500 hover:underline" on:click={addSlot}>
							+ {$i18n.t('Add type')}
						</button>
					</div>
					{#if slots.length === 0}
						<p class="text-xs text-gray-400">{$i18n.t('No types configured — no jobs will run.')}</p>
					{/if}
					{#each slots as slot, i}
						<div class="flex gap-2 items-start mb-1.5">
							<select
								bind:value={slot.job_type}
								class="text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 bg-transparent outline-none flex-1"
							>
								{#each JOB_TYPES as t}
									<option value={t}>{t}</option>
								{/each}
							</select>
							<div class="flex flex-col gap-1">
								<input
									type="number"
									min="1"
									bind:value={slot.max_concurrent}
									class="w-16 text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 bg-transparent outline-none"
									title={$i18n.t('Max concurrent')}
								/>
								<input
									type="number"
									min="0"
									bind:value={slot.min_remaining_minutes}
									class="w-16 text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 bg-transparent outline-none"
									title={$i18n.t('Min remaining minutes')}
								/>
							</div>
							<button
								type="button"
								class="text-red-400 hover:text-red-600 mt-1"
								on:click={() => removeSlot(i)}
							>×</button>
						</div>
					{/each}
					{#if slots.length > 0}
						<p class="text-xs text-gray-400 mt-0.5">{$i18n.t('Max concurrent / Min remaining minutes per type')}</p>
					{/if}
				</div>

				<!-- Notes -->
				<div>
					<label class="block text-xs font-medium mb-1">{$i18n.t('Notes')} ({$i18n.t('optional')})</label>
					<textarea
						bind:value={notes}
						rows="2"
						class="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 bg-transparent outline-none resize-none"
					/>
				</div>

				<!-- Enabled -->
				<div class="flex items-center gap-2">
					<input type="checkbox" id="window-enabled" bind:checked={enabled} class="rounded" />
					<label for="window-enabled" class="text-sm">{$i18n.t('Enabled')}</label>
				</div>

				{#if error}
					<p class="text-xs text-red-500">{error}</p>
				{/if}
			</div>

			<div class="px-6 py-4 border-t border-gray-100 dark:border-gray-800 flex justify-end gap-2">
				<button
					type="button"
					class="px-4 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
					on:click={() => (show = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					type="button"
					class="px-4 py-1.5 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:opacity-90 disabled:opacity-50"
					on:click={save}
					disabled={saving || !name}
				>
					{saving ? $i18n.t('Saving…') : $i18n.t('Save')}
				</button>
			</div>
		</div>
	</div>
{/if}
