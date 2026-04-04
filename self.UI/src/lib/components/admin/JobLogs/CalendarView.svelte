<script lang="ts">
	import dayjs from 'dayjs';
	import isoWeek from 'dayjs/plugin/isoWeek';
	import { onMount } from 'svelte';
	import type { ScheduledJob } from '$lib/apis/schedule';

	dayjs.extend(isoWeek);

	export let jobs: ScheduledJob[] = [];

	type ViewMode = 'month' | 'week' | 'day';
	let viewMode: ViewMode = 'month';
	let current = dayjs();

	const DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
	const HOURS = Array.from({ length: 24 }, (_, i) => i);

	const prev = () => {
		if (viewMode === 'month') current = current.subtract(1, 'month');
		else if (viewMode === 'week') current = current.subtract(1, 'week');
		else current = current.subtract(1, 'day');
	};
	const next = () => {
		if (viewMode === 'month') current = current.add(1, 'month');
		else if (viewMode === 'week') current = current.add(1, 'week');
		else current = current.add(1, 'day');
	};
	const goToday = () => { current = dayjs(); };

	$: title = (() => {
		if (viewMode === 'month') return current.format('MMMM YYYY');
		if (viewMode === 'week') {
			const s = current.startOf('isoWeek');
			const e = current.endOf('isoWeek');
			return s.month() === e.month()
				? `${s.format('MMM D')} – ${e.format('D, YYYY')}`
				: `${s.format('MMM D')} – ${e.format('MMM D, YYYY')}`;
		}
		return current.format('dddd, MMMM D, YYYY');
	})();

	$: notCurrentPeriod = (() => {
		const t = dayjs();
		if (viewMode === 'month') return !current.isSame(t, 'month');
		if (viewMode === 'week') return !current.startOf('isoWeek').isSame(t.startOf('isoWeek'), 'day');
		return !current.isSame(t, 'day');
	})();

	// Month grid — weeks starting Monday
	$: monthWeeks = (() => {
		if (viewMode !== 'month') return [] as dayjs.Dayjs[][];
		const start = current.startOf('month').startOf('isoWeek');
		const end = current.endOf('month').endOf('isoWeek');
		const days: dayjs.Dayjs[] = [];
		let d = start;
		while (!d.isAfter(end)) { days.push(d); d = d.add(1, 'day'); }
		const result: dayjs.Dayjs[][] = [];
		for (let i = 0; i < days.length; i += 7) result.push(days.slice(i, i + 7));
		return result;
	})();

	// Week columns Mon–Sun
	$: weekDays = (() => {
		if (viewMode === 'month') return [] as dayjs.Dayjs[];
		if (viewMode === 'week') {
			const s = current.startOf('isoWeek');
			return Array.from({ length: 7 }, (_, i) => s.add(i, 'day'));
		}
		return [current] as dayjs.Dayjs[];
	})();

	$: jobsByDay = jobs.reduce((acc, job) => {
		if (job.scheduled_for) {
			const key = dayjs(job.scheduled_for * 1000).format('YYYY-MM-DD');
			(acc[key] = acc[key] ?? []).push(job);
		}
		return acc;
	}, {} as Record<string, ScheduledJob[]>);

	const statusDot = (s: string) => ({
		pending: 'bg-amber-400', scheduled: 'bg-violet-500', queued: 'bg-blue-400',
		running: 'bg-indigo-500', completed: 'bg-green-500', failed: 'bg-red-500',
		cancelled: 'bg-gray-400'
	}[s] ?? 'bg-gray-400');

	const statusPill = (s: string) => ({
		pending: 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300',
		scheduled: 'bg-violet-50 dark:bg-violet-900/20 text-violet-700 dark:text-violet-300',
		queued: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
		running: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300',
		completed: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300',
		failed: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300',
		cancelled: 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
	}[s] ?? 'bg-gray-100 dark:bg-gray-800 text-gray-500');

	const jobLabel = (job: ScheduledJob) =>
		job.type === 'curation' ? (job.pipeline_name ?? 'Curate')
		: job.type === 'training' ? (job.course_name ?? 'Train')
		: (job.benchmark ?? 'Eval');

	const today = dayjs();
	const VIEW_MODES: ViewMode[] = ['month', 'week', 'day'];

	// Pre-computed lookup: "YYYY-MM-DD-H" → jobs — avoids per-cell filtering in template
	$: jobsByDayHour = jobs.reduce((acc, job) => {
		if (job.scheduled_for) {
			const t = dayjs(job.scheduled_for * 1000);
			const key = `${t.format('YYYY-MM-DD')}-${t.hour()}`;
			(acc[key] = acc[key] ?? []).push(job);
		}
		return acc;
	}, {} as Record<string, ScheduledJob[]>);

	const formatHour = (h: number) =>
		h === 0 ? '12 AM' : h < 12 ? `${h} AM` : h === 12 ? '12 PM' : `${h - 12} PM`;

	let timeGridEl: HTMLElement | null = null;

	const setView = (v: ViewMode) => {
		viewMode = v;
		if (v === 'week' || v === 'day') {
			// Schedule scroll after DOM updates — no reactive dependency on timeGridEl
			setTimeout(() => {
				if (timeGridEl) timeGridEl.scrollTop = Math.max(0, (today.hour() - 1) * 48);
			}, 0);
		}
	};

	// Selected slot for new event creation
	let selectedSlot: { date: string; hour?: number } | null = null;
	const selectSlot = (date: string, hour?: number) => {
		selectedSlot = { date, hour };
	};

	onMount(() => {
		if (viewMode === 'week' || viewMode === 'day') {
			setTimeout(() => {
				if (timeGridEl) timeGridEl.scrollTop = Math.max(0, (today.hour() - 1) * 48);
			}, 0);
		}
	});
