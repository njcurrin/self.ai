<script lang="ts">
	export let percent: number = 0;
	export let label: string = '';
	export let size: number = 160;
	export let strokeWidth: number = 12;

	$: clampedPercent = Math.min(100, Math.max(0, percent));

	// Arc geometry: semicircle from left to right
	$: r = (size - strokeWidth) / 2;
	$: cx = size / 2;
	$: cy = size / 2;

	// SVG arc path (semicircle, left to right)
	$: arcPath = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;

	// stroke-dasharray/offset for fill
	$: arcLength = Math.PI * r;
	$: dashOffset = arcLength * (1 - clampedPercent / 100);

	// Color based on percentage
	$: color =
		clampedPercent >= 85
			? '#ef4444' // red-500
			: clampedPercent >= 60
				? '#eab308' // yellow-500
				: '#22c55e'; // green-500
</script>

<div class="flex flex-col items-center">
	<svg
		width={size}
		height={size / 2 + strokeWidth}
		viewBox="0 0 {size} {size / 2 + strokeWidth}"
		class="overflow-visible"
	>
		<!-- Background arc -->
		<path
			d={arcPath}
			fill="none"
			stroke="currentColor"
			stroke-width={strokeWidth}
			stroke-linecap="round"
			class="text-gray-200 dark:text-gray-700"
		/>

		<!-- Foreground arc (filled portion) -->
		<path
			d={arcPath}
			fill="none"
			stroke={color}
			stroke-width={strokeWidth}
			stroke-linecap="round"
			stroke-dasharray={arcLength}
			stroke-dashoffset={dashOffset}
			class="transition-all duration-700 ease-out"
		/>

		<!-- Percentage text -->
		<text
			x={cx}
			y={cy - 8}
			text-anchor="middle"
			dominant-baseline="auto"
			class="fill-current text-gray-900 dark:text-gray-100"
			font-size={size * 0.18}
			font-weight="600"
		>
			{Math.round(clampedPercent)}%
		</text>

		<!-- Label text -->
		{#if label}
			<text
				x={cx}
				y={cy + size * 0.08}
				text-anchor="middle"
				dominant-baseline="auto"
				class="fill-current text-gray-500 dark:text-gray-400"
				font-size={size * 0.09}
			>
				{label}
			</text>
		{/if}
	</svg>
</div>
