<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getCuratorConfig, updateCuratorConfig } from '$lib/apis/curator';
	import { getLmEvalConfig, updateLmEvalConfig } from '$lib/apis/lm_eval';
	import { getBigcodeEvalConfig, updateBigcodeEvalConfig } from '$lib/apis/bigcode_eval';
	import { getLlamolotlConfig, updateLlamolotlConfig } from '$lib/apis/llamolotl';
	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getModels as _getModels } from '$lib/apis';

	import { models, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from './Connections/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';
	import CuratorConnection from './Connections/CuratorConnection.svelte';
	import LmEvalConnection from './Connections/LmEvalConnection.svelte';
	import BigcodeEvalConnection from './Connections/BigcodeEvalConnection.svelte';
	import LlamolotlConnection from './Connections/LlamolotlConnection.svelte';

	const i18n = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(localStorage.token);
		return models;
	};

	// External
	let CURATOR_BASE_URLS = [''];
	let CURATOR_API_CONFIGS = {};

	let LM_EVAL_BASE_URLS: string[] = [''];
	let BIGCODE_EVAL_BASE_URLS: string[] = [''];

	let LLAMOLOTL_BASE_URLS = [''];
	let LLAMOLOTL_API_CONFIGS = {};

	let OLLAMA_BASE_URLS = [''];
	let OLLAMA_API_CONFIGS = {};

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];
	let OPENAI_API_CONFIGS = {};

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;
	let ENABLE_LLAMOLOTL_API: null | boolean = null;
	let ENABLE_CURATOR_API: null | boolean = null;
	let ENABLE_LM_EVAL_API: null | boolean = null;
	let ENABLE_BIGCODE_EVAL_API: null | boolean = null;

	let pipelineUrls = {};
	let showAddOpenAIConnectionModal = false;
	let showAddOllamaConnectionModal = false;
	let showAddLlamolotlConnectionModal = false;
	let showAddCuratorConnectionModal = false;

	const updateOpenAIHandler = async () => {
		if (ENABLE_OPENAI_API !== null) {
			OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
				(url, urlIdx) => OPENAI_API_BASE_URLS.indexOf(url) === urlIdx && url !== ''
			).map((url) => url.replace(/\/$/, ''));

			// Check if API KEYS length is same than API URLS length
			if (OPENAI_API_KEYS.length !== OPENAI_API_BASE_URLS.length) {
				// if there are more keys than urls, remove the extra keys
				if (OPENAI_API_KEYS.length > OPENAI_API_BASE_URLS.length) {
					OPENAI_API_KEYS = OPENAI_API_KEYS.slice(0, OPENAI_API_BASE_URLS.length);
				}

				// if there are more urls than keys, add empty keys
				if (OPENAI_API_KEYS.length < OPENAI_API_BASE_URLS.length) {
					const diff = OPENAI_API_BASE_URLS.length - OPENAI_API_KEYS.length;
					for (let i = 0; i < diff; i++) {
						OPENAI_API_KEYS.push('');
					}
				}
			}

			const res = await updateOpenAIConfig(localStorage.token, {
				ENABLE_OPENAI_API: ENABLE_OPENAI_API,
				OPENAI_API_BASE_URLS: OPENAI_API_BASE_URLS,
				OPENAI_API_KEYS: OPENAI_API_KEYS,
				OPENAI_API_CONFIGS: OPENAI_API_CONFIGS
			}).catch((error) => {
				toast.error(error);
			});

			if (res) {
				toast.success($i18n.t('OpenAI API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateOllamaHandler = async () => {
		if (ENABLE_OLLAMA_API !== null) {
			// Remove duplicate URLs
			OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter(
				(url, urlIdx) => OLLAMA_BASE_URLS.indexOf(url) === urlIdx && url !== ''
			).map((url) => url.replace(/\/$/, ''));

			console.log(OLLAMA_BASE_URLS);

			if (OLLAMA_BASE_URLS.length === 0) {
				ENABLE_OLLAMA_API = false;
				toast.info($i18n.t('Ollama API disabled'));
			}

			const res = await updateOllamaConfig(localStorage.token, {
				ENABLE_OLLAMA_API: ENABLE_OLLAMA_API,
				OLLAMA_BASE_URLS: OLLAMA_BASE_URLS,
				OLLAMA_API_CONFIGS: OLLAMA_API_CONFIGS
			}).catch((error) => {
				toast.error(error);
			});

			if (res) {
				toast.success($i18n.t('Ollama API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const addOpenAIConnectionHandler = async (connection) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key];
		OPENAI_API_CONFIGS[connection.url] = connection.config;

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[connection.url] = connection.config;

		await updateOllamaHandler();
	};

	const updateLlamolotlHandler = async () => {
		if (ENABLE_LLAMOLOTL_API !== null) {
			// Remove duplicate URLs
			LLAMOLOTL_BASE_URLS = LLAMOLOTL_BASE_URLS.filter(
				(url, urlIdx) => LLAMOLOTL_BASE_URLS.indexOf(url) === urlIdx && url !== ''
			).map((url) => url.replace(/\/$/, ''));

			if (LLAMOLOTL_BASE_URLS.length === 0) {
				ENABLE_LLAMOLOTL_API = false;
				toast.info($i18n.t('Llamolotl API disabled'));
			}

			const res = await updateLlamolotlConfig(localStorage.token, {
				ENABLE_LLAMOLOTL_API: ENABLE_LLAMOLOTL_API,
				LLAMOLOTL_BASE_URLS: LLAMOLOTL_BASE_URLS,
				LLAMOLOTL_API_CONFIGS: LLAMOLOTL_API_CONFIGS
			}).catch((error) => {
				toast.error(error);
			});

			if (res) {
				toast.success($i18n.t('Llamolotl API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const addLlamolotlConnectionHandler = async (connection) => {
		LLAMOLOTL_BASE_URLS = [...LLAMOLOTL_BASE_URLS, connection.url];
		LLAMOLOTL_API_CONFIGS[connection.url] = connection.config;

		await updateLlamolotlHandler();
	};

	const updateCuratorHandler = async () => {
		if (ENABLE_CURATOR_API !== null) {
			// Remove duplicate URLs
			CURATOR_BASE_URLS = CURATOR_BASE_URLS.filter(
				(url, urlIdx) => CURATOR_BASE_URLS.indexOf(url) === urlIdx && url !== ''
			).map((url) => url.replace(/\/$/, ''));

			if (CURATOR_BASE_URLS.length === 0) {
				ENABLE_CURATOR_API = false;
				toast.info($i18n.t('Curator API disabled'));
			}

			const res = await updateCuratorConfig(localStorage.token, {
				ENABLE_CURATOR_API: ENABLE_CURATOR_API,
				CURATOR_BASE_URLS: CURATOR_BASE_URLS,
				CURATOR_API_CONFIGS: CURATOR_API_CONFIGS
			}).catch((error) => {
				toast.error(error);
			});

			if (res) {
				toast.success($i18n.t('Curator API settings updated'));
			}
		}
	};

	const addCuratorConnectionHandler = async (connection) => {
		CURATOR_BASE_URLS = [...CURATOR_BASE_URLS, connection.url];
		CURATOR_API_CONFIGS[connection.url] = connection.config;

		await updateCuratorHandler();
	};

	const updateLmEvalHandler = async () => {
		if (ENABLE_LM_EVAL_API !== null) {
			LM_EVAL_BASE_URLS = LM_EVAL_BASE_URLS.filter((url) => url !== '').map((url) =>
				url.replace(/\/$/, '')
			);
			await updateLmEvalConfig(localStorage.token, {
				ENABLE_LM_EVAL_API: ENABLE_LM_EVAL_API,
				LM_EVAL_BASE_URLS
			}).catch(() => {});
		}
	};

	const updateBigcodeEvalHandler = async () => {
		if (ENABLE_BIGCODE_EVAL_API !== null) {
			BIGCODE_EVAL_BASE_URLS = BIGCODE_EVAL_BASE_URLS.filter((url) => url !== '').map((url) =>
				url.replace(/\/$/, '')
			);
			await updateBigcodeEvalConfig(localStorage.token, {
				ENABLE_BIGCODE_EVAL_API: ENABLE_BIGCODE_EVAL_API,
				BIGCODE_EVAL_BASE_URLS
			}).catch(() => {});
		}
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			let ollamaConfig = {};
			let openaiConfig = {};
			let llamolotlConfig = {};
			let curatorConfig = {};
			let lmEvalConfig: any = {};
			let bigcodeEvalConfig: any = {};

			await Promise.all([
				(async () => {
					ollamaConfig = await getOllamaConfig(localStorage.token);
				})(),
				(async () => {
					openaiConfig = await getOpenAIConfig(localStorage.token);
				})(),
				(async () => {
					llamolotlConfig = await getLlamolotlConfig(localStorage.token);
				})(),
				(async () => {
					curatorConfig = await getCuratorConfig(localStorage.token);
				})(),
				(async () => {
					lmEvalConfig = await getLmEvalConfig(localStorage.token).catch(() => ({}));
				})(),
				(async () => {
					bigcodeEvalConfig = await getBigcodeEvalConfig(localStorage.token).catch(() => ({}));
				})()
			]);

			ENABLE_OPENAI_API = openaiConfig.ENABLE_OPENAI_API;
			ENABLE_OLLAMA_API = ollamaConfig.ENABLE_OLLAMA_API;
			ENABLE_LLAMOLOTL_API = llamolotlConfig.ENABLE_LLAMOLOTL_API;
			ENABLE_CURATOR_API = curatorConfig.ENABLE_CURATOR_API;
			ENABLE_LM_EVAL_API = lmEvalConfig.ENABLE_LM_EVAL_API ?? false;
			ENABLE_BIGCODE_EVAL_API = bigcodeEvalConfig.ENABLE_BIGCODE_EVAL_API ?? false;

			OPENAI_API_BASE_URLS = openaiConfig.OPENAI_API_BASE_URLS;
			OPENAI_API_KEYS = openaiConfig.OPENAI_API_KEYS;
			OPENAI_API_CONFIGS = openaiConfig.OPENAI_API_CONFIGS;

			OLLAMA_BASE_URLS = ollamaConfig.OLLAMA_BASE_URLS;
			OLLAMA_API_CONFIGS = ollamaConfig.OLLAMA_API_CONFIGS;

			LLAMOLOTL_BASE_URLS = llamolotlConfig.LLAMOLOTL_BASE_URLS;
			LLAMOLOTL_API_CONFIGS = llamolotlConfig.LLAMOLOTL_API_CONFIGS;

			CURATOR_BASE_URLS = curatorConfig.CURATOR_BASE_URLS;
			CURATOR_API_CONFIGS = curatorConfig.CURATOR_API_CONFIGS;

			LM_EVAL_BASE_URLS = lmEvalConfig.LM_EVAL_BASE_URLS ?? [''];
			BIGCODE_EVAL_BASE_URLS = bigcodeEvalConfig.BIGCODE_EVAL_BASE_URLS ?? [''];

			if (ENABLE_OPENAI_API) {
				for (const url of OPENAI_API_BASE_URLS) {
					if (!OPENAI_API_CONFIGS[url]) {
						OPENAI_API_CONFIGS[url] = {};
					}
				}

				OPENAI_API_BASE_URLS.forEach(async (url, idx) => {
					OPENAI_API_CONFIGS[url] = OPENAI_API_CONFIGS[url] || {};
					if (!(OPENAI_API_CONFIGS[url]?.enable ?? true)) {
						return;
					}
					const res = await getOpenAIModels(localStorage.token, idx);
					if (res.pipelines) {
						pipelineUrls[url] = true;
					}
				});
			}

			if (ENABLE_OLLAMA_API) {
				for (const url of OLLAMA_BASE_URLS) {
					if (!OLLAMA_API_CONFIGS[url]) {
						OLLAMA_API_CONFIGS[url] = {};
					}
				}
			}

			if (ENABLE_LLAMOLOTL_API) {
				for (const url of LLAMOLOTL_BASE_URLS) {
					if (!LLAMOLOTL_API_CONFIGS[url]) {
						LLAMOLOTL_API_CONFIGS[url] = {};
					}
				}
			}

			if (ENABLE_CURATOR_API) {
				for (const url of CURATOR_BASE_URLS) {
					if (!CURATOR_API_CONFIGS[url]) {
						CURATOR_API_CONFIGS[url] = {};
					}
				}
			}
		}
	});
</script>

<AddConnectionModal
	bind:show={showAddOpenAIConnectionModal}
	onSubmit={addOpenAIConnectionHandler}
/>

<AddConnectionModal
	ollama
	bind:show={showAddOllamaConnectionModal}
	onSubmit={addOllamaConnectionHandler}
/>

<AddConnectionModal
	llamolotl
	bind:show={showAddLlamolotlConnectionModal}
	onSubmit={addLlamolotlConnectionHandler}
/>

<AddConnectionModal
	curator
	bind:show={showAddCuratorConnectionModal}
	onSubmit={addCuratorConnectionHandler}
/>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateOpenAIHandler();
		updateOllamaHandler();
		updateLlamolotlHandler();
		updateCuratorHandler();
		updateLmEvalHandler();
		updateBigcodeEvalHandler();

		dispatch('save');
	}}
>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && ENABLE_LLAMOLOTL_API !== null && ENABLE_CURATOR_API !== null && ENABLE_LM_EVAL_API !== null && ENABLE_BIGCODE_EVAL_API !== null}
			<div class="my-2">
				<div class="mt-2 space-y-2 pr-1.5">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{$i18n.t('OpenAI API')}</div>

						<div class="flex items-center">
							<div class="">
								<Switch
									bind:state={ENABLE_OPENAI_API}
									on:change={async () => {
										updateOpenAIHandler();
									}}
								/>
							</div>
						</div>
					</div>

					{#if ENABLE_OPENAI_API}
						<hr class=" border-gray-50 dark:border-gray-850" />

						<div class="">
							<div class="flex justify-between items-center">
								<div class="font-medium">{$i18n.t('Manage OpenAI API Connections')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										class="px-1"
										on:click={() => {
											showAddOpenAIConnectionModal = true;
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div class="flex flex-col gap-1.5 mt-1.5">
								{#each OPENAI_API_BASE_URLS as url, idx}
									<OpenAIConnection
										pipeline={pipelineUrls[url] ? true : false}
										bind:url
										bind:key={OPENAI_API_KEYS[idx]}
										bind:config={OPENAI_API_CONFIGS[url]}
										onSubmit={() => {
											updateOpenAIHandler();
										}}
										onDelete={() => {
											OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
												(url, urlIdx) => idx !== urlIdx
											);
											OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);
										}}
									/>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<hr class=" border-gray-50 dark:border-gray-850" />

			<div class="pr-1.5 my-2">
				<div class="flex justify-between items-center text-sm mb-2">
					<div class="  font-medium">{$i18n.t('Ollama API')}</div>

					<div class="mt-1">
						<Switch
							bind:state={ENABLE_OLLAMA_API}
							on:change={async () => {
								updateOllamaHandler();
							}}
						/>
					</div>
				</div>

				{#if ENABLE_OLLAMA_API}
					<hr class=" border-gray-50 dark:border-gray-850 my-2" />

					<div class="">
						<div class="flex justify-between items-center">
							<div class="font-medium">{$i18n.t('Manage Ollama API Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									on:click={() => {
										showAddOllamaConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex w-full gap-1.5">
							<div class="flex-1 flex flex-col gap-1.5 mt-1.5">
								{#each OLLAMA_BASE_URLS as url, idx}
									<OllamaConnection
										bind:url
										bind:config={OLLAMA_API_CONFIGS[url]}
										{idx}
										onSubmit={() => {
											updateOllamaHandler();
										}}
										onDelete={() => {
											OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);
										}}
									/>
								{/each}
							</div>
						</div>

						<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Trouble accessing Ollama?')}
							<a
								class=" text-gray-300 font-medium underline"
								href="https://github.com/open-webui/open-webui#troubleshooting"
								target="_blank"
							>
								{$i18n.t('Click here for help.')}
							</a>
						</div>
					</div>
				{/if}
			</div>

			<hr class=" border-gray-50 dark:border-gray-850" />

			<div class="pr-1.5 my-2">
				<div class="flex justify-between items-center text-sm mb-2">
					<div class="  font-medium">{$i18n.t('self.llamolotl API')}</div>

					<div class="mt-1">
						<Switch
							bind:state={ENABLE_LLAMOLOTL_API}
							on:change={async () => {
								updateLlamolotlHandler();
							}}
						/>
					</div>
				</div>

				{#if ENABLE_LLAMOLOTL_API}
					<hr class=" border-gray-50 dark:border-gray-850 my-2" />

					<div class="">
						<div class="flex justify-between items-center">
							<div class="font-medium">{$i18n.t('Manage self.llamolotl Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									on:click={() => {
										showAddLlamolotlConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex w-full gap-1.5">
							<div class="flex-1 flex flex-col gap-1.5 mt-1.5">
								{#each LLAMOLOTL_BASE_URLS as url, idx}
									<LlamolotlConnection
										bind:url
										bind:config={LLAMOLOTL_API_CONFIGS[url]}
										{idx}
										onSubmit={() => {
											updateLlamolotlHandler();
										}}
										onDelete={() => {
											LLAMOLOTL_BASE_URLS = LLAMOLOTL_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);
										}}
									/>
								{/each}
							</div>
						</div>
					</div>
				{/if}
			</div>

			<hr class=" border-gray-50 dark:border-gray-850" />

			<div class="pr-1.5 my-2">
				<div class="flex justify-between items-center text-sm mb-2">
					<div class="  font-medium">{$i18n.t('self.curator API')}</div>

					<div class="mt-1">
						<Switch
							bind:state={ENABLE_CURATOR_API}
							on:change={async () => {
								updateCuratorHandler();
							}}
						/>
					</div>
				</div>

				{#if ENABLE_CURATOR_API}
					<hr class=" border-gray-50 dark:border-gray-850 my-2" />

					<div class="">
						<div class="flex justify-between items-center">
							<div class="font-medium">{$i18n.t('Manage self.curator Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									on:click={() => {
										showAddCuratorConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex w-full gap-1.5">
							<div class="flex-1 flex flex-col gap-1.5 mt-1.5">
								{#each CURATOR_BASE_URLS as url, idx}
									<CuratorConnection
										bind:url
										bind:config={CURATOR_API_CONFIGS[url]}
										{idx}
										onSubmit={() => {
											updateCuratorHandler();
										}}
										onDelete={() => {
											CURATOR_BASE_URLS = CURATOR_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);
										}}
									/>
								{/each}
							</div>
						</div>
					</div>
				{/if}
			</div>
			{#if ENABLE_LM_EVAL_API || LM_EVAL_BASE_URLS.some((u) => u !== '')}
				<hr class=" border-gray-50 dark:border-gray-850" />

				<div class="pr-1.5 my-2">
					<div class="flex justify-between items-center text-sm mb-2">
						<div class="font-medium">{$i18n.t('self.lm-eval API')}</div>
						<div class="mt-1">
							<Switch
								bind:state={ENABLE_LM_EVAL_API}
								on:change={async () => {
									updateLmEvalHandler();
								}}
							/>
						</div>
					</div>

					{#if ENABLE_LM_EVAL_API}
						<hr class=" border-gray-50 dark:border-gray-850 my-2" />
						<div class="">
							<div class="flex justify-between items-center">
								<div class="font-medium">{$i18n.t('Manage lm-eval Connections')}</div>
								<Tooltip content={$i18n.t('Add Connection')}>
									<button
										class="px-1"
										on:click={() => {
											LM_EVAL_BASE_URLS = [...LM_EVAL_BASE_URLS, ''];
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>
							<div class="flex flex-col gap-1.5 mt-1.5">
								{#each LM_EVAL_BASE_URLS as url, idx}
									<LmEvalConnection
										bind:url
										{idx}
										onSubmit={() => updateLmEvalHandler()}
										onDelete={() => {
											LM_EVAL_BASE_URLS = LM_EVAL_BASE_URLS.filter((_, i) => i !== idx);
											updateLmEvalHandler();
										}}
									/>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}

			{#if ENABLE_BIGCODE_EVAL_API || BIGCODE_EVAL_BASE_URLS.some((u) => u !== '')}
				<hr class=" border-gray-50 dark:border-gray-850" />

				<div class="pr-1.5 my-2">
					<div class="flex justify-between items-center text-sm mb-2">
						<div class="font-medium">{$i18n.t('self.bigcode-eval API')}</div>
						<div class="mt-1">
							<Switch
								bind:state={ENABLE_BIGCODE_EVAL_API}
								on:change={async () => {
									updateBigcodeEvalHandler();
								}}
							/>
						</div>
					</div>

					{#if ENABLE_BIGCODE_EVAL_API}
						<hr class=" border-gray-50 dark:border-gray-850 my-2" />
						<div class="">
							<div class="flex justify-between items-center">
								<div class="font-medium">{$i18n.t('Manage bigcode-eval Connections')}</div>
								<Tooltip content={$i18n.t('Add Connection')}>
									<button
										class="px-1"
										on:click={() => {
											BIGCODE_EVAL_BASE_URLS = [...BIGCODE_EVAL_BASE_URLS, ''];
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>
							<div class="flex flex-col gap-1.5 mt-1.5">
								{#each BIGCODE_EVAL_BASE_URLS as url, idx}
									<BigcodeEvalConnection
										bind:url
										{idx}
										onSubmit={() => updateBigcodeEvalHandler()}
										onDelete={() => {
											BIGCODE_EVAL_BASE_URLS = BIGCODE_EVAL_BASE_URLS.filter((_, i) => i !== idx);
											updateBigcodeEvalHandler();
										}}
									/>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
