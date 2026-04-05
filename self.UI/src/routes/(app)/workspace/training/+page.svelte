<script>
	import { onMount } from 'svelte';
	import { knowledge } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import Training from '$lib/components/workspace/Training.svelte';

	onMount(async () => {
		knowledge.set(await getKnowledgeBases(localStorage.token));
	});
</script>

<Training />
