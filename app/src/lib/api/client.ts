import { PUBLIC_API_URL } from '$env/static/public';
import type { AutomationListOut, AutomationOut, GoalRequest, HealthStatus, ResultOut, RunOut } from './types';
export type { ResultOut };

export interface TemplateOut {
	id: string;
	name: string;
	description: string | null;
	format: string;
	schema_definition: Record<string, any>;
	is_default: boolean;
	created_at: string;
	updated_at: string;
}
import { createSSEConnection, type SSEOptions, type SSEConnection } from './sse';

export { createSSEConnection, type SSEOptions, type SSEConnection };

interface CacheEntry<T> {
	data: T;
	expiresAt: number;
}

export class ApiClient {
	private baseUrl: string;
	private cache = new Map<string, CacheEntry<any>>();

	constructor(baseUrl: string = PUBLIC_API_URL || 'http://localhost:8000/api/v1') {
		this.baseUrl = baseUrl.replace(/\/+$/, '');
	}

	private getCached<T>(key: string): T | null {
		const entry = this.cache.get(key);
		if (entry && Date.now() < entry.expiresAt) {
			return entry.data;
		}
		if (entry) this.cache.delete(key);
		return null;
	}

	private setCache<T>(key: string, data: T, ttlMs: number = 30000): void {
		this.cache.set(key, { data, expiresAt: Date.now() + ttlMs });
	}

	public invalidateCache(pattern?: string): void {
		if (!pattern) {
			this.cache.clear();
			return;
		}
		for (const key of this.cache.keys()) {
			if (key.includes(pattern)) {
				this.cache.delete(key);
			}
		}
	}

	private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
		const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
		const url = `${this.baseUrl}${cleanEndpoint}`;
		const headers: HeadersInit = {
			'Content-Type': 'application/json',
			Accept: 'application/json',
			...options.headers
		};

