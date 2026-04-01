<script lang="ts">
	import Fuse from 'fuse.js';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { onMount, getContext, onDestroy, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { mobile, showSidebar, knowledge as _knowledge } from '$lib/stores';

	import { updateFileDataContentById, uploadFile, getFileById } from '$lib/apis/files';
	import {
		addFileToKnowledgeById,
		getKnowledgeById,
		getKnowledgeBases,
		removeFileFromKnowledgeById,
		resetKnowledgeById,
		updateFileFromKnowledgeById,
		updateKnowledgeById,
		prepareKnowledgeInput
	} from '$lib/apis/knowledge';

	import { transcribeAudio } from '$lib/apis/audio';
	import { blobToFile } from '$lib/utils';
	import { processWeb, startWebCrawl, getWebCrawlStatus, cancelWebCrawl, listWebCrawlJobs, getRAGConfig } from '$lib/apis/retrieval';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Files from './KnowledgeBase/Files.svelte';
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';

	import SavePipelineModal from './KnowledgeBase/PipelineModal.svelte';
	import AddContentMenu from './KnowledgeBase/AddContentMenu.svelte';
	import AddTextContentModal from './KnowledgeBase/AddTextContentModal.svelte';
	import AddWebUrlModal from './KnowledgeBase/AddWebUrlModal.svelte';

	import SyncConfirmDialog from '../../common/ConfirmDialog.svelte';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import PipelineCanvas from './KnowledgeBase/PipelineCanvas.svelte';
	import { createCuratorJob } from '$lib/apis/curator';
    import PipelineNode from './KnowledgeBase/PipelineNode.svelte';

	let activeTab: 'files' | 'pipeline' = 'files';
	let largeScreen = true;

	let pane;
	let showSidepanel = true;
	let minSize = 0;

	type Knowledge = {
		id: string;
		name: string;
		description: string;
		data: {
			file_ids: string[];
		};
		files: any[];
	};

	let id = null;
	let knowledge: Knowledge | null = null;
	let query = '';

	let showAddTextContentModal = false;
	let showSyncConfirmModal = false;
	let showAccessControlModal = false;
	let showAddWebUrlModal = false;
	let showAddWebCrawlModal = false;
	let webLoaderEngine = '';
	let crawlLoading = false;
	let crawlJobId: string | null = null;
	let crawlUrl = '';
	let crawlProgress: { completed: number; total: number; savedCount?: number } | null = null;
	let crawlPollTimer: ReturnType<typeof setTimeout> | null = null;
	let crawlTempItemId: string | null = null;
	let lastProcessedPageIndex = 0;
	let crawlLogs: string[] = [];

	let pipelineCreatedAt = null;
	let pipelineName = 'Untitled';
	let showPipelineModal = false;
	let pipelineNodes = [];
	let pipelineConnections = [];
	let pipelineModalMode: 'save' | 'load' = 'save';
	let pendingRun = false;

	$: pipelineConfigs = (knowledge?.files ?? [])
		.filter(f => (f.name ?? f.meta?.name)?.endsWith(`_pipeline.json`))
		.map(f => {
			const raw = f.name ?? f.meta?.name ?? '';
			const base = raw.length > 37 && raw[36] === '-' ? raw.substring(37) : raw;
			const suffix = `_${knowledge.name}_pipeline.json`;
			return { id: f.id, name: base.endsWith(suffix) ? base.slice(0, -suffix.length) : base };
		});

	let inputFiles = null;

	let filteredItems = [];
	$: if (knowledge && knowledge.files) {
		fuse = new Fuse(knowledge.files, {
			keys: ['meta.name', 'meta.description']
		});
	}

	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: (knowledge?.files ?? []);
	}

	let selectedFile = null;
	let selectedFileId = null;

	$: if (selectedFileId) {
		const file = (knowledge?.files ?? []).find((file) => file.id === selectedFileId);
		if (file) {
			file.data = file.data ?? { content: '' };
			selectedFile = file;
		} else {
			selectedFile = null;
		}
	} else {
		selectedFile = null;
	}

	let fuse = null;
	let debounceTimeout = null;
	let mediaQuery;
	let dragged = false;

	const createFileFromText = (name, content) => {
		const blob = new Blob([content], { type: 'text/plain' });
		const file = blobToFile(blob, `${name}.txt`);

		console.log(file);
		return file;
	};

	const createPipelineFile = (content) => {
		const blob = new Blob([content], { type: 'application/json'})
		const file = blobToFile(blob, `${pipelineName}_${knowledge.name}_pipeline.json`)

		console.log(file);
		return file;
	}; 

	const loadPipelineHandler = async (fileId) => {
		try {
			const loadedFile = await getFileById(localStorage.token, fileId);
		
			if (loadedFile) {
				console.log(loadedFile);
				const loadedContent = JSON.parse(loadedFile.data.content)
				pipelineName = loadedContent.name;
				pipelineCreatedAt = loadedContent.created_at;
				pipelineNodes = loadedContent.nodes;
				pipelineConnections = loadedContent.connections;
			} else {
				toast.error($i18n.t('Failed to load config'))
				return null;
			}
		} catch (error) {
			toast.error(error)
		}
	}

	
	const savePipelineHandler = async () => {
		const existing = knowledge?.files.find(f => (f.name ?? f.meta?.name)?.endsWith(`${pipelineName}_${knowledge.name}_pipeline.json`))
		const now = new Date().toISOString();
		const createdAt = pipelineCreatedAt ?? now;
		const pipelineConfig = {
			created_at: createdAt,
			updated_at: now,
			name: pipelineName,
			nodes: pipelineNodes,
			connections: pipelineConnections
		};
		pipelineCreatedAt = createdAt
		if (existing) {
			await updateFileDataContentById(localStorage.token, existing.id, JSON.stringify(pipelineConfig))
			showPipelineModal = false;
			if (pendingRun) {
			    pendingRun = false;
			    runPipelineHandler();
			}
			return;
		} else {
		const configFile = createPipelineFile(JSON.stringify(pipelineConfig));
		
		if (configFile.size == 0) {
			toast.error($i18n.t('You cannot save an empty pipeline'))
			return null;
		}
		try {
		const uploadedPipeline = await uploadFile(localStorage.token, configFile);

		if (uploadedPipeline) {
			console.log(uploadedPipeline);
			await addFileHandler(uploadedPipeline.id)
			showPipelineModal = false;
		} else {
			toast.error($i18n.t('Failed to save config'))
			showPipelineModal = false;
			return null;
		}

		}
		catch (e) {
			toast.error(e);
			showPipelineModal = false;
		}

		if (pendingRun) {
			pendingRun = false;
			runPipelineHandler();
		}
	};
	};

	const runPipelineHandler = async () => {
		const source = pipelineNodes.find(n => n.type === 'source');
		const sink = pipelineNodes.find(n => n.type === 'sink');

		if (!knowledge) return;
		if (pipelineName === 'Untitled') {
			pendingRun = true;
			pipelineModalMode = 'save';
			showPipelineModal = true;
			return;
		}

		if (!source || !sink) {
			toast.error('Pipeline must have a Source and a Sink');
			return;
		}

		//Walk connections from source to sink in order
		const connMap = Object.fromEntries(pipelineConnections.map(c => [c.fromId, c.toId]));
		const stages = [];
		let currentId = source.id;

		while (connMap[currentId] && connMap[currentId] !== sink.id) {
			currentId = connMap[currentId];
			const node = pipelineNodes.find(n => n.id === currentId);
			if (!node || node.type !== 'transform' || !node.config?.stage_type) {
				toast.error(`Node "${node?.label ?? currentId}" is missing a stage type`);
            	return;
			}
			// Strip null params before sending
	        const params = Object.fromEntries(
	            Object.entries(node.config.params ?? {}).filter(([_, v]) => v !== null)
	        );
	        stages.push({ type: node.config.stage_type, params });
	    }

	    if (!connMap[source.id]) {
	        toast.error('Source node is not connected');
	        return;
	    }

		const textField = source.config?.text_field || 'text';
		const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
		//const filename = (sink.config?.filename || 'output').replace(/\.jsonl$/, '');
		const outputPath = `/workspace/ui-data/uploads/${knowledge.id}/output/${pipelineName}`;

		let inputPath: string;
		let outputFormat: string = 'jsonl'
		try {
		    const prepared = await prepareKnowledgeInput(localStorage.token, knowledge.id);
		    toast.info(`Prepared ${prepared.file_count} files for curation`);
		    inputPath = prepared.input_path;
			outputFormat = prepared.output_format ?? 'jsonl';
			} catch (e) {
			toast.error(typeof e === 'string' ? e : (e?.detail ?? 'Failed to prepare input'));
		    return;
		}


	    try {
	        const job = await createCuratorJob(localStorage.token, {
	            name: `${pipelineName}-${timestamp}`,
	            input_path: inputPath,
	            output_path: outputPath,
	            text_field: textField,
				output_format: outputFormat,
	            stages
	        });
	        toast.success(`Job started: ${job.job_id}`);
	    } catch (e) {
	        toast.error(typeof e === 'string' ? e : (e?.detail ?? 'Failed to start job'));
	    }
	};

	const uploadFileHandler = async (file) => {
		console.log(file);

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: '',
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		knowledge.files = [...(knowledge.files ?? []), fileItem];

		// Check if the file is an audio file and transcribe/convert it to text file
		if (['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-m4a'].includes(file['type'])) {
			const res = await transcribeAudio(localStorage.token, file).catch((error) => {
				toast.error(error);
				return null;
			});

			if (res) {
				console.log(res);
				const blob = new Blob([res.text], { type: 'text/plain' });
				file = blobToFile(blob, `${file.name}.txt`);
			}
		}

		try {
			const uploadedFile = await uploadFile(localStorage.token, file).catch((e) => {
				toast.error(e);
				return null;
			});

			if (uploadedFile) {
				console.log(uploadedFile);
				knowledge.files = knowledge.files.map((item) => {
					if (item.itemId === tempItemId) {
						item.id = uploadedFile.id;
					}

					// Remove temporary item id
					delete item.itemId;
					return item;
				});
				await addFileHandler(uploadedFile.id);
			} else {
				toast.error($i18n.t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(e);
		}
	};

	const uploadDirectoryHandler = async () => {
		// Check if File System Access API is supported
		const isFileSystemAccessSupported = 'showDirectoryPicker' in window;

		try {
			if (isFileSystemAccessSupported) {
				// Modern browsers (Chrome, Edge) implementation
				await handleModernBrowserUpload();
			} else {
				// Firefox fallback
				await handleFirefoxUpload();
			}
		} catch (error) {
			handleUploadError(error);
		}
	};

	// Helper function to check if a path contains hidden folders
	const hasHiddenFolder = (path) => {
		return path.split('/').some((part) => part.startsWith('.'));
	};

	// Modern browsers implementation using File System Access API
	const handleModernBrowserUpload = async () => {
		const dirHandle = await window.showDirectoryPicker();
		let totalFiles = 0;
		let uploadedFiles = 0;

		// Function to update the UI with the progress
		const updateProgress = () => {
			const percentage = (uploadedFiles / totalFiles) * 100;
			toast.info(`Upload Progress: ${uploadedFiles}/${totalFiles} (${percentage.toFixed(2)}%)`);
		};

		// Recursive function to count all files excluding hidden ones
		async function countFiles(dirHandle) {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				if (entry.kind === 'file') {
					totalFiles++;
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await countFiles(entry);
					}
				}
			}
		}

		// Recursive function to process directories excluding hidden files and folders
		async function processDirectory(dirHandle, path = '') {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				const entryPath = path ? `${path}/${entry.name}` : entry.name;

				// Skip if the path contains any hidden folders
				if (hasHiddenFolder(entryPath)) continue;

				if (entry.kind === 'file') {
					const file = await entry.getFile();
					const fileWithPath = new File([file], entryPath, { type: file.type });

					await uploadFileHandler(fileWithPath);
					uploadedFiles++;
					updateProgress();
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await processDirectory(entry, entryPath);
					}
				}
			}
		}

		await countFiles(dirHandle);
		updateProgress();

		if (totalFiles > 0) {
			await processDirectory(dirHandle);
		} else {
			console.log('No files to upload.');
		}
	};

	const scrapeURLHandler = async () => {
		showAddWebUrlModal = true;
	};

	const submitScrapeURLHandler = async (url: string) => {
		console.log('[scrapeURL] Starting scrape for:', url);

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: url,
			size: 0,
			status: 'uploading',
			error: '',
			itemId: tempItemId
		};

		knowledge.files = [...(knowledge.files ?? []), fileItem];
		console.log('[scrapeURL] Added placeholder to files list, tempItemId:', tempItemId);

		const res = await processWeb(localStorage.token, id, url).catch((e) => {
			console.error('[scrapeURL] processWeb failed:', e);
			toast.error(e);
			return null;
		});

		console.log('[scrapeURL] processWeb response:', res);

		if (res) {
			const content = res?.file?.data?.content ?? '';
			console.log('[scrapeURL] Extracted content length:', content.length, 'chars');

			const blob = new Blob([content], { type: 'text/plain' });
			const file = blobToFile(blob, `${url}.md`);
			console.log('[scrapeURL] Created file blob, uploading...');

			const uploadedFile = await uploadFile(localStorage.token, file).catch((e) => {
				console.error('[scrapeURL] uploadFile failed:', e);
				toast.error(e);
				return null;
			});

			console.log('[scrapeURL] uploadFile response:', uploadedFile);

			if (uploadedFile) {
				knowledge.files = knowledge.files.map((item) => {
					if (item.itemId === tempItemId) {
						item.id = uploadedFile.id;
					}
					delete item.itemId;
					return item;
				});
				console.log('[scrapeURL] Updated placeholder with file id:', uploadedFile.id, '— calling addFileHandler');
				await addFileHandler(uploadedFile.id);
			} else {
				console.warn('[scrapeURL] uploadFile returned null, removing placeholder');
				knowledge.files = knowledge.files.filter((item) => item.itemId !== tempItemId);
				toast.error($i18n.t('Failed to upload scraped content.'));
			}
		} else {
			console.warn('[scrapeURL] processWeb returned null, removing placeholder');
			knowledge.files = knowledge.files.filter((item) => item.itemId !== tempItemId);
		}
	};

