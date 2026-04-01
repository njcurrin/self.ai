<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, createEventDispatcher } from 'svelte';

    import Modal from '$lib/components/common/Modal.svelte';

    const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let title = 'Save the Pipeline';
	export let loading = false;
	export let mode: 'save' | 'load' = 'save';
	export let pipelineConfigs: { id: string; name: string }[] = [];

	

    let name = 'Untitled';
	let selectedConfigId: string | null = null;
	let searchQuery = '';

	$: filteredConfigs = pipelineConfigs.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
	);


    const closeModal = () => {
        show = false;
        name = 'Untitled';
		selectedConfigId = null;
		searchQuery = '';
    }
    
    const submitPipelineHandler = () => {
        if (mode ==='load') {
			if (!selectedConfigId) {
				toast.error($i18n.t('Please select a pipeline from the list'));
				return;
			}
			dispatch('confirm', { fileId: selectedConfigId });
		} else if (mode ==='save') {
			if (name.trim() === '') {
            	toast.error($i18n.t('Cannot Submit an unnamed pipeline'));
            	return;
        	}
        	dispatch('confirm', {name: name.trim()})
		}
        closeModal()
    };


</script>

<Modal size="sm" bind:show>
	<div class="px-5 pt-4 pb-5 dark:text-gray-200">
		<div class="flex items-center justify-between pb-3">
			<div class="text-lg font-medium">
				{$i18n.t(title)}
			</div>
		</div>
	    <form class="flex flex-col gap-4" on:submit|preventDefault={submitPipelineHandler}>
			{#if mode === 'load'}
				<div>
	    			<div class="mb-1 text-xs text-gray-500">{$i18n.t('Load a Pipeline')}</div>
	    			<input
	    				type="text"
	    				bind:value={searchQuery}
	    				placeholder="Search.."
	    				class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
	    				autocomplete="off"
	    			/>
	    		</div>
				<div class="max-h-48 overflow-y-auto flex flex-col gap-1">
					{#each filteredConfigs as config}
					<button
	    				type="button"
	    				class="text-left px-3 py-2 rounded-lg text-sm w-full {selectedConfigId === config.id ? 'bg-black text-white dark:bg-white dark:text-black' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}"
	    				on:click={ () => selectedConfigId = config.id }
	    			>
	    				{config.name}
	    			</button>
					{:else}
						{$i18n.t('No Pipelines found, please create one first')}
					{/each}
				</div>
			{/if}
			{#if mode === 'save'}
				<div>
	    			<div class="mb-1 text-xs text-gray-500">{$i18n.t('Save a Pipeline')}</div>
	    			<input
	    				type="text"
	    				bind:value={name}
	    				placeholder="Untitled"
	    				class="w-full rounded-xl bg-transparent px-3 py-2 text-sm outline-none border border-gray-200 dark:border-gray-700 disabled:opacity-50"
	    				autocomplete="off"
	    			/>
	    		</div>
			{/if}
        			<div class="flex justify-end gap-2 text-sm font-medium">
	    			<button
	    				type="button"
	    				class="px-3.5 py-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800"
	    				on:click={closeModal}
	    			>
	    				{$i18n.t('Cancel')}
	    			</button>
                
                    <button
	    				type="submit"
	    				class="px-3.5 py-2 rounded-full bg-black text-white dark:bg-white dark:text-black disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
	    			>
	    				{mode === 'load' ? $i18n.t('Load') : $i18n.t('Save')}
	    			</button>
	    		</div>
        </form>
    </div>
    
</Modal>