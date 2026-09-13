export type Frequency = 'once' | 'hourly' | 'daily' | 'weekly' | 'monthly';

export interface ExtractionField {
	name: string;
	type: 'string' | 'number' | 'boolean' | 'array' | 'object';
	description?: string;
	required?: boolean;
	enum_values?: string[] | null;
}

export interface DynamicExtractionSchema {
	entity_name: string;
	fields: ExtractionField[];
	description?: string | null;
}

export interface MissingParameter {
	node_id?: string;
	adapter_type: string;
	parameter_name: string;
	label: string;
	prompt: string;
	default_value?: string | null;
	required?: boolean;
}

export interface ExecutionPlan {
	objective: string;
	domain: string;
	search_query: string;
	source_hints?: string[];
	geography?: string | null;
	country_code?: string | null;
	extraction_schema: DynamicExtractionSchema;
	frequency: Frequency;
	schedule_time?: string | null;
	timezone: string;
	condition?: string | null;
	notification_channel?: string | null;
	workflow_nodes?: any[];
	missing_parameters?: MissingParameter[];
}

export interface GoalRequest {
	goal: string;
}

export interface AutomationOut {
	id: string;
	raw_goal: string;
	plan: ExecutionPlan;
	active: boolean;
	created_at: string;
	next_run_at?: string | null;
}

export interface AutomationListOut {
	items: AutomationOut[];
	total: number;
}

export interface ResultOut {
	id: string;
	url?: string | null;
	data: Record<string, any>;
	valid: boolean;
	validation_errors?: string[] | null;
	created_at: string;
}

export interface RunOut {
	id: string;
	automation_id: string;
	status: 'pending' | 'running' | 'completed' | 'failed' | 'partial' | string;
	started_at: string;
	finished_at?: string | null;
	sources_found?: string[] | null;
	pages_retrieved?: string[] | null;
	extracted_count?: number;
	validated_count?: number;
	condition_matched?: boolean | null;
	condition_message?: string | null;
	reasoning_log?: Array<Record<string, any>> | null;
	error?: string | null;
	results: ResultOut[];
}

export interface HealthStatus {
	status: string;
	version: string;
	environment: string;
	scheduler_enabled: boolean;
}