// ── Crawl polling (top-level so onMount can resume it after a refresh) ──────
	const startPolling = () => {
		const pollCrawlStatus = async () => {
			if (!crawlJobId) return;

			const jobStatus = await getWebCrawlStatus(localStorage.token, crawlJobId).catch((e) => {
				console.error('[crawlURL] poll failed:', e);
				return null;
			});

			console.log('[crawlURL] poll:', jobStatus);
			if (!jobStatus) {
				crawlPollTimer = setTimeout(pollCrawlStatus, 2000) as any;
				return;
			}

			crawlProgress = {
				completed: jobStatus.completed ?? 0,
				total: jobStatus.total ?? 0,
				savedCount: jobStatus.saved_count ?? 0
			};

			// Log newly arrived page titles (display only — backend handles embedding)
			const pages: Array<{ url: string; title: string }> = jobStatus.pages ?? [];
			const newPages = pages.slice(lastProcessedPageIndex);
			for (const page of newPages) {
				crawlLogs = [...crawlLogs, `↳ ${page.title?.trim() || page.url}`];
				lastProcessedPageIndex++;
			}

			if (jobStatus.status === 'completed') {
				crawlPollTimer = null;
				crawlLoading = false;
				const savedCount = jobStatus.saved_count ?? 0;
				crawlLogs = [...crawlLogs, `Done — ${savedCount} page(s) saved.`];
				showAddWebCrawlModal = false;
				// Refresh knowledge from the API since the backend added files directly
				const refreshed = await getKnowledgeById(localStorage.token, id).catch(() => null);
				if (refreshed) knowledge = refreshed;
				knowledge.files = (knowledge.files ?? []).filter((item) => item.itemId !== crawlTempItemId);
				crawlTempItemId = null;
				if (savedCount === 0) toast.warning($i18n.t('No pages were saved.'));
				localStorage.removeItem('activeCrawlJob');
			} else if (jobStatus.status === 'failed') {
				crawlPollTimer = null;
				crawlLoading = false;
				crawlLogs = [...crawlLogs, 'Crawl failed.'];
				showAddWebCrawlModal = false;
				knowledge.files = (knowledge.files ?? []).filter((item) => item.itemId !== crawlTempItemId);
				crawlTempItemId = null;
				toast.error($i18n.t('Crawl failed.'));
				localStorage.removeItem('activeCrawlJob');
			} else if (jobStatus.status === 'cancelled') {
				crawlPollTimer = null;
				crawlLoading = false;
				showAddWebCrawlModal = false;
				const refreshed = await getKnowledgeById(localStorage.token, id).catch(() => null);
				if (refreshed) knowledge = refreshed;
				knowledge.files = (knowledge.files ?? []).filter((item) => item.itemId !== crawlTempItemId);
				crawlTempItemId = null;
				localStorage.removeItem('activeCrawlJob');
				if (jobStatus.cancel_reason) {
					toast.warning(jobStatus.cancel_reason);
				}
			} else {
				crawlPollTimer = setTimeout(pollCrawlStatus, 2000) as any;
			}
		};

		crawlPollTimer = setTimeout(pollCrawlStatus, 2000) as any;
	};

	const submitCrawlURLHandler = async (url: string, limit: number = 10, maxDepth: number = 3, crawlDelay: number = 2, max403s: number = 5, includePaths: string[] = [], excludePaths: string[] = [], regexOnFullUrl: boolean = false, crawlEntireDomain: boolean = false, batchSize: number = 10) => {
		console.log('[crawlURL] Starting crawl for:', url, 'limit:', limit);
		crawlLoading = true;
		crawlProgress = null;
		crawlLogs = [];

		const tempItemId = uuidv4();
		crawlTempItemId = tempItemId;
		crawlUrl = url;
		knowledge.files = [
			...(knowledge.files ?? []),
			{
				type: 'file',
				file: '',
				id: null,
				url: '',
				name: url,
				size: 0,
				status: 'uploading',
				error: '',
				itemId: tempItemId
			}
		];
		console.log('[crawlURL] Added placeholder, tempItemId:', tempItemId);

		const startRes = await startWebCrawl(localStorage.token, id, url, limit, crawlDelay, maxDepth, max403s > 0 ? max403s : null, includePaths.length > 0 ? includePaths : null, excludePaths.length > 0 ? excludePaths : null, regexOnFullUrl || null, crawlEntireDomain || null, batchSize).catch((e) => {
			console.error('[crawlURL] startWebCrawl failed:', e);
			toast.error(e);
			return null;
		});

		if (!startRes) {
			crawlLoading = false;
			showAddWebCrawlModal = false;
			knowledge.files = knowledge.files.filter((item) => item.itemId !== tempItemId);
			crawlTempItemId = null;
			return;
		}

		crawlJobId = startRes.job_id;
		lastProcessedPageIndex = 0;
		crawlLogs = ['Crawl started…'];
		console.log('[crawlURL] Job started, job_id:', crawlJobId);

		localStorage.setItem('activeCrawlJob', JSON.stringify({
			jobId: crawlJobId, knowledgeId: id, url, tempItemId, lastProcessedPageIndex: 0
		}));

		startPolling();
	};


	const cancelCrawlHandler = async () => {
		console.log('[crawlURL] Cancelling job:', crawlJobId);

		if (crawlPollTimer) {
			clearTimeout(crawlPollTimer ?? undefined);
			crawlPollTimer = null;
		}

		if (crawlJobId) {
			await cancelWebCrawl(localStorage.token, crawlJobId).catch((e) =>
				console.error('[crawlURL] cancel request failed:', e)
			);
			crawlJobId = null;
		}

		crawlLoading = false;
		showAddWebCrawlModal = false;
		crawlProgress = null;

		if (crawlTempItemId) {
			knowledge.files = knowledge.files.filter((item) => item.itemId !== crawlTempItemId);
			crawlTempItemId = null;
		}

		localStorage.removeItem('activeCrawlJob');
		toast.info($i18n.t('Crawl cancelled.'));
	};

	// Firefox fallback implementation using traditional file input
	const handleFirefoxUpload = async () => {
		return new Promise((resolve, reject) => {
			// Create hidden file input
			const input = document.createElement('input');
			input.type = 'file';
			input.webkitdirectory = true;
			input.directory = true;
			input.multiple = true;
			input.style.display = 'none';

			// Add input to DOM temporarily
			document.body.appendChild(input);

			input.onchange = async () => {
				try {
					const files = Array.from(input.files)
						// Filter out files from hidden folders
						.filter((file) => !hasHiddenFolder(file.webkitRelativePath));

					let totalFiles = files.length;
					let uploadedFiles = 0;

					// Function to update the UI with the progress
					const updateProgress = () => {
						const percentage = (uploadedFiles / totalFiles) * 100;
						toast.info(
							`Upload Progress: ${uploadedFiles}/${totalFiles} (${percentage.toFixed(2)}%)`
						);
					};

					updateProgress();

					// Process all files
					for (const file of files) {
						// Skip hidden files (additional check)
						if (!file.name.startsWith('.')) {
							const relativePath = file.webkitRelativePath || file.name;
							const fileWithPath = new File([file], relativePath, { type: file.type });

							await uploadFileHandler(fileWithPath);
							uploadedFiles++;
							updateProgress();
						}
					}

					// Clean up
					document.body.removeChild(input);
					resolve();
				} catch (error) {
					reject(error);
				}
			};

			input.onerror = (error) => {
				document.body.removeChild(input);
				reject(error);
			};

			// Trigger file picker
			input.click();
		});
	};

	// Error handler
	const handleUploadError = (error) => {
		if (error.name === 'AbortError') {
			toast.info('Directory selection was cancelled');
		} else {
			toast.error('Error accessing directory');
			console.error('Directory access error:', error);
		}
	};

	// Helper function to maintain file paths within zip
	const syncDirectoryHandler = async () => {
		if ((knowledge?.files ?? []).length > 0) {
			const res = await resetKnowledgeById(localStorage.token, id).catch((e) => {
				toast.error(e);
			});

			if (res) {
				knowledge = res;
				toast.success($i18n.t('Knowledge reset successfully.'));

				// Upload directory
				uploadDirectoryHandler();
			}
		} else {
			uploadDirectoryHandler();
		}
	};

	const addFileHandler = async (fileId) => {
		const updatedKnowledge = await addFileToKnowledgeById(localStorage.token, id, fileId).catch(
			(e) => {
				toast.error(e);
				return null;
			}
		);

		if (updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File added successfully.'));
		} else {
			toast.error($i18n.t('Failed to add file.'));
			knowledge.files = knowledge.files.filter((file) => file.id !== fileId);
		}
	};

	const deleteFileHandler = async (fileId) => {
		const updatedKnowledge = await removeFileFromKnowledgeById(
			localStorage.token,
			id,
			fileId
		).catch((e) => {
			toast.error(e);
		});

		if (updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File removed successfully.'));
		}
	};

	const updateFileContentHandler = async () => {
		const fileId = selectedFile.id;
		const content = selectedFile.data.content;

		const res = updateFileDataContentById(localStorage.token, fileId, content).catch((e) => {
			toast.error(e);
		});

		const updatedKnowledge = await updateFileFromKnowledgeById(
			localStorage.token,
			id,
			fileId
		).catch((e) => {
			toast.error(e);
		});

		if (res && updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File content updated successfully.'));
		}
	};

	const changeDebounceHandler = () => {
		console.log('debounce');
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(async () => {
			if (knowledge.name.trim() === '' || knowledge.description.trim() === '') {
				toast.error($i18n.t('Please fill in all fields.'));
				return;
			}

			const res = await updateKnowledgeById(localStorage.token, id, {
				...knowledge,
				name: knowledge.name,
				description: knowledge.description,
				access_control: knowledge.access_control
			}).catch((e) => {
				toast.error(e);
			});

			if (res) {
				toast.success($i18n.t('Knowledge updated successfully'));
				_knowledge.set(await getKnowledgeBases(localStorage.token));
			}
		}, 1000);
	};

	const handleMediaQuery = async (e) => {
		if (e.matches) {
			largeScreen = true;
		} else {
			largeScreen = false;
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
		if (e.dataTransfer?.types?.includes('Files')) {
			dragged = true;
		} else {
			dragged = false;
		}
	};

	const onDragLeave = () => {
		dragged = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		dragged = false;

		if (e.dataTransfer?.types?.includes('Files')) {
			if (e.dataTransfer?.files) {
				const inputFiles = e.dataTransfer?.files;

				if (inputFiles && inputFiles.length > 0) {
					for (const file of inputFiles) {
						await uploadFileHandler(file);
					}
				} else {
					toast.error($i18n.t(`File not found.`));
				}
			}
		}
	};

	onMount(async () => {
		// listen to resize 1024px
		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		// Select the container element you want to observe
		const container = document.getElementById('collection-container');

		// initialize the minSize based on the container width
		minSize = !largeScreen ? 100 : Math.floor((300 / container.clientWidth) * 100);

		// Create a new ResizeObserver instance
		const resizeObserver = new ResizeObserver((entries) => {
			for (let entry of entries) {
				const width = entry.contentRect.width;
				// calculate the percentage of 300
				const percentage = (300 / width) * 100;
				// set the minSize to the percentage, must be an integer
				minSize = !largeScreen ? 100 : Math.floor(percentage);

				if (showSidepanel) {
					if (pane && pane.isExpanded() && pane.getSize() < minSize) {
						pane.resize(minSize);
					}
				}
			}
		});

		// Start observing the container's size changes
		resizeObserver.observe(container);

		if (pane) {
			pane.expand();
		}

		id = $page.params.id;

		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			toast.error(e);
			return null;
		});

			const ragConfig = await getRAGConfig(localStorage.token).catch(() => null);
		if (ragConfig) {
			webLoaderEngine = ragConfig.web_loader_engine ?? '';
		}

		if (res) {
			knowledge = res;

			// Resume an active crawl job — check the server so any device can pick it up
			try {
				const activeJobs = await listWebCrawlJobs(localStorage.token, id, 'running').catch(() => null);
				const activeJob = activeJobs?.length ? activeJobs[0] : null;

				if (activeJob) {
					crawlJobId = activeJob.job_id;
					crawlUrl = activeJob.url;
					crawlTempItemId = uuidv4();
					lastProcessedPageIndex = 0;
					crawlLoading = true;
					showAddWebCrawlModal = true;
					crawlLogs = ['Reconnected to crawl…'];
					knowledge.files = [
						...(knowledge.files ?? []),
						{ type: 'file', file: '', id: null, url: '', name: crawlUrl,
						  size: 0, status: 'uploading', error: '', itemId: crawlTempItemId }
					];
					localStorage.setItem('activeCrawlJob', JSON.stringify({
						jobId: crawlJobId, knowledgeId: id, url: crawlUrl,
						tempItemId: crawlTempItemId, lastProcessedPageIndex: 0
					}));
					startPolling();
				} else {
					localStorage.removeItem('activeCrawlJob');
				}
			} catch (_) {}
		} else {
			goto('/workspace/knowledge');
		}

		const dropZone = document.querySelector('body');
		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		mediaQuery?.removeEventListener('change', handleMediaQuery);
		const dropZone = document.querySelector('body');
		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});
