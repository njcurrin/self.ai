<script lang="ts">
	import Fuse from 'fuse.js';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, models, prompts } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { getLlamolotlTrainingConfigs, getLlamolotlTrainingConfig, getLlamolotlTrainingStatus, getAvailableLlamolotlModels, type TrainingConfigSummary } from '$lib/apis/llamolotl';
	import {
		getCourses,
		createCourse,
		updateCourse,
		deleteCourse,
		createJob,
		type TrainingCourse,
		type TrainingCourseForm
	} from '$lib/apis/training';

	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	const getToken = () => localStorage.getItem('token') ?? '';

	let loaded = false;
	let submitting = false;
	let saving = false;

	let query = '';
	let showForm = false;
	let editingId: string | null = null;

	let courses: TrainingCourse[] = [];
	let fuse: Fuse<TrainingCourse> | null = null;

	let knowledgeBases: any[] = [];
	let availableConfigs: TrainingConfigSummary[] = [];

	// ── Job submission modal ─────────────────────────────────────────────
	let showJobModal = false;
	let jobCourseId = '';
	let jobModelId = '';
	let modelSearch = '';
	let showModelDropdown = false;
	let trainableModels: { value: string; label: string }[] = [];

	// ── Form state ───────────────────────────────────────────────────────
	let formName = '';
	let formDescription = '';
	let formAccess: 'public' | 'private' = 'private';
	let formBaseConfig = '';
	let formKnowledgeIds: string[] = [];
	let formDatasetIds: string[] = [];
	let formPromptIds: string[] = [];
	let showAdvanced = false;
	let loadingConfig = false;

	type AdvancedParams = {
		num_epochs: number;
		micro_batch_size: number;
		gradient_accumulation_steps: number;
		learning_rate: number;
		lr_scheduler: string;
		optimizer: string;
		warmup_ratio: number;
		weight_decay: number;
		sequence_len: number;
		val_set_size: number;
		lora_r: number;
		lora_alpha: number;
		lora_dropout: number;
		adapter: string;
		load_in_8bit: boolean;
		load_in_4bit: boolean;
		sample_packing: boolean;
		gradient_checkpointing: boolean;
		flash_attention: boolean;
		saves_per_epoch: number;
		evals_per_epoch: number;
		bf16: string;
	};

	const defaultAdvanced: AdvancedParams = {
		num_epochs: 4,
		micro_batch_size: 2,
		gradient_accumulation_steps: 4,
		learning_rate: 0.0002,
		lr_scheduler: 'cosine',
		optimizer: 'adamw_bnb_8bit',
		warmup_ratio: 0.1,
		weight_decay: 0.0,
		sequence_len: 4096,
		val_set_size: 0.05,
		lora_r: 32,
		lora_alpha: 16,
		lora_dropout: 0.05,
		adapter: 'lora',
		load_in_8bit: true,
		load_in_4bit: false,
		sample_packing: false,
		gradient_checkpointing: true,
		flash_attention: true,
		saves_per_epoch: 1,
		evals_per_epoch: 4,
		bf16: 'auto'
	};

	let formAdvanced: AdvancedParams = { ...defaultAdvanced };

	// ── Reactivity ───────────────────────────────────────────────────────
	$: fuse = new Fuse(courses, { keys: ['name', 'description'] });

	$: filteredCourses = query && fuse
		? fuse.search(query).map((r) => r.item)
		: courses;

	$: filteredTrainableModels = modelSearch
		? trainableModels.filter(
				(m) =>
					m.label.toLowerCase().includes(modelSearch.toLowerCase()) ||
					m.value.toLowerCase().includes(modelSearch.toLowerCase())
		  )
		: trainableModels;

	$: knowledgeItems = knowledgeBases.filter((k: any) => !k?.meta?.dataset);
	$: datasetItems = knowledgeBases.filter((k: any) => k?.meta?.dataset);

	// ── Config param loading ─────────────────────────────────────────────
	const parseYamlValue = (content: string, key: string) => {
		const m = content.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
		return m ? m[1].trim() : undefined;
	};

	const loadConfigParams = async (configPath: string) => {
		if (!configPath) { formAdvanced = { ...defaultAdvanced }; return; }
		loadingConfig = true;
		try {
			const configName = configPath.replace(/\.(ya?ml)$/, '').split('/').pop() ?? configPath;
			const detail = await getLlamolotlTrainingConfig(getToken(), configName);
			if (detail?.content) {
				const c = detail.content;
				const num = (k: string) => { const v = parseYamlValue(c, k); return v !== undefined ? parseFloat(v) : null; };
				const bool = (k: string, fb: boolean) => { const v = parseYamlValue(c, k); return v !== undefined ? v === 'true' : fb; };
				const str = (k: string, fb: string) => parseYamlValue(c, k) ?? fb;
				formAdvanced = {
					num_epochs: num('num_epochs') ?? defaultAdvanced.num_epochs,
					micro_batch_size: num('micro_batch_size') ?? defaultAdvanced.micro_batch_size,
					gradient_accumulation_steps: num('gradient_accumulation_steps') ?? defaultAdvanced.gradient_accumulation_steps,
					learning_rate: num('learning_rate') ?? defaultAdvanced.learning_rate,
					lr_scheduler: str('lr_scheduler', defaultAdvanced.lr_scheduler),
					optimizer: str('optimizer', defaultAdvanced.optimizer),
					warmup_ratio: num('warmup_ratio') ?? defaultAdvanced.warmup_ratio,
					weight_decay: num('weight_decay') ?? defaultAdvanced.weight_decay,
					sequence_len: num('sequence_len') ?? defaultAdvanced.sequence_len,
					val_set_size: num('val_set_size') ?? defaultAdvanced.val_set_size,
					lora_r: num('lora_r') ?? defaultAdvanced.lora_r,
					lora_alpha: num('lora_alpha') ?? defaultAdvanced.lora_alpha,
					lora_dropout: num('lora_dropout') ?? defaultAdvanced.lora_dropout,
					adapter: str('adapter', defaultAdvanced.adapter),
					load_in_8bit: bool('load_in_8bit', defaultAdvanced.load_in_8bit),
					load_in_4bit: bool('load_in_4bit', defaultAdvanced.load_in_4bit),
					sample_packing: bool('sample_packing', defaultAdvanced.sample_packing),
					gradient_checkpointing: bool('gradient_checkpointing', defaultAdvanced.gradient_checkpointing),
					flash_attention: bool('flash_attention', defaultAdvanced.flash_attention),
					saves_per_epoch: num('saves_per_epoch') ?? defaultAdvanced.saves_per_epoch,
					evals_per_epoch: num('evals_per_epoch') ?? defaultAdvanced.evals_per_epoch,
					bf16: str('bf16', defaultAdvanced.bf16)
				};
			}
		} catch (e) {
			console.error('Failed to load config params', e);
		} finally {
			loadingConfig = false;
		}
	};

	let prevBaseConfig = '';
	$: if (formBaseConfig !== prevBaseConfig) {
		prevBaseConfig = formBaseConfig;
		loadConfigParams(formBaseConfig);
	}

	// ── Form helpers ─────────────────────────────────────────────────────
	const resetForm = () => {
		formName = ''; formDescription = ''; formAccess = 'private';
		formBaseConfig = ''; formKnowledgeIds = []; formDatasetIds = [];
		formPromptIds = []; formAdvanced = { ...defaultAdvanced };
		showAdvanced = false; showForm = false; editingId = null;
		prevBaseConfig = '';
	};

	const openEdit = (course: TrainingCourse) => {
		editingId = course.id;
		formName = course.name;
		formDescription = course.description;
		formAccess = course.access_control === null ? 'public' : 'private';
		const d = course.data ?? {};
		formBaseConfig = d.base_config ?? '';
		formKnowledgeIds = [...(d.knowledge_ids ?? [])];
		formDatasetIds = [...(d.dataset_ids ?? [])];
		formPromptIds = [...(d.prompt_ids ?? [])];
		formAdvanced = d.advanced_config
			? { ...defaultAdvanced, ...(d.advanced_config as Partial<AdvancedParams>) }
			: { ...defaultAdvanced };
		showAdvanced = !!d.advanced_config;
		prevBaseConfig = formBaseConfig;
		showForm = true;
	};

	const handleSave = async () => {
		if (!formName.trim()) {
			toast.error($i18n.t('Please enter a name for the training course.'));
			return;
		}
		saving = true;
		try {
			const form: TrainingCourseForm = {
				name: formName.trim(),
				description: formDescription.trim(),
				access_control: formAccess === 'public' ? null : {},
				data: {
					base_config: formBaseConfig,
					knowledge_ids: formKnowledgeIds,
					dataset_ids: formDatasetIds,
					prompt_ids: formPromptIds,
					advanced_config: showAdvanced ? { ...formAdvanced } : { ...defaultAdvanced }
				}
			};

			if (editingId) {
				await updateCourse(getToken(), editingId, form);
				toast.success($i18n.t('Training course updated.'));
			} else {
				await createCourse(getToken(), form);
				toast.success($i18n.t('Training course created.'));
			}

			courses = await getCourses(getToken());
			resetForm();
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to save training course.'));
		} finally {
			saving = false;
		}
	};

	const handleDelete = async (id: string) => {
		try {
			await deleteCourse(getToken(), id);
			courses = courses.filter((c) => c.id !== id);
			toast.success($i18n.t('Training course deleted.'));
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to delete training course.'));
		}
	};

	const loadTrainableModels = async () => {
		try {
			const allModels = await getAvailableLlamolotlModels(getToken());
			trainableModels = (allModels ?? [])
				.filter((m: any) => m.trainable && m.hf_repo)
				.map((m: any) => ({
					value: m.hf_repo,
					label: `${m.name} (${m.hf_repo})`
				}));
		} catch (e) {
			console.error('Failed to load trainable models:', e);
		}
	};

	const openJobModal = async (courseId: string) => {
		jobCourseId = courseId;
		jobModelId = '';
		modelSearch = '';
		showModelDropdown = false;
		showJobModal = true;
		if (trainableModels.length === 0) {
			await loadTrainableModels();
		}
	};

	const handleSubmitJob = async () => {
		if (!jobModelId) {
			toast.error($i18n.t('Please select a model to train.'));
			return;
		}
		submitting = true;
		try {
			await createJob(getToken(), jobCourseId, jobModelId);
			toast.success($i18n.t('Training job submitted and pending admin approval.'));
			showJobModal = false;
		} catch (e) {
			toast.error(typeof e === 'string' ? e : $i18n.t('Failed to submit training job.'));
		} finally {
			submitting = false;
		}
	};

	const setAccess = (val: string) => { formAccess = val === 'public' ? 'public' : 'private'; };

	const toggleAdvanced = (key: string) => {
		formAdvanced = { ...formAdvanced, [key]: !(formAdvanced as Record<string, unknown>)[key] };
	};

	const isAdvancedChecked = (key: string): boolean =>
		!!(formAdvanced as Record<string, unknown>)[key];

	const toggle = (arr: string[], val: string): string[] =>
		arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];

	const getKnowledgeName = (id: string) =>
		knowledgeBases.find((k: any) => k.id === id)?.name ?? id;

	const getPromptName = (cmd: string) =>
		($prompts ?? []).find((p: any) => p.command === cmd)?.title ?? cmd;

	onMount(async () => {
		try {
			const [coursesData, kbData, statusData] = await Promise.all([
				getCourses(getToken()),
				getKnowledgeBases(getToken()),
				getLlamolotlTrainingStatus(getToken()).catch(() => null)
			]);
			courses = coursesData;
			knowledgeBases = kbData;

			if (statusData?.ENABLE_LLAMOLOTL_API) {
				availableConfigs = await getLlamolotlTrainingConfigs(getToken()).catch(() => []);
			}
		} catch (e) {
			console.error('Failed to load training page:', e);
		} finally {
			loaded = true;
		}
	});
