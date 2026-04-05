<script lang="ts">
	import Tooltip from './Tooltip.svelte';

	export let status: string | null | undefined = null;
</script>

{#if status === 'loaded'}
	<Tooltip content="Loaded" className="flex items-center">
		<span class="w-2 h-2 rounded-full bg-green-500 inline-block flex-shrink-0" />
	</Tooltip>
{:else if status === 'loading'}
	<Tooltip content="Loading" className="flex items-center">
		<span class="w-2 h-2 rounded-full bg-yellow-500 inline-block flex-shrink-0 animate-pulse" />
	</Tooltip>
{/if}
