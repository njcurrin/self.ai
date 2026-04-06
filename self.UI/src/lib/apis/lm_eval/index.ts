import { LM_EVAL_API_BASE_URL } from '$lib/constants';

type LmEvalConfig = {
	ENABLE_LM_EVAL_API: boolean;
	LM_EVAL_BASE_URLS: string[];
};

export const getLmEvalConfig = async (token: string = ''): Promise<LmEvalConfig> => {
	const res = await fetch(`${LM_EVAL_API_BASE_URL}/config`, {
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		}
	}).then(async (r) => {
		if (!r.ok) throw await r.json();
		return r.json();
	});
	return res;
};

export const updateLmEvalConfig = async (
	token: string = '',
	config: LmEvalConfig
): Promise<LmEvalConfig> => {
	const res = await fetch(`${LM_EVAL_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(config)
	}).then(async (r) => {
		if (!r.ok) throw await r.json();
		return r.json();
	});
	return res;
};

export const verifyLmEvalConnection = async (
	token: string = '',
	url: string = ''
): Promise<any> => {
	const res = await fetch(`${LM_EVAL_API_BASE_URL}/verify`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({ url })
	}).then(async (r) => {
		if (!r.ok) throw await r.json();
		return r.json();
	});
	return res;
};
