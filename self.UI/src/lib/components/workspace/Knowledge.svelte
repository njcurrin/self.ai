<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, knowledge } from '$lib/stores';
	import {
		getKnowledgeBases,
		deleteKnowledgeById,
		getKnowledgeBaseList
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import Badge from '../common/Badge.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';
	import Tooltip from '../common/Tooltip.svelte';
	import Dropdown from '../common/Dropdown.svelte';

	let loaded = false;

	let query = '';
	let selectedItem = null;
	let showDeleteConfirm = false;
	let showAddMenu = false;

	let fuse = null;

	let knowledgeBases = [];
	let filteredItems = [];

	$: if (knowledgeBases) {
		fuse = new Fuse(knowledgeBases, {
			keys: ['name', 'description']
		});
	}

	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: knowledgeBases;
	}

	const deleteHandler = async (item) => {
		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(e);
		});

		if (res) {
			knowledgeBases = await getKnowledgeBaseList(localStorage.token);
			knowledge.set(await getKnowledgeBases(localStorage.token));
			toast.success($i18n.t('Knowledge deleted successfully.'));
		}
	};

	onMount(async () => {
		knowledgeBases = await getKnowledgeBaseList(localStorage.token);
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Knowledge')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			deleteHandler(selectedItem);
		}}
	/>

	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
				{$i18n.t('Knowledge')}
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
					>{filteredItems.length}</span
				>
			</div>
		</div>

		<div class=" flex w-full space-x-2">
			<div class="flex flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm py-1 rounded-r-xl outline-none bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Knowledge')}
				/>
			</div>

			<div>
				<Dropdown
					bind:show={showAddMenu}
					align="end"
				>
					<button
						class=" px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center space-x-1"
						aria-label={$i18n.t('Add')}
					>
						<Plus className="size-3.5" />
					</button>

					<div slot="content">
						<DropdownMenu.Content
							class="w-full max-w-56 rounded-xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
							sideOffset={4}
							side="bottom"
							align="end"
							transition={flyAndScale}
						>
							<DropdownMenu.Item
								class="flex gap-2 items-center px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
								on:click={() => {
									goto('/workspace/knowledge/create');
								}}
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
									<path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06v-11a.75.75 0 00-.546-.721A9.006 9.006 0 0015 3a8.963 8.963 0 00-4.25 1.065V16.82zM9.25 4.065A8.963 8.963 0 005 3c-.85 0-1.673.118-2.454.339A.75.75 0 002 4.06v11a.75.75 0 00.954.721A7.506 7.506 0 015 15.5c1.579 0 3.042.487 4.25 1.32V4.065z" />
								</svg>
								<div class="flex items-center">{$i18n.t('Create Knowledge Base')}</div>
							</DropdownMenu.Item>

							<DropdownMenu.Item
								class="flex gap-2 items-center px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
								on:click={() => {
									goto('/workspace/knowledge/dataset/create');
								}}
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
									<path fill-rule="evenodd" d="M10 1c-1.828 0-3.623.149-5.371.435a.75.75 0 00-.629.74v.01c0 2.458.82 4.775 2.293 6.612A10.95 10.95 0 009.25 11.3V17h-2.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-2.5v-5.7a10.95 10.95 0 002.957-2.503A10.969 10.969 0 0016 2.185v-.01a.75.75 0 00-.629-.74A33.118 33.118 0 0010 1zM7.544 7.159A9.47 9.47 0 015.5 2.57c1.466-.17 2.967-.258 4.5-.258s3.034.088 4.5.258a9.47 9.47 0 01-2.044 4.589A9.45 9.45 0 0110 9.465a9.45 9.45 0 01-2.456-2.306z" clip-rule="evenodd" />
								</svg>
								<div class="flex items-center">{$i18n.t('Add Dataset')}</div>
							</DropdownMenu.Item>
						</DropdownMenu.Content>
					</div>
				</Dropdown>
			</div>
		</div>
	</div>

	<div class="mb-5 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-2">
		{#each filteredItems as item}
			<button
				class=" flex space-x-4 cursor-pointer text-left w-full px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-xl"
				on:click={() => {
					if (item?.meta?.document) {
						toast.error(
							$i18n.t(
								'Only collections can be edited, create a new knowledge base to edit/add documents.'
							)
						);
					} else {
						goto(`/workspace/knowledge/${item.id}`);
					}
				}}
			>
				<div class=" w-full">
					<div class="flex items-center justify-between -mt-1">
						{#if item?.meta?.dataset}
							<Badge type="info" content={$i18n.t('Dataset')} />
						{:else if item?.meta?.document}
							<Badge type="muted" content={$i18n.t('Document')} />
						{:else}
							<Badge type="success" content={$i18n.t('Collection')} />
						{/if}

						<div class=" flex self-center -mr-1 translate-y-1">
							<ItemMenu
								on:delete={() => {
									selectedItem = item;
									showDeleteConfirm = true;
								}}
							/>
						</div>
					</div>

					<div class=" self-center flex-1 px-1 mb-1">
						<div class=" font-semibold line-clamp-1 h-fit">{item.name}</div>

						<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1">
							{item.description}
						</div>

						<div class="mt-3 flex justify-between">
							<div class="text-xs text-gray-500">
								<Tooltip
									content={item?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
									{$i18n.t('By {{name}}', {
										name: capitalizeFirstLetter(
											item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
										)
									})}
								</Tooltip>
							</div>
							<div class=" text-xs text-gray-500 line-clamp-1">
								{$i18n.t('Updated')}
								{dayjs(item.updated_at * 1000).fromNow()}
							</div>
						</div>
					</div>
				</div>
			</button>
		{/each}
	</div>

	<div class=" text-gray-500 text-xs mt-1 mb-2">
		ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
