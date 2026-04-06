<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, models, MODEL_DOWNLOAD_POOL, user, config } from '$lib/stores';
	import { splitStream } from '$lib/utils';

	import {
		pullLlamolotlModel,
		cancelLlamolotlModelPull,
		deleteLlamolotlModel,
		getAvailableLlamolotlModels,
		registerLlamolotlModel,
		inspectLlamolotlModel
	} from '$lib/apis/llamolotl';
	import type { ModelInspectResult } from '$lib/apis/llamolotl';
	import { getModels } from '$lib/apis';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ModelDeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let show = false;
	export let urlIdx: number | null = null;

	let showModelDeleteConfirm = false;
	let loading = true;

	let availableModels: { name: string; size: number; modified: number; registered?: boolean; shards?: number; hf_repo?: string; quant?: string; trainable?: boolean; source_type?: string; pulled_at?: string; bake_info?: { base_model: string; adapters: { path: string; weight: number }[]; outtype: string; quant_type?: string; baked_at: string } }[] = [];

	const MAX_PARALLEL_DOWNLOADS = 3;

	let modelTransferring = false;
	let modelTag = '';
	let selectedFilename: string | null = null;
	let availableFiles: string[] = [];
	let showFileSelector = false;

	let inspecting = false;
	let showDownloadConfirm = false;
	let downloadInfo: ModelInspectResult | null = null;

	let deleteModelName = '';

	const pullModelHandler = async () => {
		const sanitizedModelTag = modelTag.trim();
		if (!sanitizedModelTag) return;

		if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag]) {
			toast.error(
				$i18n.t(`Model '{{modelTag}}' is already in queue for downloading.`, {
					modelTag: sanitizedModelTag
				})
			);
			return;
		}
		if (Object.keys($MODEL_DOWNLOAD_POOL).length >= MAX_PARALLEL_DOWNLOADS) {
			toast.error(
				$i18n.t('Maximum of 3 models can be downloaded simultaneously. Please try again later.')
			);
			return;
		}

		// If we haven't confirmed yet, inspect first and show confirmation
		if (!showDownloadConfirm) {
			inspecting = true;
			try {
				downloadInfo = await inspectLlamolotlModel(localStorage.token, sanitizedModelTag, urlIdx);
				showDownloadConfirm = true;
			} catch (err: any) {
				toast.error(err?.detail ?? err?.message ?? String(err));
			} finally {
				inspecting = false;
			}
			return;
		}

		// Confirmed — proceed with actual download
		showDownloadConfirm = false;
		downloadInfo = null;

		const [res, controller] = await pullLlamolotlModel(
			localStorage.token,
			sanitizedModelTag,
			selectedFilename,
			urlIdx
		).catch((error) => {
			toast.error(error);
			return [null, null];
		});

		if (res) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			// Show indeterminate progress immediately while backend prepares (model_info call etc.)
			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL,
				[sanitizedModelTag]: {
					abortController: controller,
					reader,
					done: false,
					pullProgress: -1,
					digest: 'Starting...',
					downloadedBytes: 0
				}
			});

			// Check first message for file selection
			const { value: firstValue, done: firstDone } = await reader.read();
			if (firstDone) {
				delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];
				MODEL_DOWNLOAD_POOL.set({ ...$MODEL_DOWNLOAD_POOL });
				return;
			}

			let lines = firstValue.split('\n');
			for (const line of lines) {
				if (line !== '') {
					let data = JSON.parse(line);

					if (data.error) {
						delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];
						MODEL_DOWNLOAD_POOL.set({ ...$MODEL_DOWNLOAD_POOL });
						toast.error(data.error);
						return;
					}

					if (data.status === 'select_file') {
						delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];
						MODEL_DOWNLOAD_POOL.set({ ...$MODEL_DOWNLOAD_POOL });
						availableFiles = data.files;
						showFileSelector = true;
						return;
					}
				}
			}

			while (true) {
				try {
					const { value, done } = await reader.read();
					if (done) break;

					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line);
							console.log(data);
							if (data.error) {
								throw data.error;
							}
							if (data.detail) {
								throw data.detail;
							}

							if (data.status) {
								if (data.digest) {
									let downloadProgress = 0;
									if (data.status === 'converting') {
										// Conversion phase — always indeterminate
										downloadProgress = -1;
									} else if (data.total > 0 && data.completed) {
										downloadProgress =
											Math.round((data.completed / data.total) * 1000) / 10;
									} else if (data.total > 0 && !data.completed) {
										downloadProgress = 0;
									} else if (data.total === 0) {
										// Unknown total size — show indeterminate
										downloadProgress = data.completed > 0 ? -1 : 0;
									} else {
										downloadProgress = 100;
									}

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											pullProgress: downloadProgress,
											digest: data.digest,
											downloadedBytes: data.completed || 0,
											...(data.log && { statusText: data.log })
										}
									});
								} else if (data.status === 'success') {
									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											done: true
										}
									});
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
					if (typeof error !== 'string') {
						error = error.message;
					}
					toast.error(error);
				}
			}

			if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag]?.done) {
				toast.success(
					$i18n.t(`Model '{{modelName}}' has been successfully downloaded.`, {
						modelName: sanitizedModelTag
					})
				);

				models.set(await getModels(localStorage.token));
				await init();
			} else {
				toast.error($i18n.t('Download canceled'));
			}

			delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
		}

		modelTag = '';
		selectedFilename = null;
		availableFiles = [];
		showFileSelector = false;
		modelTransferring = false;
	};

	const confirmAndPull = async () => {
		showDownloadConfirm = true; // flag so pullModelHandler skips inspect
		await pullModelHandler();
	};

	const cancelDownloadInspect = () => {
		showDownloadConfirm = false;
		downloadInfo = null;
		selectedFilename = null;
	};

	const selectFileAndPull = async (filename: string) => {
		selectedFilename = filename;
		showFileSelector = false;
		await pullModelHandler();
	};

	const cancelModelPullHandler = async (model: string) => {
		const { reader, abortController } = $MODEL_DOWNLOAD_POOL[model];
		if (abortController) {
			abortController.abort();
		}
		if (reader) {
			await reader.cancel();
			delete $MODEL_DOWNLOAD_POOL[model];
			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});

			try {
				await cancelLlamolotlModelPull(localStorage.token, model, null, urlIdx);
			} catch (e) {
				console.log('Cancel request failed:', e);
			}

			toast.success(`${model} download has been canceled`);
		}
	};

	const registerModelHandler = async (modelName: string) => {
		const res = await registerLlamolotlModel(localStorage.token, modelName, urlIdx).catch(
			(error) => {
				toast.error(error);
				return null;
			}
		);

		if (res) {
			toast.success(
				$i18n.t(`Model '{{modelName}}' has been registered.`, { modelName })
			);
			models.set(await getModels(localStorage.token));
			await init();
		}
	};

	const deleteModelHandler = async () => {
		const res = await deleteLlamolotlModel(localStorage.token, deleteModelName, urlIdx).catch(
			(error) => {
				toast.error(error);
			}
		);

		if (res) {
			toast.success($i18n.t(`Deleted {{deleteModelTag}}`, { deleteModelTag: deleteModelName }));
		}

		deleteModelName = '';
		models.set(await getModels(localStorage.token));
		await init();
	};

	const init = async () => {
		loading = true;
		try {
			availableModels = await getAvailableLlamolotlModels(localStorage.token, urlIdx);
		} catch (e) {
			console.log('Failed to load available models:', e);
			availableModels = [];
		}
		loading = false;
	};

	$: if (show) {
		init();
	}
