import { WEBUI_API_BASE_URL } from '$lib/constants';

const BASE = `${WEBUI_API_BASE_URL}/evaluations`;

export type EvalJob = {
	id: string;
	user_id: string;
	eval_type: 'bigcode' | 'lm-eval';
	benchmark: string;
	model_id: string;
	status: 'pending' | 'scheduled' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
	scheduled_for: number | null;
	error_message: string | null;
	meta: Record<string, unknown> | null;
	created_at: number;
	updated_at: number;
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

export const getEvalJobs = (token: string): Promise<EvalJob[]> =>
	apiFetch(token, '/jobs');

export const createEvalJob = (
	token: string,
	benchmark: string,
	modelId: string,
	evalType: 'bigcode' | 'lm-eval' = 'bigcode',
	totalSamples?: number,
	dryRun: boolean = false
): Promise<EvalJob> =>
	apiFetch(token, '/jobs/create', {
		method: 'POST',
		body: JSON.stringify({
			benchmark,
			model_id: modelId,
			eval_type: evalType,
			total_samples: totalSamples,
			dry_run: dryRun
		})
	});

export const cancelEvalJob = (token: string, id: string): Promise<EvalJob> =>
	apiFetch(token, `/jobs/${id}/cancel`, { method: 'POST' });

export const approveEvalJob = (token: string, id: string): Promise<EvalJob> =>
	apiFetch(token, `/jobs/${id}/approve`, { method: 'POST' });

export const rejectEvalJob = (token: string, id: string): Promise<EvalJob> =>
	apiFetch(token, `/jobs/${id}/reject`, { method: 'POST' });

export const deleteEvalJob = (token: string, id: string): Promise<boolean> =>
	apiFetch(token, `/jobs/${id}/delete`, { method: 'DELETE' });

export type LiveEvalEvent = {
	index: number;
	total: number;
	// bigcode format
	task_id?: string;
	prompt?: string;
	completions?: string[];
	// lm-eval format
	task_name?: string;
	doc_id?: number;
	target?: string;
	thinking?: string;
	response?: string;
	scored_response?: string;
	metrics?: Record<string, unknown>;
	timestamp: string;
};

export const getEvalJobEvents = (
	token: string,
	jobId: string
): Promise<{ events: LiveEvalEvent[]; status: string; job: Record<string, unknown> }> =>
	apiFetch(token, `/jobs/${jobId}/events`);

export function streamEvalJobLive(
	token: string,
	jobId: string,
	onEvent: (event: LiveEvalEvent) => void,
	onDone: (status: string) => void,
	onError: (error: string) => void
): () => void {
	const controller = new AbortController();

	(async () => {
		try {
			const res = await fetch(`${BASE}/jobs/${jobId}/live`, {
				headers: { Authorization: `Bearer ${token}` },
				signal: controller.signal
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({ detail: res.statusText }));
				onError(err?.detail ?? 'Stream failed');
				return;
			}

			const reader = res.body?.getReader();
			if (!reader) {
				onError('No response body');
				return;
			}

			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() ?? '';

				let eventType = 'message';
				for (const line of lines) {
					if (line.startsWith('event: ')) {
						eventType = line.slice(7).trim();
					} else if (line.startsWith('data: ')) {
						const data = line.slice(6);
						try {
							const parsed = JSON.parse(data);
							if (eventType === 'done') {
								onDone(parsed.status);
								return;
							} else if (eventType === 'error') {
								onError(parsed.error);
								return;
							} else {
								onEvent(parsed as LiveEvalEvent);
							}
						} catch {
							// skip malformed JSON
						}
						eventType = 'message';
					}
				}
			}
		} catch (e: unknown) {
			if (e instanceof DOMException && e.name === 'AbortError') return;
			onError(e instanceof Error ? e.message : 'Stream error');
		}
	})();

	return () => controller.abort();
}
