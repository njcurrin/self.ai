import { WEBUI_BASE_URL } from '$lib/constants';

const BASE = `${WEBUI_BASE_URL}/api/windows`;

export type WindowSlot = {
	id?: string;
	job_type: string;
	max_concurrent: number;
	min_remaining_minutes: number;
};

export type JobWindow = {
	id: string;
	name: string;
	notes?: string;
	start_at: number;
	end_at: number;
	preferred_job_type: string;
	enabled: boolean;
	created_at: number;
	updated_at: number;
	slots: WindowSlot[];
	status: 'upcoming' | 'active' | 'completed';
};

export type WindowForm = {
	id?: string;
	name: string;
	notes?: string;
	start_at: number;
	end_at: number;
	preferred_job_type: string;
	enabled: boolean;
	slots: WindowSlot[];
};

async function windowsFetch<T>(
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

export const listWindows = (token: string) => windowsFetch<JobWindow[]>(token, '');

export const createWindow = (token: string, form: WindowForm) =>
	windowsFetch<JobWindow>(token, '', {
		method: 'POST',
		body: JSON.stringify(form)
	});

export const getWindow = (token: string, id: string) =>
	windowsFetch<JobWindow>(token, `/${id}`);

export const updateWindow = (token: string, id: string, form: WindowForm) =>
	windowsFetch<JobWindow>(token, `/${id}`, {
		method: 'PUT',
		body: JSON.stringify(form)
	});

export const deleteWindow = (token: string, id: string) =>
	windowsFetch<{ message: string }>(token, `/${id}`, { method: 'DELETE' });
