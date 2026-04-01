import { WEBUI_API_BASE_URL } from '$lib/constants';

/**
 * Unified schedule API — fetches both training and eval jobs,
 * and provides schedule/unschedule actions for either type.
 */

export type ScheduledJobType = 'training' | 'eval';

export type ScheduledJob = {
	id: string;
	type: ScheduledJobType;
	status: string;
	scheduled_for: number | null;
	model_id: string;
	created_at: number;
	updated_at: number;
	user: { id: string; name: string; email: string } | null;
	// Training-specific
	course_name?: string;
	course_id?: string;
	// Eval-specific
	eval_type?: string;
	benchmark?: string;
	error_message?: string | null;
};

async function apiFetch<T>(
	token: string,
	url: string,
	options: RequestInit = {}
): Promise<T> {
	const res = await fetch(url, {
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

/** Fetch all training and eval jobs, merge into a unified list. */
export async function getAllScheduledJobs(token: string): Promise<ScheduledJob[]> {
	const [trainingJobs, evalJobs] = await Promise.all([
		apiFetch<any[]>(token, `${WEBUI_API_BASE_URL}/training/jobs`),
		apiFetch<any[]>(token, `${WEBUI_API_BASE_URL}/evaluations/jobs`)
	]);

	const jobs: ScheduledJob[] = [];

	for (const j of trainingJobs) {
		jobs.push({
			id: j.id,
			type: 'training',
			status: j.status,
			scheduled_for: j.scheduled_for ?? null,
			model_id: j.model_id,
			created_at: j.created_at,
			updated_at: j.updated_at,
			user: j.user ?? null,
			course_name: j.course?.name ?? undefined,
			course_id: j.course_id,
			error_message: j.error_message ?? null
		});
	}

	for (const j of evalJobs) {
		jobs.push({
			id: j.id,
			type: 'eval',
			status: j.status,
			scheduled_for: j.scheduled_for ?? null,
			model_id: j.model_id,
			created_at: j.created_at,
			updated_at: j.updated_at,
			user: j.user ?? null,
			eval_type: j.eval_type,
			benchmark: j.benchmark,
			error_message: j.error_message ?? null
		});
	}

	return jobs;
}

/** Schedule a job for a specific time. */
export async function scheduleJob(
	token: string,
	type: ScheduledJobType,
	id: string,
	scheduledFor: number
): Promise<any> {
	const base =
		type === 'training'
			? `${WEBUI_API_BASE_URL}/training`
			: `${WEBUI_API_BASE_URL}/evaluations`;
	return apiFetch(token, `${base}/jobs/${id}/schedule`, {
		method: 'POST',
		body: JSON.stringify({ scheduled_for: scheduledFor })
	});
}

/** Remove the schedule from a job. */
export async function unscheduleJob(
	token: string,
	type: ScheduledJobType,
	id: string
): Promise<any> {
	const base =
		type === 'training'
			? `${WEBUI_API_BASE_URL}/training`
			: `${WEBUI_API_BASE_URL}/evaluations`;
	return apiFetch(token, `${base}/jobs/${id}/unschedule`, { method: 'POST' });
}

/** Approve a job immediately (bypass schedule). */
export async function approveJobNow(
	token: string,
	type: ScheduledJobType,
	id: string
): Promise<any> {
	const base =
		type === 'training'
			? `${WEBUI_API_BASE_URL}/training`
			: `${WEBUI_API_BASE_URL}/evaluations`;
	return apiFetch(token, `${base}/jobs/${id}/approve`, { method: 'POST' });
}

/** Cancel a job. */
export async function cancelScheduledJob(
	token: string,
	type: ScheduledJobType,
	id: string
): Promise<any> {
	const base =
		type === 'training'
			? `${WEBUI_API_BASE_URL}/training`
			: `${WEBUI_API_BASE_URL}/evaluations`;
	return apiFetch(token, `${base}/jobs/${id}/cancel`, { method: 'POST' });
}
