import { LLAMOLOTL_API_BASE_URL } from '$lib/constants';

export type TrainingConfigSummary = {
	name: string;
	path: string;
	size: number;
	modified: number;
};

export type TrainingConfigDetail = {
	name: string;
	content: string;
};

export type TrainingJobMetric = Record<string, any>;

export type TrainingJob = {
	job_id: string;
	status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
	config_path: string;
	output_dir: string;
	pid?: number | null;
	created_at: string;
	started_at?: string | null;
	finished_at?: string | null;
	exit_code?: number | null;
	log_file: string;
	metrics: TrainingJobMetric[];
	error_message?: string | null;
	approved?: boolean;
};

export type TrainingOutput = {
	name: string;
	path: string;
	has_model: boolean;
	has_config: boolean;
	size_bytes: number;
	modified: number;
};

export type TrainingStatus = {
	ENABLE_LLAMOLOTL_API: boolean;
	LLAMOLOTL_BASE_URLS: string[];
};

const getTrainingUrl = (
	path: string,
	urlIdx: number | null = null,
	params: Record<string, string | number> = {}
) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== null) {
		searchParams.set('url_idx', `${urlIdx}`);
	}
	for (const [key, value] of Object.entries(params)) {
		searchParams.set(key, `${value}`);
	}
	const query = searchParams.toString();
	return `${LLAMOLOTL_API_BASE_URL}${path}${query ? `?${query}` : ''}`;
};