</script>

<div class="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden flex flex-col" style="min-height: 0">
	<!-- Toolbar -->
	<div class="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-850 border-b border-gray-200 dark:border-gray-800 flex-none">
		<!-- Left: nav -->
		<div class="flex items-center gap-1">
			<button
				class="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition"
				on:click={prev}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4 text-gray-500">
					<path fill-rule="evenodd" d="M9.78 4.22a.75.75 0 0 1 0 1.06L7.06 8l2.72 2.72a.75.75 0 1 1-1.06 1.06L5.47 8.53a.75.75 0 0 1 0-1.06l3.25-3.25a.75.75 0 0 1 1.06 0Z" clip-rule="evenodd" />
				</svg>
			</button>
			<button
				class="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition"
				on:click={next}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4 text-gray-500">
					<path fill-rule="evenodd" d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06L7.28 11.78a.75.75 0 0 1-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
				</svg>
			</button>

			<span class="text-sm font-medium text-gray-900 dark:text-white ml-1">{title}</span>

			{#if notCurrentPeriod}
				<button
					class="ml-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition px-1.5 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
					on:click={goToday}
				>
					Today
				</button>
			{/if}
		</div>

		<!-- Right: view tabs -->
		<div class="flex items-center gap-0.5 bg-gray-200/60 dark:bg-gray-800 rounded-lg p-0.5">
			{#each VIEW_MODES as v}
				<button
					class="px-2.5 py-1 rounded-md text-xs font-medium transition
						{viewMode === v
							? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
							: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}"
					on:click={() => setView(v)}
				>
					{v.charAt(0).toUpperCase() + v.slice(1)}
				</button>
			{/each}
		</div>
	</div>

	<!-- ═══ MONTH VIEW ═══ -->
	{#if viewMode === 'month'}
		<!-- Day-of-week headers -->
		<div class="grid grid-cols-7 border-b border-gray-200 dark:border-gray-800 flex-none">
			{#each DAY_SHORT as label}
				<div class="py-1.5 text-center text-[11px] font-medium text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-850">
					{label}
				</div>
			{/each}
		</div>

		<!-- Month grid -->
		<div class="flex-1 overflow-y-auto">
			{#each monthWeeks as week, wi}
				<div class="grid grid-cols-7 {wi < monthWeeks.length - 1 ? 'border-b border-gray-100 dark:border-gray-800/60' : ''}">
					{#each week as day}
						{@const isCurrentMonth = day.month() === current.month()}
						{@const isToday = day.isSame(today, 'day')}
						{@const dayJobs = jobsByDay[day.format('YYYY-MM-DD')] ?? []}
						<button
							class="min-h-[80px] p-1.5 border-r border-gray-100 dark:border-gray-800/60 last:border-r-0 text-left
								{isCurrentMonth ? 'bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50' : 'bg-gray-50/60 dark:bg-gray-900/40'}
								transition"
							on:click={() => selectSlot(day.format('YYYY-MM-DD'))}
						>
							<div class="mb-1 flex justify-center">
								<span
									class="size-5 flex items-center justify-center rounded-full text-xs
										{isToday
											? 'bg-black dark:bg-white text-white dark:text-black font-semibold'
											: isCurrentMonth
											? 'text-gray-700 dark:text-gray-200'
											: 'text-gray-300 dark:text-gray-600'}"
								>
									{day.date()}
								</span>
							</div>
							<div class="flex flex-col gap-0.5">
								{#each dayJobs.slice(0, 3) as job}
									<div class="flex items-center gap-1 rounded px-1 py-0.5 {statusPill(job.status)}">
										<span class="size-1.5 rounded-full flex-none {statusDot(job.status)}"></span>
										<span class="text-[10px] truncate">{jobLabel(job)}</span>
									</div>
								{/each}
								{#if dayJobs.length > 3}
									<div class="text-[10px] text-gray-400 dark:text-gray-500 px-1">
										+{dayJobs.length - 3} more
									</div>
								{/if}
							</div>
						</button>
					{/each}
				</div>
			{/each}
		</div>

	<!-- ═══ WEEK / DAY VIEW ═══ -->
	{:else}
		<!-- Day column headers -->
		<div
			class="border-b border-gray-200 dark:border-gray-800 flex-none"
			style="display: grid; grid-template-columns: 48px repeat({weekDays.length}, 1fr)"
		>
			<div class="bg-gray-50 dark:bg-gray-850"></div>
			{#each weekDays as day}
				{@const isToday = day.isSame(today, 'day')}
				<div class="py-2 text-center border-l border-gray-100 dark:border-gray-800/60 bg-gray-50 dark:bg-gray-850">
					<div class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase">{day.format('ddd')}</div>
					<div class="mt-0.5 flex justify-center">
						<span
							class="size-6 flex items-center justify-center rounded-full text-sm
								{isToday
									? 'bg-black dark:bg-white text-white dark:text-black font-semibold'
									: 'text-gray-700 dark:text-gray-200'}"
						>
							{day.date()}
						</span>
					</div>
				</div>
			{/each}
		</div>

		<!-- Time grid (scrollable) -->
		<div class="flex-1 overflow-y-auto" bind:this={timeGridEl}>
			{#each HOURS as hour}
				<div
					class="border-b border-gray-100 dark:border-gray-800/40"
					style="display: grid; grid-template-columns: 48px repeat({weekDays.length}, 1fr); min-height: 48px"
				>
					<!-- Hour label -->
					<div class="relative">
						{#if hour !== 0}
							<span class="absolute -top-2 right-2 text-[10px] text-gray-400 dark:text-gray-500 whitespace-nowrap select-none">
								{formatHour(hour)}
							</span>
						{/if}
					</div>

					<!-- Day cells -->
					{#each weekDays as day}
						{@const slotJobs = jobsByDayHour[`${day.format('YYYY-MM-DD')}-${hour}`] ?? []}
						{@const isToday = day.isSame(today, 'day')}
						{@const isCurrentHour = isToday && today.hour() === hour}
						<button
							class="border-l border-gray-100 dark:border-gray-800/60 p-0.5 text-left relative
								{isCurrentHour ? 'bg-indigo-50/40 dark:bg-indigo-900/10' : isToday ? 'bg-gray-50/40 dark:bg-gray-850/20' : ''}
								hover:bg-gray-50 dark:hover:bg-gray-800/30 transition"
							on:click={() => selectSlot(day.format('YYYY-MM-DD'), hour)}
						>
							{#each slotJobs as job}
								<div class="rounded px-1 py-0.5 text-[10px] truncate {statusPill(job.status)} mb-0.5 flex items-center gap-1">
									<span class="size-1.5 rounded-full flex-none {statusDot(job.status)}"></span>
									{jobLabel(job)}
								</div>
							{/each}
						</button>
					{/each}
				</div>
			{/each}
		</div>
	{/if}
</div>
