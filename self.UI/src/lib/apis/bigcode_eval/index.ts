import { BIGCODE_EVAL_API_BASE_URL } from '$lib/constants';

type BigcodeEvalConfig = {
	ENABLE_BIGCODE_EVAL_API: boolean;
	BIGCODE_EVAL_BASE_URLS: string[];
};

export const getBigcodeEvalConfig = async (token: string = ''): Promise<BigcodeEvalConfig> => {
	const res = await fetch(`${BIGCODE_EVAL_API_BASE_URL}/config`, {
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

export const updateBigcodeEvalConfig = async (
	token: string = '',
	config: BigcodeEvalConfig
): Promise<BigcodeEvalConfig> => {
	const res = await fetch(`${BIGCODE_EVAL_API_BASE_URL}/config/update`, {
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

export const verifyBigcodeEvalConnection = async (
	token: string = '',
	url: string = ''
): Promise<any> => {
	const res = await fetch(`${BIGCODE_EVAL_API_BASE_URL}/verify`, {
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
