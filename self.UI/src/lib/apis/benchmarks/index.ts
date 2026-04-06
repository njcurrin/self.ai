import { WEBUI_BASE_URL } from '$lib/constants';

const BASE = `${WEBUI_BASE_URL}/api/benchmarks`;

export type BenchmarkConfig = {
	id: string;
	benchmark: string;
	eval_type: string;
	max_duration_minutes: number;
	notes?: string;
	created_at: number;
	updated_at: number;
};

export type BenchmarkConfigUpdate = {
	max_duration_minutes: number;
	notes?: string;
};

async function benchmarksFetch<T>(
	token: string,
	path: string,
	options: RequestInit = {}
): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
			...((options.headers as Record<string, string>) ?? {})
		}
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw err?.detail ?? 'Request failed';
	}
	return res.json();
}

export const listBenchmarks = (token: string) => benchmarksFetch<BenchmarkConfig[]>(token, '');

export const updateBenchmark = (token: string, id: string, form: BenchmarkConfigUpdate) =>
	benchmarksFetch<BenchmarkConfig>(token, `/${id}`, {
		method: 'PUT',
		body: JSON.stringify(form)
	});
