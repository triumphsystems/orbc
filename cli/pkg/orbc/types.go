package orbc

type ExtractionField struct {
	Name        string   `json:"name"`
	Type        string   `json:"type"`
	Description string   `json:"description,omitempty"`
	Required    bool     `json:"required"`
	EnumValues  []string `json:"enum_values,omitempty"`
}

type DynamicExtractionSchema struct {
	EntityName  string            `json:"entity_name"`
	Fields      []ExtractionField `json:"fields"`
	Description string            `json:"description,omitempty"`
}

type MissingParameter struct {
	NodeID        string  `json:"node_id"`
	AdapterType   string  `json:"adapter_type"`
	ParameterName string  `json:"parameter_name"`
	Label         string  `json:"label"`
	Prompt        string  `json:"prompt"`
	DefaultValue  *string `json:"default_value,omitempty"`
	Required      bool    `json:"required"`
}

type ExecutionPlan struct {
	Objective           string                  `json:"objective"`
	Domain              string                  `json:"domain"`
	SearchQuery         string                  `json:"search_query"`
	SourceHints         []string                `json:"source_hints,omitempty"`
	Geography           string                  `json:"geography,omitempty"`
	CountryCode         string                  `json:"country_code,omitempty"`
	ExtractionSchema    DynamicExtractionSchema `json:"extraction_schema"`
	Frequency           string                  `json:"frequency"`
	ScheduleTime        string                  `json:"schedule_time,omitempty"`
	Timezone            string                  `json:"timezone"`
	Condition           string                  `json:"condition,omitempty"`
	NotificationChannel string                  `json:"notification_channel,omitempty"`
	WorkflowNodes       []map[string]interface{} `json:"workflow_nodes,omitempty"`
	MissingParameters   []MissingParameter      `json:"missing_parameters,omitempty"`
}

type GoalRequest struct {
	Goal string `json:"goal"`
}

type AutomationOut struct {
	ID        string        `json:"id"`
	RawGoal   string        `json:"raw_goal"`
	Plan      ExecutionPlan `json:"plan"`
	Active    bool          `json:"active"`
	CreatedAt string        `json:"created_at"`
	NextRunAt *string       `json:"next_run_at,omitempty"`
}

type AutomationListOut struct {
	Items []AutomationOut `json:"items"`
	Total int             `json:"total"`
}

type ResultOut struct {
	ID               string                 `json:"id"`
	URL              string                 `json:"url,omitempty"`
	Data             map[string]interface{} `json:"data"`
	Valid            bool                   `json:"valid"`
	ValidationErrors []string               `json:"validation_errors,omitempty"`
	CreatedAt        string                 `json:"created_at"`
}

type RunOut struct {
	ID               string                   `json:"id"`
	AutomationID     string                   `json:"automation_id"`
	Status           string                   `json:"status"`
	StartedAt        string                   `json:"started_at"`
	FinishedAt       *string                  `json:"finished_at,omitempty"`
	SourcesFound     []string                 `json:"sources_found,omitempty"`
	PagesRetrieved   []string                 `json:"pages_retrieved,omitempty"`
	ExtractedCount   int                      `json:"extracted_count"`
	ValidatedCount   int                      `json:"validated_count"`
	ConditionMatched *bool                    `json:"condition_matched,omitempty"`
	ConditionMessage *string                  `json:"condition_message,omitempty"`
	ReasoningLog     []map[string]interface{} `json:"reasoning_log,omitempty"`
	Error            *string                  `json:"error,omitempty"`
	Results          []ResultOut              `json:"results,omitempty"`
}

type HealthResponse struct {
	Status           string `json:"status"`
	Version          string `json:"version"`
	Environment      string `json:"environment"`
	SchedulerEnabled bool   `json:"scheduler_enabled"`
}

type WorkflowNodeOut struct {
	ID          string                 `json:"id"`
	Label       string                 `json:"label"`
	Category    string                 `json:"category"`
	Mode        string                 `json:"mode,omitempty"`
	Engine      string                 `json:"engine,omitempty"`
	IconName    string                 `json:"iconName"`
	Description string                 `json:"description"`
	Status      string                 `json:"status"`
	Config      map[string]interface{} `json:"config"`
}

type WorkflowDeployPayload struct {
	Nodes []map[string]interface{} `json:"nodes"`
}

type WorkflowDeployResponse struct {
	Status     string `json:"status"`
	Message    string `json:"message"`
	DeployedAt string `json:"deployed_at,omitempty"`
	PipelineID string `json:"pipeline_id,omitempty"`
	NodeCount  int    `json:"node_count,omitempty"`
}

type TestConnectionPayload struct {
	AdapterID string                 `json:"adapter_id"`
	Config    map[string]interface{} `json:"config"`
}

type TestConnectionResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

type SaveAdapterConfigPayload struct {
	Config map[string]interface{} `json:"config"`
}

type SaveAdapterConfigResponse struct {
	Status    string `json:"status"`
	AdapterID string `json:"adapter_id"`
	Message   string `json:"message"`
	SavedAt   string `json:"saved_at"`
}

type ScheduledItem struct {
	AutomationID string  `json:"automation_id"`
	Objective    string  `json:"objective"`
	Frequency    string  `json:"frequency"`
	ScheduleTime *string `json:"schedule_time,omitempty"`
	Timezone     string  `json:"timezone"`
	NextRunAt    *string `json:"next_run_at,omitempty"`
	IsDue        bool    `json:"is_due"`
}

type SchedulerStatusResponse struct {
	ServerTimeUTC       string          `json:"server_time_utc"`
	ActiveScheduleCount int             `json:"active_schedule_count"`
	Schedules           []ScheduledItem `json:"schedules"`
}

type SchedulerTriggerResponse struct {
	Status                 string                   `json:"status"`
	DueCount               int                      `json:"due_count"`
	TriggeredAutomationIDs []string                 `json:"triggered_automation_ids"`
	Wait                   bool                     `json:"wait"`
	ServerTimeUTC          string                   `json:"server_time_utc"`
	Executions             []map[string]interface{} `json:"executions,omitempty"`
}
