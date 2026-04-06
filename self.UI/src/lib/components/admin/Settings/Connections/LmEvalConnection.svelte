<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext<any>('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let url = '';
	export let idx = 0;
</script>

<div class="flex gap-1.5">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}/health"`, { url })}
		placement="top-start"
	>
		<input
			class="w-full text-sm bg-transparent outline-none"
			placeholder={$i18n.t('Enter URL (e.g. http://self-lm-eval:8096)')}
			bind:value={url}
			on:change={() => onSubmit({ url })}
		/>
	</Tooltip>

	<div class="flex gap-1">
		<Tooltip content={$i18n.t('Delete')} className="self-start">
			<button
				class="self-center p-1 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition text-red-500"
				on:click={onDelete}
				type="button"
				aria-label="Delete connection"
			>
				<span class="text-base leading-none">×</span>
			</button>
		</Tooltip>
	</div>
</div>