		const response = await fetch(url, { ...options, headers });
		if (!response.ok) {
			let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
			try {
				const errorJson = await response.json();
				if (errorJson.detail) {
					errorMessage =
						typeof errorJson.detail === 'string'
							? errorJson.detail
							: JSON.stringify(errorJson.detail);
				}
			} catch {}
			throw new Error(errorMessage);
		}
		const text = await response.text();
		return text ? JSON.parse(text) : ({} as T);
	}

	async getHealth(): Promise<HealthStatus> {
		return this.request<HealthStatus>('/health');
	}
	async listAutomations(useCache: boolean = true): Promise<AutomationListOut> {
		const key = 'automations:list';
		if (useCache) {
			const cached = this.getCached<AutomationListOut>(key);
			if (cached) return cached;
		}
		const res = await this.request<AutomationListOut>('/automations');
		this.setCache(key, res, 15000);
		return res;
	}
	async getAutomation(id: string): Promise<AutomationOut> {
		return this.request<AutomationOut>(`/automations/${id}`);
	}
	async createAutomation(payload: GoalRequest): Promise<AutomationOut> {
		this.invalidateCache('automations');
		return this.request<AutomationOut>('/automations', {
			method: 'POST',
			body: JSON.stringify(payload)
		});
	}
	streamGoalPlan(
		goal: string,
		onReasoning: (data: { stage: string; message: string }) => void,
		onPlan: (plan: any) => void,
		onComplete: (auto: AutomationOut) => void,
		onError?: (err: any) => void
	): () => void {
		const url = `${this.baseUrl}/automations/plan/stream?goal=${encodeURIComponent(goal)}`;
		const conn = createSSEConnection({
			url,
			onEvent: {
				reasoning: (data) => onReasoning(data),
				plan: (data) => onPlan(data),
				complete: (data) => {
					this.invalidateCache('automations');
					onComplete(data);
					conn.close();
				},
				error: (err) => {
					if (onError) onError(err);
					conn.close();
				}
			},
			onError: (err) => {
				if (onError) onError(err);
			}
		});

		return () => conn.close();
	}
	async deleteAutomation(id: string): Promise<{ message: string }> {
		this.invalidateCache('automations');
		return this.request<{ message: string }>(`/automations/${id}`, { method: 'DELETE' });
	}
	async runAutomation(id: string): Promise<RunOut> {
		this.invalidateCache('automations');
		return this.request<RunOut>(`/automations/${id}/run`, { method: 'POST' });
	}
	async retryRun(runId: string): Promise<RunOut> {
		this.invalidateCache('automations');
		return this.request<RunOut>(`/runs/${runId}/retry`, { method: 'POST' });
	}
	async getRun(runId: string): Promise<RunOut> {
		return this.request<RunOut>(`/runs/${runId}`);
	}
	getRunStreamUrl(runId: string): string {
		return `${this.baseUrl}/runs/${runId}/stream`;
	}
	streamRun(
		runId: string,
		onUpdate: (run: RunOut) => void,
		onError?: (err: any) => void
	): () => void {
		const url = this.getRunStreamUrl(runId);
		const conn = createSSEConnection<RunOut>({
			url,
			onEvent: {
				snapshot: (data) => onUpdate(data),
				update: (data) => onUpdate(data),
				complete: (data) => {
					this.invalidateCache('automations');
					onUpdate(data);
					conn.close();
				}
			},
			onError: (err) => {
				if (onError) onError(err);
			}
		});

		return () => {
			conn.close();
		};
	}
	streamRunResults(
		runId: string,
		onRecord: (record: ResultOut) => void,
		onComplete?: (status: any) => void,
		onError?: (err: any) => void
	): () => void {
		const url = `${this.baseUrl}/runs/${runId}/results/stream`;
		const conn = createSSEConnection({
			url,
			onEvent: {
				record: (data) => onRecord(data),
				complete: (data) => {
					onComplete?.(data);
					conn.close();
				}
			},
			onError: (err) => {
				if (onError) onError(err);
			}
		});

		return () => conn.close();
	}
	async listAutomationRuns(automationId: string): Promise<RunOut[]> {
		return this.request<RunOut[]>(`/automations/${automationId}/runs`);
	}
	async getWorkflowTopology(useCache: boolean = true): Promise<any[]> {
		const key = 'workflows:topology';
		if (useCache) {
			const cached = this.getCached<any[]>(key);
			if (cached) return cached;
		}
		const res = await this.request<any[]>('/workflows/topology');
		this.setCache(key, res, 60000);
		return res;
	}
	async getPipeline(useCache: boolean = true): Promise<any[]> {
		const key = 'workflows:pipeline';
		if (useCache) {
			const cached = this.getCached<any[]>(key);
			if (cached) return cached;
		}
		const res = await this.request<any[]>('/workflows/pipeline');
		this.setCache(key, res, 30000);
		return res;
	}
	async deployWorkflow(nodes: any[]): Promise<{ status: string; message: string }> {
		this.invalidateCache('workflows');
		return this.request<{ status: string; message: string }>('/workflows/deploy', {
			method: 'POST',
			body: JSON.stringify({ nodes })
		});
	}
	async testAdapterConnection(
		adapterId: string,
		config: Record<string, any>
	): Promise<{ success: boolean; message: string }> {
		return this.request<{ success: boolean; message: string }>('/workflows/test-connection', {
			method: 'POST',
			body: JSON.stringify({ adapter_id: adapterId, config })
		});
	}
	async saveAdapterConfig(
		adapterId: string,
		config: Record<string, any>
	): Promise<{ status: string; message: string }> {
		this.invalidateCache('workflows');
		return this.request<{ status: string; message: string }>(
			`/workflows/adapters/${adapterId}/config`,
			{
				method: 'POST',
				body: JSON.stringify({ config })
			}
		);
	}

	// --- Template CRUD ---
	async listTemplates(): Promise<TemplateOut[]> {
		return this.request<TemplateOut[]>('/templates');
	}
	async createTemplate(payload: {
		name: string;
		description?: string;
		format?: string;
		schema_definition?: Record<string, any>;
		is_default?: boolean;
	}): Promise<TemplateOut> {
		return this.request<TemplateOut>('/templates', {
			method: 'POST',
			body: JSON.stringify(payload)
		});
	}
	async getTemplate(id: string): Promise<TemplateOut> {
		return this.request<TemplateOut>(`/templates/${id}`);
	}
	async updateTemplate(
		id: string,
		payload: Partial<{
			name: string;
			description: string;
			format: string;
			schema_definition: Record<string, any>;
			is_default: boolean;
		}>
	): Promise<TemplateOut> {
		return this.request<TemplateOut>(`/templates/${id}`, {
			method: 'PUT',
			body: JSON.stringify(payload)
		});
	}
	async deleteTemplate(id: string): Promise<void> {
		await this.request<void>(`/templates/${id}`, { method: 'DELETE' });
	}
	async previewTemplate(
		schemaDefinition: Record<string, any>,
		sampleData?: Record<string, any>[],
		title?: string,
		sources?: string[]
	): Promise<string> {
		const url = `${this.baseUrl}/templates/preview`;
		const res = await fetch(url, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				schema_definition: schemaDefinition,
				sample_data: sampleData || [],
				title: title || 'Sample Orbit Mission Briefing',
				sources: sources || []
			})
		});
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		return res.text();
	}
}

export const api = new ApiClient();