</script>

<svelte:head>
	<title>{$i18n.t('Training')} | {$WEBUI_NAME}</title>
</svelte:head>

{#if !loaded}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{:else}
	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
				{$i18n.t('Training Courses')}
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{filteredCourses.length}</span>
			</div>
			<button
				class="px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center space-x-1"
				on:click={() => { resetForm(); showForm = true; }}
				aria-label={$i18n.t('Create')}
			>
				<Plus className="size-3.5" />
			</button>
		</div>

		<div class="flex w-full space-x-2">
			<div class="flex flex-1">
				<div class="self-center ml-1 mr-3"><Search className="size-3.5" /></div>
				<input
					class="w-full text-sm py-1 rounded-r-xl outline-none bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Training Courses')}
				/>
			</div>
		</div>
	</div>

	<!-- Create / Edit Form -->
	{#if showForm}
		<div class="mt-2 mb-4 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
			<div class="flex items-center justify-between mb-4">
				<div class="font-medium text-sm">
					{$i18n.t(editingId ? 'Edit Training Course' : 'New Training Course')}
				</div>
				<button class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition" on:click={resetForm}>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-gray-500">
						<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
					</svg>
				</button>
			</div>

			<div class="space-y-4">
				<div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Name')}</div>
					<input class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800"
						bind:value={formName} placeholder={$i18n.t('e.g. Customer Support Fine-tune')} />
				</div>

				<div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Description')}</div>
					<textarea class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800 resize-y min-h-[60px]"
						bind:value={formDescription} placeholder={$i18n.t('What will models learn from this course?')}></textarea>
				</div>

				<!-- Visibility -->
				<div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Visibility')}</div>
					<div class="flex gap-2">
						{#each [['public', 'Public'], ['private', 'Private']] as [val, label]}
							<button
								class="px-3 py-1.5 rounded-lg text-xs font-medium transition border {formAccess === val
									? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300'
									: 'border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850'}"
								on:click={() => setAccess(val)}
							>
								{$i18n.t(label)}
							</button>
						{/each}
					</div>
				</div>

				<!-- Base Config -->
				<div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Base Training Config')}</div>
					{#if availableConfigs.length > 0}
						<select class="w-full rounded-xl px-3 py-2 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800"
							bind:value={formBaseConfig}>
							<option value="">{$i18n.t('Select a base config...')}</option>
							{#each availableConfigs as cfg}
								<option value={cfg.path}>{cfg.name}</option>
							{/each}
						</select>
					{:else}
						<div class="rounded-xl px-3 py-2 text-sm text-gray-400 dark:text-gray-500 border border-gray-200 dark:border-gray-800">
							{$i18n.t('No base configs available — check Llamolotl connection in admin settings.')}
						</div>
					{/if}
				</div>

				<!-- Knowledge Bases -->
				<div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1.5">
						{$i18n.t('Knowledge Bases')}
						{#if formKnowledgeIds.length > 0}<span class="ml-1 text-gray-400">({formKnowledgeIds.length})</span>{/if}
					</div>
					{#if knowledgeItems.length > 0}
						<div class="flex flex-wrap gap-1.5">
							{#each knowledgeItems as item}
								<button
									class="px-2.5 py-1 rounded-lg text-xs transition border {formKnowledgeIds.includes(item.id)
										? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300'
										: 'border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 text-gray-700 dark:text-gray-300'}"
									on:click={() => (formKnowledgeIds = toggle(formKnowledgeIds, item.id))}
								>{item.name}</button>
							{/each}
						</div>
					{:else}
						<div class="text-xs text-gray-400 dark:text-gray-500">{$i18n.t('No knowledge bases available.')}</div>
					{/if}
				</div>

				<!-- Datasets -->
				<div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1.5">
						{$i18n.t('Datasets')}
						{#if formDatasetIds.length > 0}<span class="ml-1 text-gray-400">({formDatasetIds.length})</span>{/if}
					</div>
					{#if datasetItems.length > 0}
						<div class="flex flex-wrap gap-1.5">
							{#each datasetItems as item}
								<button
									class="px-2.5 py-1 rounded-lg text-xs transition border {formDatasetIds.includes(item.id)
										? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300'
										: 'border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 text-gray-700 dark:text-gray-300'}"
									on:click={() => (formDatasetIds = toggle(formDatasetIds, item.id))}
								>{item.name}</button>
							{/each}
						</div>
					{:else}
						<div class="text-xs text-gray-400 dark:text-gray-500">{$i18n.t('No datasets available.')}</div>
					{/if}
				</div>

				<!-- Prompts -->
				<div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1.5">
						{$i18n.t('Prompts')}
						{#if formPromptIds.length > 0}<span class="ml-1 text-gray-400">({formPromptIds.length})</span>{/if}
					</div>
					{#if ($prompts ?? []).length > 0}
						<div class="flex flex-wrap gap-1.5">
							{#each $prompts ?? [] as prompt}
								<button
									class="px-2.5 py-1 rounded-lg text-xs transition border {formPromptIds.includes(prompt.command)
										? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300'
										: 'border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 text-gray-700 dark:text-gray-300'}"
									on:click={() => (formPromptIds = toggle(formPromptIds, prompt.command))}
								>{prompt.title ?? prompt.command}</button>
							{/each}
						</div>
					{:else}
						<div class="text-xs text-gray-400 dark:text-gray-500">{$i18n.t('No prompts available.')}</div>
					{/if}
				</div>

				<!-- Advanced Config -->
				<div>
					<button
						class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
						on:click={() => (showAdvanced = !showAdvanced)}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3 transition-transform {showAdvanced ? 'rotate-90' : ''}">
							<path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
						</svg>
						{$i18n.t('Advanced Configuration')}
						{#if loadingConfig}<Spinner className="size-3" />{/if}
					</button>

					{#if showAdvanced}
						<div class="mt-3 space-y-4 pl-1 border-l-2 border-gray-100 dark:border-gray-800 ml-1">
							<div>
								<div class="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2 pl-3">{$i18n.t('Training')}</div>
								<div class="grid grid-cols-2 sm:grid-cols-3 gap-3 pl-3">
									<div><label class="text-[11px] text-gray-400">{$i18n.t('Epochs')}</label>
										<input type="number" min="1" step="1" bind:value={formAdvanced.num_epochs} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('Micro Batch Size')}</label>
										<input type="number" min="1" step="1" bind:value={formAdvanced.micro_batch_size} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('Grad Accum Steps')}</label>
										<input type="number" min="1" step="1" bind:value={formAdvanced.gradient_accumulation_steps} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('Learning Rate')}</label>
										<input type="number" min="0" step="0.00001" bind:value={formAdvanced.learning_rate} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('LR Scheduler')}</label>
										<select bind:value={formAdvanced.lr_scheduler} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800">
											<option value="cosine">cosine</option><option value="linear">linear</option><option value="constant">constant</option><option value="constant_with_warmup">constant_with_warmup</option>
										</select></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('Optimizer')}</label>
										<select bind:value={formAdvanced.optimizer} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800">
											<option value="adamw_bnb_8bit">adamw_bnb_8bit</option><option value="adamw_torch">adamw_torch</option><option value="paged_adamw_32bit">paged_adamw_32bit</option><option value="paged_adamw_8bit">paged_adamw_8bit</option><option value="sgd">sgd</option>
										</select></div>
								</div>
							</div>

							<div>
								<div class="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2 pl-3">{$i18n.t('LoRA / Adapter')}</div>
								<div class="grid grid-cols-2 sm:grid-cols-3 gap-3 pl-3">
									<div><label class="text-[11px] text-gray-400">{$i18n.t('Adapter')}</label>
										<select bind:value={formAdvanced.adapter} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800">
											<option value="lora">lora</option><option value="qlora">qlora</option>
										</select></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('LoRA Rank (r)')}</label>
										<input type="number" min="1" step="1" bind:value={formAdvanced.lora_r} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('LoRA Alpha')}</label>
										<input type="number" min="1" step="1" bind:value={formAdvanced.lora_alpha} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('LoRA Dropout')}</label>
										<input type="number" min="0" max="1" step="0.01" bind:value={formAdvanced.lora_dropout} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
								</div>
							</div>

							<div>
								<div class="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2 pl-3">{$i18n.t('Performance')}</div>
								<div class="flex flex-wrap gap-3 pl-3">
									{#each [['load_in_8bit', 'Load in 8-bit'], ['load_in_4bit', 'Load in 4-bit'], ['sample_packing', 'Sample Packing'], ['gradient_checkpointing', 'Gradient Checkpointing'], ['flash_attention', 'Flash Attention']] as [key, label]}
										<label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300 cursor-pointer">
											<input type="checkbox" checked={isAdvancedChecked(key)} on:change={() => toggleAdvanced(key)} class="rounded" />
											{$i18n.t(label)}
										</label>
									{/each}
								</div>
								<div class="grid grid-cols-2 sm:grid-cols-3 gap-3 pl-3 mt-2">
									<div><label class="text-[11px] text-gray-400">{$i18n.t('Sequence Length')}</label>
										<input type="number" min="1" step="1" bind:value={formAdvanced.sequence_len} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800" /></div>
									<div><label class="text-[11px] text-gray-400">{$i18n.t('BF16')}</label>
										<select bind:value={formAdvanced.bf16} class="w-full rounded-lg px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-800">
											<option value="auto">auto</option><option value="true">true</option><option value="false">false</option>
										</select></div>
								</div>
							</div>
						</div>
					{/if}
				</div>

				<div class="flex justify-end gap-2 pt-1">
					<button class="px-3 py-1.5 rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-gray-850 transition" on:click={resetForm}>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-4 py-1.5 rounded-xl text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition disabled:opacity-50"
						on:click={handleSave} disabled={saving || !formName.trim()}
					>
						{saving ? $i18n.t('Saving...') : $i18n.t(editingId ? 'Save' : 'Create')}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Course List -->
	<div class="mb-5 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-2">
		{#each filteredCourses as course}
			<div class="flex flex-col text-left w-full px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-xl">
				<div class="flex items-center justify-between -mt-1">
					<div class="flex items-center gap-1.5">
						{#if course.access_control === null}
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300">{$i18n.t('Public')}</span>
						{:else}
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">{$i18n.t('Private')}</span>
						{/if}
					</div>
					<div class="flex items-center gap-1 -mr-1">
						<Tooltip content={$i18n.t('Submit Training Job')}>
							<button class="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => openJobModal(course.id)}>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-blue-500">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
								</svg>
							</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Edit')}>
							<button class="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => openEdit(course)}>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-500 dark:text-gray-400">
									<path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
								</svg>
							</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Delete')}>
							<button class="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => handleDelete(course.id)}>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5 text-gray-500 hover:text-red-500 transition">
									<path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022 1.005 11.36A2.75 2.75 0 007.77 20h4.46a2.75 2.75 0 002.751-2.689l1.005-11.36.149.022a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 01.7.797l-.5 5.5a.75.75 0 01-1.494-.136l.5-5.5a.75.75 0 01.794-.66zm2.84 0a.75.75 0 01.794.66l.5 5.5a.75.75 0 01-1.494.137l-.5-5.5a.75.75 0 01.7-.798z" clip-rule="evenodd" />
								</svg>
							</button>
						</Tooltip>
					</div>
				</div>

				<div class="flex-1 px-1 mb-1">
					<div class="font-semibold line-clamp-1">{course.name}</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
						{course.description || $i18n.t('No description')}
					</div>
					<div class="mt-2 flex flex-wrap gap-1">
						{#if course.data?.base_config}
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
								{course.data.base_config.split('/').pop()}
							</span>
						{/if}
						{#each (course.data?.knowledge_ids ?? []) as kid}
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300">{getKnowledgeName(kid)}</span>
						{/each}
						{#each (course.data?.dataset_ids ?? []) as did}
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">{getKnowledgeName(did)}</span>
						{/each}
						{#each (course.data?.prompt_ids ?? []) as pid}
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-300">{getPromptName(pid)}</span>
						{/each}
						{#if course.data?.advanced_config}
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">{$i18n.t('Custom params')}</span>
						{/if}
					</div>
					<div class="mt-2 flex justify-end">
						<div class="text-xs text-gray-500">{$i18n.t('Updated')} {dayjs(course.updated_at * 1000).fromNow()}</div>
					</div>
				</div>
			</div>
		{/each}
	</div>

	{#if filteredCourses.length === 0 && !showForm}
		<div class="flex flex-col items-center justify-center py-12 text-center">
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{query ? $i18n.t('No courses match your search.') : $i18n.t('No training courses yet.')}
			</div>
			{#if !query}
				<button
					class="mt-3 px-4 py-1.5 rounded-xl text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition"
					on:click={() => { resetForm(); showForm = true; }}
				>
					{$i18n.t('Create your first course')}
				</button>
			{/if}
		</div>
	{/if}
{/if}

<!-- Submit Job Modal -->
{#if showJobModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4">
			<div class="font-semibold text-base mb-4">{$i18n.t('Submit Training Job')}</div>

			<div class="mb-4 relative">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Model')}</div>
				<button
					type="button"
					class="w-full rounded-xl px-3 py-2 text-sm text-left bg-gray-50 dark:bg-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700 flex items-center justify-between"
					on:click={() => { showModelDropdown = !showModelDropdown; modelSearch = ''; }}
				>
					<span class={jobModelId ? '' : 'text-gray-400'}>
						{jobModelId ? (trainableModels.find((m) => m.value === jobModelId)?.label ?? jobModelId) : $i18n.t('Select a trainable model')}
					</span>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4 text-gray-400">
						<path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clip-rule="evenodd" />
					</svg>
				</button>

				{#if showModelDropdown}
					<div class="absolute z-[60] mt-1 w-full rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-lg">
						<div class="p-2">
							<input
								class="w-full rounded-lg px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-900 dark:text-gray-100 outline-none border border-gray-200 dark:border-gray-700"
								bind:value={modelSearch}
								placeholder={$i18n.t('Search models...')}
							/>
						</div>
						<div class="max-h-48 overflow-y-auto px-1 pb-1">
							{#each filteredTrainableModels as model}
								<button
									type="button"
									class="w-full text-left px-3 py-1.5 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition {jobModelId === model.value ? 'bg-gray-100 dark:bg-gray-700 font-medium' : ''}"
									on:click={() => { jobModelId = model.value; showModelDropdown = false; }}
								>
									{model.label}
								</button>
							{:else}
								<div class="px-3 py-2 text-sm text-gray-400">{$i18n.t('No trainable models found')}</div>
							{/each}
						</div>
					</div>
				{/if}

				<div class="mt-1.5 text-[11px] text-gray-400 dark:text-gray-500">
					{$i18n.t('Select a trainable model to fine-tune with this course.')}
				</div>
			</div>

			<div class="text-xs text-gray-400 dark:text-gray-500 mb-4">
				{$i18n.t('The job will be submitted for admin approval before training begins.')}
			</div>

			<div class="flex justify-end gap-2">
				<button class="px-3 py-1.5 rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition" on:click={() => (showJobModal = false)}>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-4 py-1.5 rounded-xl text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition disabled:opacity-50"
					on:click={handleSubmitJob} disabled={submitting || !jobModelId}
				>
					{submitting ? $i18n.t('Submitting...') : $i18n.t('Submit Job')}
				</button>
			</div>
		</div>
	</div>
{/if}
