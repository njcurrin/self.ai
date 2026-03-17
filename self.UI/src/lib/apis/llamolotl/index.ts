import { LLAMOLOTL_API_BASE_URL } from '$lib/constants';

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