</script>

{#if dragged}
	<div
		class="fixed {$showSidebar
			? 'left-0 md:left-[260px] md:w-[calc(100%-260px)]'
			: 'left-0'}  w-full h-full flex z-50 touch-none pointer-events-none"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
	>
		<div class="absolute w-full h-full backdrop-blur bg-gray-800/40 flex justify-center">
			<div class="m-auto pt-64 flex flex-col justify-center">
				<div class="max-w-md">
					<AddFilesPlaceholder>
						<div class=" mt-2 text-center text-sm dark:text-gray-200 w-full">
							Drop any files here to add to my documents
						</div>
					</AddFilesPlaceholder>
				</div>
			</div>
		</div>
	</div>
{/if}

<SyncConfirmDialog
	bind:show={showSyncConfirmModal}
	message={$i18n.t(
		'This will reset the knowledge base and sync all files. Do you wish to continue?'
	)}
	on:confirm={() => {
		syncDirectoryHandler();
	}}
/>

<AddTextContentModal
	bind:show={showAddTextContentModal}
	on:submit={(e) => {
		const file = createFileFromText(e.detail.name, e.detail.content);
		uploadFileHandler(file);
	}}
/>

<AddWebUrlModal
	bind:show={showAddWebUrlModal}
	on:submit={(e) => {
		submitScrapeURLHandler(e.detail.url);
	}}