</script>

<ModelDeleteConfirmDialog
	bind:show={showModelDeleteConfirm}
	on:confirm={() => {
		deleteModelHandler();
	}}
/>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div
				class="flex w-full justify-between items-center text-lg font-medium self-center font-primary"
			>
				<div class=" flex-shrink-0">
					{$i18n.t('Manage Llamolotl')}
				</div>
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			{#if !loading}
				<div class=" flex flex-col w-full">
					<div>
						<div class="space-y-2">
							<div>
								<div class=" mb-2 text-sm font-medium">
									{$i18n.t('Pull a model from HuggingFace')}
								</div>
								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
											placeholder={$i18n.t('Enter HuggingFace repo (e.g. {{modelTag}})', {
												modelTag: 'bartowski/Llama-3.2-1B-Instruct-GGUF'
											})}
											bind:value={modelTag}
										/>
									</div>
									<button
										class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
										on:click={() => {
											pullModelHandler();
										}}
										disabled={modelTransferring}
									>
										{#if modelTransferring}
											<div class="self-center">
												<svg
													class=" w-4 h-4"
													viewBox="0 0 24 24"
													fill="currentColor"
													xmlns="http://www.w3.org/2000/svg"
												>
													<style>
														.spinner_ajPY {
															transform-origin: center;
															animation: spinner_AtaB 0.75s infinite linear;
														}

														@keyframes spinner_AtaB {
															100% {
																transform: rotate(360deg);
															}
														}
													</style>
													<path
														d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
														opacity=".25"
													/>
													<path
														d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
														class="spinner_ajPY"
													/>
												</svg>
											</div>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
											>
												<path
													d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
												/>
												<path
													d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
												/>
											</svg>
										{/if}
									</button>
								</div>

								<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('To access the GGUF models available for downloading,')}
									<a
										class=" text-gray-500 dark:text-gray-300 font-medium underline"
										href="https://huggingface.co/models?search=gguf"
										target="_blank">{$i18n.t('click here.')}</a
									>
								</div>

								{#if inspecting}
								<div class="mt-2 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
									<Spinner className="w-4 h-4" />
									{$i18n.t('Checking download size...')}
								</div>
							{/if}

							{#if showDownloadConfirm && downloadInfo}
								{@const singleFile = downloadInfo.files.length === 1}
								<div class="mt-2 rounded-lg border border-gray-200 dark:border-gray-700 p-3 space-y-2">
									{#if singleFile}
										<div class="flex justify-between text-sm dark:text-gray-200">
											<span class="truncate mr-2 text-gray-600 dark:text-gray-400">{downloadInfo.files[0].name}</span>
											<span class="flex-shrink-0 font-semibold">
												{downloadInfo.files[0].size > 0 ? (downloadInfo.files[0].size / 1024 ** 3).toFixed(2) + ' GB' : '?'}
											</span>
										</div>
									{:else if downloadInfo.type === 'gguf'}
										<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Select a file to download:')}</div>
										<div class="max-h-48 overflow-y-auto space-y-0.5">
											{#each downloadInfo.files as file}
												<button
													class="w-full flex justify-between items-center text-xs py-1.5 px-2 rounded transition text-left {selectedFilename === file.name ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium' : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400'}"
													on:click={() => { selectedFilename = file.name; }}
												>
													<span class="truncate mr-2">{file.name}</span>
													<span class="flex-shrink-0">
														{file.size > 0 ? (file.size / 1024 ** 3).toFixed(2) + ' GB' : '?'}
													</span>
												</button>
											{/each}
										</div>
									{:else}
										<details>
											<summary class="cursor-pointer text-sm dark:text-gray-200 flex justify-between">
												<span>{downloadInfo.files.length} files</span>
												<span class="font-semibold">
													{downloadInfo.total_size > 0 ? (downloadInfo.total_size / 1024 ** 3).toFixed(2) + ' GB' : '?'}
												</span>
											</summary>
											<div class="mt-1.5 max-h-36 overflow-y-auto space-y-0.5">
												{#each downloadInfo.files as file}
													<div class="flex justify-between text-xs py-0.5">
														<span class="truncate mr-2 text-gray-500 dark:text-gray-400">{file.name}</span>
														<span class="flex-shrink-0 text-gray-600 dark:text-gray-300">
															{file.size > 0 ? (file.size / 1024 ** 3).toFixed(2) + ' GB' : '?'}
														</span>
													</div>
												{/each}
											</div>
										</details>
									{/if}
									<div class="flex justify-end gap-2 pt-1 border-t border-gray-200 dark:border-gray-700">
										<button
											class="px-3 py-1 text-xs rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200 transition"
											on:click={cancelDownloadInspect}
										>
											{$i18n.t('Cancel')}
										</button>
										<button
											class="px-3 py-1 text-xs rounded-lg bg-blue-500 hover:bg-blue-600 text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
											on:click={confirmAndPull}
											disabled={!singleFile && downloadInfo.type === 'gguf' && !selectedFilename}
										>
											{$i18n.t('Download')}
										</button>
									</div>
								</div>
							{/if}

							{#if showFileSelector && availableFiles.length > 0}
									<div class="mt-2">
										<div class="mb-2 text-sm font-medium">
											{$i18n.t('Select a GGUF file to download')}
										</div>
										<div class="flex flex-col gap-1 max-h-48 overflow-y-auto">
											{#each availableFiles as file}
												<button
													class="w-full text-left rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
													on:click={() => {
														selectFileAndPull(file);
													}}
												>
													{file}
												</button>
											{/each}
										</div>
									</div>
								{/if}

								{#if Object.keys($MODEL_DOWNLOAD_POOL).length > 0}
									{#each Object.keys($MODEL_DOWNLOAD_POOL) as model}
										{#if 'pullProgress' in $MODEL_DOWNLOAD_POOL[model]}
											<div class="flex flex-col">
												<div class="font-medium mb-1">{model}</div>
												<div class="">
													<div class="flex flex-row justify-between space-x-4 pr-2">
														<div class=" flex-1">
															{#if ($MODEL_DOWNLOAD_POOL[model].pullProgress ?? 0) === -1}
																<div
																	class="dark:bg-gray-600 bg-gray-500 text-xs font-medium text-gray-100 text-center p-0.5 leading-none rounded-full animate-pulse"
																	style="width: 100%"
																>
																	{#if $MODEL_DOWNLOAD_POOL[model].statusText}
																		{$MODEL_DOWNLOAD_POOL[model].statusText.slice(0, 40)}
																	{:else if $MODEL_DOWNLOAD_POOL[model].downloadedBytes}
																		{($MODEL_DOWNLOAD_POOL[model].downloadedBytes / 1024 / 1024).toFixed(0)} MB
																	{:else}
																		downloading...
																	{/if}
																</div>
															{:else}
																<div
																	class="dark:bg-gray-600 bg-gray-500 text-xs font-medium text-gray-100 text-center p-0.5 leading-none rounded-full"
																	style="width: {Math.max(
																		15,
																		$MODEL_DOWNLOAD_POOL[model].pullProgress ?? 0
																	)}%"
																>
																	{$MODEL_DOWNLOAD_POOL[model].pullProgress ?? 0}%
																</div>
															{/if}
														</div>

														<Tooltip content={$i18n.t('Cancel')}>
															<button
																class="text-gray-800 dark:text-gray-100"
																on:click={() => {
																	cancelModelPullHandler(model);
																}}
															>
																<svg
																	class="w-4 h-4 text-gray-800 dark:text-white"
																	aria-hidden="true"
																	xmlns="http://www.w3.org/2000/svg"
																	width="24"
																	height="24"
																	fill="currentColor"
																	viewBox="0 0 24 24"
																>
																	<path
																		stroke="currentColor"
																		stroke-linecap="round"
																		stroke-linejoin="round"
																		stroke-width="2"
																		d="M6 18 17.94 6M18 18 6.06 6"
																	/>
																</svg>
															</button>
														</Tooltip>
													</div>
													{#if 'digest' in $MODEL_DOWNLOAD_POOL[model]}
														<div
															class="mt-1 text-xs dark:text-gray-500"
															style="font-size: 0.5rem;"
														>
															{$MODEL_DOWNLOAD_POOL[model].digest}
														</div>
													{/if}
												</div>
											</div>
										{/if}
									{/each}
								{/if}
							</div>

							{#if availableModels.some((m) => !m.registered)}
								<div>
									<div class=" mb-2 text-sm font-medium">
										{$i18n.t('Unregistered models')}
									</div>
									<div class="text-xs text-gray-400 dark:text-gray-500 mb-2">
										{$i18n.t('These models are in subdirectories and not visible to llama-server. Register them to make them available for inference.')}
									</div>
									<div class="flex flex-col gap-1 max-h-36 overflow-y-auto">
										{#each availableModels.filter((m) => !m.registered) as model}
											<div
												class="flex items-center justify-between rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850"
											>
												<div class="flex-1 truncate mr-2">
													<div class="flex items-center gap-1.5">
														{model.name}
														{#if model.quant}
															<span class="px-1.5 py-0.5 text-xs font-mono rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">{model.quant}</span>
														{/if}
														{#if model.trainable}
															<span class="px-1.5 py-0.5 text-xs rounded bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">trainable</span>
														{/if}
														{#if model.source_type === 'baked'}
															<span class="px-1.5 py-0.5 text-xs rounded bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300">baked</span>
														{/if}
													</div>
													<span class="text-xs text-gray-400">
														({(model.size / 1024 ** 3).toFixed(1)} GB{model.shards ? `, ${model.shards} shards` : ''})
														{#if model.hf_repo}
															&middot; {model.hf_repo}
														{/if}
													</span>
													{#if model.bake_info}
														<div class="text-xs text-gray-400 mt-0.5">
															Base: {model.bake_info.base_model}
															{#if model.bake_info.adapters.length > 0}
																&middot; {model.bake_info.adapters.length} LoRA{model.bake_info.adapters.length > 1 ? 's' : ''} merged
															{/if}
														</div>
													{/if}
												</div>
												<Tooltip content={$i18n.t('Register')}>
													<button
														class="px-2 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
														on:click={() => {
															registerModelHandler(model.name);
														}}
													>
														{$i18n.t('Register')}
													</button>
												</Tooltip>
											</div>
										{/each}
									</div>
								</div>
							{/if}

							<div>
								<div class=" mb-2 text-sm font-medium">{$i18n.t('Delete a model')}</div>
								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<select
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
											bind:value={deleteModelName}
											placeholder={$i18n.t('Select a model')}
										>
											{#if !deleteModelName}
												<option value="" disabled selected
													>{$i18n.t('Select a model')}</option
												>
											{/if}
											{#each availableModels as model}
												<option value={model.name} class="bg-gray-50 dark:bg-gray-700"
													>{model.name +
														(model.quant ? ` [${model.quant}]` : '') +
														' (' +
														(model.size / 1024 ** 3).toFixed(1) +
														' GB)' +
														(model.hf_repo ? ` — ${model.hf_repo}` : '') +
														(model.source_type === 'baked' ? ' [baked]' : '')}</option
												>
											{/each}
										</select>
									</div>
									<button
										class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
										on:click={() => {
											showModelDeleteConfirm = true;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			{:else}
				<Spinner />
			{/if}
		</div>
	</div>
</Modal>