export const verifyLlamolotlConnection = async (
	token: string = '',
	url: string = '',
	key: string = ''
) => {
	let error = null;

	const res = await fetch(`${LLAMOLOTL_API_BASE_URL}/verify`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			url,
			key
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `Llamolotl: ${err?.error?.message ?? err?.detail ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getLlamolotlConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${LLAMOLOTL_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type LlamolotlConfig = {
	ENABLE_LLAMOLOTL_API: boolean;
	LLAMOLOTL_BASE_URLS: string[];
	LLAMOLOTL_API_CONFIGS: object;
};

export const updateLlamolotlConfig = async (token: string = '', config: LlamolotlConfig) => {
	let error = null;

	const res = await fetch(`${LLAMOLOTL_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			...config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getLlamolotlTrainingStatus = async (token: string = '') => {
	let error = null;

	const res = await fetch(getTrainingUrl('/api/status'), {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res as TrainingStatus;
};

export const getLlamolotlModels = async (token: string = '', urlIdx: null | number = null) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/models${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return (res?.data ?? []).sort((a: any, b: any) => {
		return a.name.localeCompare(b.name);
	});
};

export type ModelInspectResult = {
	type: 'gguf' | 'safetensors';
	files: { name: string; size: number }[];
	total_size: number;
};

export const inspectLlamolotlModel = async (
	token: string,
	name: string,
	urlIdx: number | null = null
): Promise<ModelInspectResult> => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/inspect${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ name })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as ModelInspectResult;
};

export const pullLlamolotlModel = async (
	token: string,
	name: string,
	filename: string | null = null,
	urlIdx: number | null = null
) => {
	let error = null;
	const controller = new AbortController();

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/pull${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			signal: controller.signal,
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				name,
				...(filename && { filename })
			})
		}
	).catch((err) => {
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const cancelLlamolotlModelPull = async (
	token: string,
	name: string,
	filename: string | null = null,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/pull/cancel${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				name,
				...(filename && { filename })
			})
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteLlamolotlModel = async (
	token: string,
	name: string,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/delete${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ name })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAvailableLlamolotlModels = async (
	token: string,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/available-models${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? [];
};

export const registerLlamolotlModel = async (
	token: string,
	name: string,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/register${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ name })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getLlamolotlModelStatus = async (
	token: string,
	urlIdx: number | null = null
): Promise<Record<string, string>> => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/model-status${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.status ?? {};
};

export const loadLlamolotlModel = async (
	token: string,
	model: string,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/models/load${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ model })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const unloadLlamolotlModel = async (
	token: string,
	model: string,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/models/unload${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ model })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const unloadAllLlamolotlModels = async (
	token: string,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/models/unload-all${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ─── Model Lineage Types ────────────────────────────────────────────

export type BakeInfo = {
	base_model: string;
	adapters: { path: string; weight: number }[];
	outtype: string;
	quant_type?: string | null;
	baked_at: string;
};

export type AvailableLora = {
	file: string;
	base_model: string | null;
	training_output: string | null;
	size: number;
	modified: number;
	converting?: boolean;
};

export type LoraEntry = {
	file: string;
	scale: number;
};

export type ModelLineage = {
	hf_repo?: string;
	quant?: string;
	source_type?: string;
	trainable?: boolean;
	pulled_at?: string;
	bake_info?: BakeInfo;
	active_loras?: LoraEntry[];
};

// ─── Bake Pipeline ──────────────────────────────────────────────────

export type BakeModelParams = {
	base_model: string;
	adapters: { path: string; weight: number }[];
	output_name: string;
	outtype?: string;
	quant_type?: string | null;
};

export const bakeLlamolotlModel = async (
	token: string,
	params: BakeModelParams,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/pipeline/bake${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(params)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ─── LoRA Management ────────────────────────────────────────────────

export const getAvailableLlamolotlLoras = async (
	token: string,
	urlIdx: number | null = null
): Promise<AvailableLora[]> => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/loras/available${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return (res ?? []) as AvailableLora[];
};

export const applyLlamolotlLoras = async (
	token: string,
	modelId: string,
	loras: LoraEntry[],
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/system/apply-loras${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ model_id: modelId, loras })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getActiveLlamolotlLoras = async (
	token: string,
	urlIdx: number | null = null
): Promise<LoraEntry[]> => {
	let error = null;

	const res = await fetch(
		`${LLAMOLOTL_API_BASE_URL}/api/system/active-loras${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return (res ?? []) as LoraEntry[];
};

// ─── Training ───────────────────────────────────────────────────────

export const getLlamolotlTrainingConfigs = async (
	token: string,
	urlIdx: number | null = null
): Promise<TrainingConfigSummary[]> => {
	let error = null;

	const res = await fetch(getTrainingUrl('/api/configs', urlIdx), {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return (res ?? []) as TrainingConfigSummary[];
};

export const getLlamolotlTrainingConfig = async (
	token: string,
	name: string,
	urlIdx: number | null = null
): Promise<TrainingConfigDetail> => {
	let error = null;

	const res = await fetch(getTrainingUrl(`/api/configs/${encodeURIComponent(name)}`, urlIdx), {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res as TrainingConfigDetail;
};

export const getLlamolotlTrainingJobs = async (
	token: string,
	urlIdx: number | null = null
): Promise<TrainingJob[]> => {
	let error = null;

	const res = await fetch(getTrainingUrl('/api/jobs', urlIdx), {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return (res ?? []) as TrainingJob[];
};

export const getLlamolotlTrainingJob = async (
	token: string,
	jobId: string,
	urlIdx: number | null = null
): Promise<TrainingJob> => {
	let error = null;

	const res = await fetch(getTrainingUrl(`/api/jobs/${encodeURIComponent(jobId)}`, urlIdx), {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res as TrainingJob;
};

export const createLlamolotlTrainingJob = async (
	token: string,
	configPath: string,
	outputDir: string,
	urlIdx: number | null = null,
	baseModel: string | null = null
): Promise<TrainingJob> => {
	let error = null;

	const res = await fetch(getTrainingUrl('/api/jobs', urlIdx), {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			config_path: configPath,
			output_dir: outputDir,
			...(baseModel && { base_model: baseModel })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as TrainingJob;
};

export const cancelLlamolotlTrainingJob = async (
	token: string,
	jobId: string,
	urlIdx: number | null = null
) => {
	let error = null;

	const res = await fetch(getTrainingUrl(`/api/jobs/${encodeURIComponent(jobId)}`, urlIdx), {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const approveLlamolotlTrainingJob = async (
	token: string,
	jobId: string,
	urlIdx: number | null = null
): Promise<TrainingJob> => {
	let error = null;

	const res = await fetch(
		getTrainingUrl(`/api/jobs/${encodeURIComponent(jobId)}/approve`, urlIdx),
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as TrainingJob;
};

export const getLlamolotlTrainingJobLogs = async (
	token: string,
	jobId: string,
	tail: number = 200,
	urlIdx: number | null = null
): Promise<string[]> => {
	let error = null;

	const res = await fetch(
		getTrainingUrl(`/api/jobs/${encodeURIComponent(jobId)}/logs`, urlIdx, { tail }),
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.lines ?? [];
};

export const getLlamolotlTrainingOutputs = async (
	token: string,
	urlIdx: number | null = null
): Promise<TrainingOutput[]> => {
	let error = null;

	const res = await fetch(getTrainingUrl('/api/outputs', urlIdx), {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return (res ?? []) as TrainingOutput[];
};
