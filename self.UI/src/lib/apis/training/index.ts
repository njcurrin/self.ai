import { WEBUI_API_BASE_URL } from '$lib/constants';

const BASE = `${WEBUI_API_BASE_URL}/training`;

export type TrainingCourse = {
	id: string;
	user_id: string;
	name: string;
	description: string;
	data: {
		base_config?: string;
		knowledge_ids?: string[];
		dataset_ids?: string[];
		prompt_ids?: string[];
		advanced_config?: Record<string, unknown>;
	} | null;
	meta: Record<string, unknown> | null;
	access_control: {
		read?: { group_ids: string[]; user_ids: string[] };
		write?: { group_ids: string[]; user_ids: string[] };
	} | null;
	created_at: number;
	updated_at: number;
	user?: { id: string; name: string; email: string } | null;
};

export type TrainingCourseForm = {
	name: string;
	description: string;
	data?: TrainingCourse['data'];
	meta?: Record<string, unknown> | null;
	access_control?: TrainingCourse['access_control'];
};

export type TrainingJob = {
	id: string;
	course_id: string;
	user_id: string;
	model_id: string;
	status: 'pending' | 'scheduled' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
	scheduled_for: number | null;
	llamolotl_job_id: string | null;
	llamolotl_url_idx: number | null;
	error_message: string | null;
	meta: Record<string, unknown> | null;
	created_at: number;
	updated_at: number;
	course: TrainingCourse | null;
	user: { id: string; name: string; email: string } | null;
};

async function apiFetch<T>(
	token: string,
	path: string,
	options: RequestInit = {}
): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
			...(options.headers ?? {})
		}
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw err?.detail ?? 'Request failed';
	}
	return res.json();
}

// ─── Courses ────────────────────────────────────────────────────────────────

export const getCourses = (token: string): Promise<TrainingCourse[]> =>
	apiFetch(token, '/courses');

export const getCourse = (token: string, id: string): Promise<TrainingCourse> =>
	apiFetch(token, `/courses/${id}`);

export const createCourse = (
	token: string,
	form: TrainingCourseForm
): Promise<TrainingCourse> =>
	apiFetch(token, '/courses/create', { method: 'POST', body: JSON.stringify(form) });

export const updateCourse = (
	token: string,
	id: string,
	form: TrainingCourseForm
): Promise<TrainingCourse> =>
	apiFetch(token, `/courses/${id}/update`, { method: 'POST', body: JSON.stringify(form) });

export const deleteCourse = (token: string, id: string): Promise<boolean> =>
	apiFetch(token, `/courses/${id}/delete`, { method: 'DELETE' });

// ─── Jobs ────────────────────────────────────────────────────────────────────

export const getJobs = (token: string): Promise<TrainingJob[]> =>
	apiFetch(token, '/jobs');

export const getJob = (token: string, id: string): Promise<TrainingJob> =>
	apiFetch(token, `/jobs/${id}`);

export const createJob = (
	token: string,
	courseId: string,
	modelId: string
): Promise<TrainingJob> =>
	apiFetch(token, '/jobs/create', {
		method: 'POST',
		body: JSON.stringify({ course_id: courseId, model_id: modelId })
	});

export const cancelJob = (token: string, id: string): Promise<TrainingJob> =>
	apiFetch(token, `/jobs/${id}/cancel`, { method: 'POST' });

export const approveJob = (token: string, id: string): Promise<TrainingJob> =>
	apiFetch(token, `/jobs/${id}/approve`, { method: 'POST' });

export const rejectJob = (token: string, id: string): Promise<TrainingJob> =>
	apiFetch(token, `/jobs/${id}/reject`, { method: 'POST' });

export const deleteJob = (token: string, id: string): Promise<boolean> =>
	apiFetch(token, `/jobs/${id}/delete`, { method: 'DELETE' });

export const syncJobStatus = (token: string, id: string): Promise<TrainingJob> =>
	apiFetch(token, `/jobs/${id}/sync`, { method: 'POST' });