/>

<AddWebUrlModal
	bind:show={showAddWebCrawlModal}
	title="Crawl a website"
	loading={crawlLoading}
	viewOnly={!crawlLoading && crawlLogs.length > 0}
	managedClose={true}
	showLimitInput={true}
	showMaxDepthInput={true}
	showPollIntervalInput={true}
	showMax403Input={true}
	showIncludePathsInput={true}
	showExcludePathsInput={true}
	showRegexOnFullUrlInput={true}
	showCrawlEntireDomainInput={true}
	showBatchSizeInput={true}
	{crawlProgress}
	{crawlLogs}
	on:submit={(e) => {
		submitCrawlURLHandler(e.detail.url, e.detail.limit, e.detail.maxDepth, e.detail.crawlDelay, e.detail.max403s ?? 5, e.detail.includePaths, e.detail.excludePaths, e.detail.regexOnFullUrl, e.detail.crawlEntireDomain, e.detail.batchSize ?? 10);
	}}
	on:cancel={() => {
		cancelCrawlHandler();
	}}
/>

<SavePipelineModal
	bind:show={showPipelineModal}
	title="Set the name of the pipeline"
	mode={pipelineModalMode}
	{pipelineConfigs}
	on:confirm={(e) => {
		if (pipelineModalMode === 'load') {
			loadPipelineHandler(e.detail.fileId)
		} else if (pipelineModalMode === 'save'){
			pipelineName = e.detail.name;
			savePipelineHandler();
		}
	}}
/>

<input
	id="files-input"
	bind:files={inputFiles}
	type="file"
	multiple
	hidden
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			for (const file of inputFiles) {
				await uploadFileHandler(file);
			}

			inputFiles = null;
			const fileInputElement = document.getElementById('files-input');

			if (fileInputElement) {
				fileInputElement.value = '';
			}
		} else {
			toast.error($i18n.t(`File not found.`));
		}
	}}
/>

<div class="flex flex-col w-full translate-y-1" id="collection-container">
	{#if id && knowledge}
		<AccessControlModal
			bind:show={showAccessControlModal}
			bind:accessControl={knowledge.access_control}
			onChange={() => {
				changeDebounceHandler();
			}}
		/>
		<div class="w-full mb-2.5">
			<div class=" flex w-full">
				<div class="flex-1">
					<div class="flex items-center justify-between w-full px-0.5 mb-1">
						<div class="w-full">
							<input
								type="text"
								class="text-left w-full font-semibold text-2xl font-primary bg-transparent outline-none"
								bind:value={knowledge.name}
								placeholder="Knowledge Name"
								on:input={() => {
									changeDebounceHandler();
								}}
							/>
						</div>

						<div class="self-center flex-shrink-0">
							<button
								class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
								type="button"
								on:click={() => {
									showAccessControlModal = true;
								}}
							>
								<LockClosed strokeWidth="2.5" className="size-3.5" />

								<div class="text-sm font-medium flex-shrink-0">
									{$i18n.t('Access')}
								</div>
							</button>
						</div>
					</div>

					<div class="flex w-full px-1">
						<input
							type="text"
							class="text-left text-xs w-full text-gray-500 bg-transparent outline-none"
							bind:value={knowledge.description}
							placeholder="Knowledge Description"
							on:input={() => {
								changeDebounceHandler();
							}}
						/>
					</div>
				</div>
			</div>

			<div class="flex items-center gap-1 px-1 mt-1 relative">
				<button
					class="px-3 py-1 text-sm font-medium rounded-lg transition {activeTab === 'files'
						? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
						: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850'}"
					on:click={() => {
						activeTab = 'files';
					}}
				>
					{$i18n.t('Files')}
				</button>
				<button
					class="px-3 py-1 text-sm font-medium rounded-lg transition {activeTab === 'pipeline'
						? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
						: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850'}"
					on:click={() => {
						activeTab = 'pipeline';
					}}
				>
					{$i18n.t('Pipeline')}
				</button>
				{#if activeTab === 'pipeline'}
				<span class="absolute left-1/2 -translate-x-1/2 text-xs font-medium text-gray-500 dark:text-gray-400 pointer-events-none">
					{pipelineName}
				</span>
				<div class="ml-auto flex items-center gap-1">
					<button
						class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
						on:click={() => {
							pipelineModalMode = 'load'
							showPipelineModal = true;
						}}
					>
						{$i18n.t('Load')}
					</button>
					<button
						class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
						on:click={() => {
							if (pipelineName !== 'Untitled') {
								savePipelineHandler();
							} else {
								pendingRun = false;
								pipelineModalMode = 'save';
								showPipelineModal = true;
							}
						}}
					>
						{$i18n.t('Save')}
					</button>
					<button
						class="bg-emerald-600 hover:bg-emerald-700 text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
						on:click={runPipelineHandler}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3">
							<path d="M3 3.732a1.5 1.5 0 0 1 2.305-1.265l6.706 4.267a1.5 1.5 0 0 1 0 2.531l-6.706 4.268A1.5 1.5 0 0 1 3 12.267V3.732Z" />
						</svg>
						<span class="text-xs">
							{$i18n.t('Run')}
						</span>
					</button>
				</div>
				{/if}
			</div>
		</div>

		{#if activeTab === 'files'}
		<div class="flex flex-row flex-1 h-full max-h-full pb-2.5 gap-3">
			{#if largeScreen}
				<div class="flex-1 flex justify-start w-full h-full max-h-full">
					{#if selectedFile}
						<div class=" flex flex-col w-full h-full max-h-full">
							<div class="flex-shrink-0 mb-2 flex items-center">
								{#if !showSidepanel}
									<div class="-translate-x-2">
										<button
											class="w-full text-left text-sm p-1.5 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850"
											on:click={() => {
												pane.expand();
											}}
										>
											<ChevronLeft strokeWidth="2.5" />
										</button>
									</div>
								{/if}

								<div class=" flex-1 text-xl font-medium">
									<a
										class="hover:text-gray-500 hover:dark:text-gray-100 hover:underline flex-grow line-clamp-1"
										href={selectedFile.id ? `/api/v1/files/${selectedFile.id}/content` : '#'}
										target="_blank"
									>
										{selectedFile?.meta?.name}
									</a>
								</div>

								<div>
									<button
										class="self-center w-fit text-sm py-1 px-2.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
										on:click={() => {
											updateFileContentHandler();
										}}
									>
										{$i18n.t('Save')}
									</button>
								</div>
							</div>

							<div
								class=" flex-1 w-full h-full max-h-full text-sm bg-transparent outline-none overflow-y-auto scrollbar-hidden"
							>
								{#key selectedFile.id}
									<RichTextInput
										className="input-prose-sm"
										bind:value={selectedFile.data.content}
										placeholder={$i18n.t('Add content here')}
										preserveBreaks={true}
									/>
								{/key}
							</div>
						</div>
					{:else}
						<div class="h-full flex w-full">
							<div class="m-auto text-xs text-center text-gray-200 dark:text-gray-700">
								{$i18n.t('Drag and drop a file to upload or select a file to view')}
							</div>
						</div>
					{/if}
				</div>
			{:else if !largeScreen && selectedFileId !== null}
				<Drawer
					className="h-full"
					show={selectedFileId !== null}
					on:close={() => {
						selectedFileId = null;
					}}
				>
					<div class="flex flex-col justify-start h-full max-h-full p-2">
						<div class=" flex flex-col w-full h-full max-h-full">
							<div class="flex-shrink-0 mt-1 mb-2 flex items-center">
								<div class="mr-2">
									<button
										class="w-full text-left text-sm p-1.5 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850"
										on:click={() => {
											selectedFileId = null;
										}}
									>
										<ChevronLeft strokeWidth="2.5" />
									</button>
								</div>
								<div class=" flex-1 text-xl line-clamp-1">
									{selectedFile?.meta?.name}
								</div>

								<div>
									<button
										class="self-center w-fit text-sm py-1 px-2.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
										on:click={() => {
											updateFileContentHandler();
										}}
									>
										{$i18n.t('Save')}
									</button>
								</div>
							</div>

							<div
								class=" flex-1 w-full h-full max-h-full py-2.5 px-3.5 rounded-lg text-sm bg-transparent overflow-y-auto scrollbar-hidden"
							>
								{#key selectedFile.id}
									<RichTextInput
										className="input-prose-sm"
										bind:value={selectedFile.data.content}
										placeholder={$i18n.t('Add content here')}
										preserveBreaks={true}
									/>
								{/key}
							</div>
						</div>
					</div>
				</Drawer>
			{/if}

			<div
				class="{largeScreen ? 'flex-shrink-0 w-72 max-w-72' : 'flex-1'}
			flex
			py-2
			rounded-2xl
			border
			border-gray-50
			h-full
			dark:border-gray-850"
			>
				<div class=" flex flex-col w-full space-x-2 rounded-lg h-full">
					<div class="w-full h-full flex flex-col">
						<div class=" px-3">
							<div class="flex mb-0.5">
								<div class=" self-center ml-1 mr-3">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<input
									class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
									bind:value={query}
									placeholder={$i18n.t('Search Collection')}
									on:focus={() => {
										selectedFileId = null;
									}}
								/>

								<div>
									<AddContentMenu
										{webLoaderEngine}
										on:upload={(e) => {
											if (e.detail.type === 'directory') {
												uploadDirectoryHandler();
											} else if (e.detail.type === 'text') {
												showAddTextContentModal = true;
											} else if (e.detail.type === 'scrape'){
												scrapeURLHandler();
											} else if (e.detail.type === 'crawl') {
												crawlLogs = [];
												crawlProgress = null;
												showAddWebCrawlModal = true;
											} else {
												document.getElementById('files-input').click();
											}
										}}
										on:sync={(e) => {
											showSyncConfirmModal = true;
										}}
									/>
								</div>
							</div>
						</div>

						<div class="px-4 py-1 text-xs text-gray-500">
							{(knowledge?.files ?? []).length} {(knowledge?.files ?? []).length === 1 ? $i18n.t('document') : $i18n.t('documents')}
							{#if query && filteredItems.length !== (knowledge?.files ?? []).length}
								<span>({filteredItems.length} {$i18n.t('matching')})</span>
							{/if}
						</div>

						{#if filteredItems.length > 0}
							<div class=" flex overflow-y-auto h-full w-full scrollbar-hidden text-xs">
								<Files
									small
									files={filteredItems}
									{selectedFileId}
									crawlItemId={null}
									on:click={(e) => {
										if (e.detail === null && crawlLogs.length > 0) {
											showAddWebCrawlModal = true;
										} else {
											selectedFileId = selectedFileId === e.detail ? null : e.detail;
										}
									}}
									on:delete={(e) => {
										console.log(e.detail);

										selectedFileId = null;
										deleteFileHandler(e.detail);
									}}
								/>
							</div>
						{:else}
							<div class="my-3 flex flex-col justify-center text-center text-gray-500 text-xs">
								<div>
									{$i18n.t('No content found')}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
		{:else if activeTab === 'pipeline'}
		<div style="height: calc(100vh - 190px);">
			<PipelineCanvas nodes={pipelineNodes} connections={pipelineConnections} on:configchange={(e) => { pipelineNodes = e.detail.nodes; e.detail.nodes; pipelineConnections = e.detail.connections; }}/>
		</div>
		{/if}
	{:else}
		<Spinner />
	{/if}
</div>
