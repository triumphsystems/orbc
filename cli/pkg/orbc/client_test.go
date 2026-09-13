package orbc

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestClient_Health(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/health" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(HealthResponse{
			Status:           "ok",
			Version:          "0.2.0",
			Environment:      "test",
			SchedulerEnabled: true,
		})
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)
	resp, err := client.Health()
	if err != nil {
		t.Fatalf("Health() error = %v", err)
	}

	if resp.Status != "ok" || resp.Version != "0.2.0" {
		t.Errorf("unexpected health response: %+v", resp)
	}
}

func TestClient_CreateAutomation(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/automations" || r.Method != http.MethodPost {
			t.Errorf("unexpected request: %s %s", r.Method, r.URL.Path)
		}

		var req GoalRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatalf("failed to decode request body: %v", err)
		}

		if req.Goal != "Find PS5" {
			t.Errorf("unexpected goal in request: %s", req.Goal)
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(AutomationOut{
			ID:      "auto-123",
			RawGoal: req.Goal,
			Plan: ExecutionPlan{
				Objective:   "Find PS5",
				Domain:      "ecommerce",
				SearchQuery: "PS5 Nigeria",
				Frequency:   "daily",
			},
			Active:    true,
			CreatedAt: "2026-08-20T23:00:00Z",
		})
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)
	resp, err := client.CreateAutomation("Find PS5")
	if err != nil {
		t.Fatalf("CreateAutomation() error = %v", err)
	}

	if resp.ID != "auto-123" || resp.Plan.Domain != "ecommerce" {
		t.Errorf("unexpected automation response: %+v", resp)
	}
}

func TestClient_ListAutomations(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/automations" || r.Method != http.MethodGet {
			t.Errorf("unexpected request: %s %s", r.Method, r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(AutomationListOut{
			Items: []AutomationOut{
				{
					ID:      "auto-1",
					RawGoal: "Goal 1",
					Plan:    ExecutionPlan{Objective: "Obj 1", Domain: "jobs"},
					Active:  true,
				},
				{
					ID:      "auto-2",
					RawGoal: "Goal 2",
					Plan:    ExecutionPlan{Objective: "Obj 2", Domain: "real_estate"},
					Active:  false,
				},
			},
			Total: 2,
		})
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)
	list, err := client.ListAutomations()
	if err != nil {
		t.Fatalf("ListAutomations() error = %v", err)
	}

	if list.Total != 2 || len(list.Items) != 2 {
		t.Fatalf("unexpected items count: %+v", list)
	}
	if list.Items[0].ID != "auto-1" || list.Items[1].ID != "auto-2" {
		t.Errorf("unexpected automation list contents: %+v", list.Items)
	}
}

func TestClient_GetAutomation(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path != "/api/v1/automations/auto-abc" {
				t.Errorf("unexpected path: %s", r.URL.Path)
			}
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(AutomationOut{
				ID:      "auto-abc",
				RawGoal: "Track Flights",
				Plan: ExecutionPlan{
					Objective: "Find Lagos to London Flights",
					Domain:    "travel",
				},
				Active: true,
			})
		}))
		defer ts.Close()

		client := NewClient(ts.URL, 5*time.Second)
		auto, err := client.GetAutomation("auto-abc")
		if err != nil {
			t.Fatalf("GetAutomation() error = %v", err)
		}
		if auto.ID != "auto-abc" || auto.Plan.Domain != "travel" {
			t.Errorf("unexpected automation: %+v", auto)
		}
	})

	t.Run("not found (404)", func(t *testing.T) {
		ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			http.Error(w, `{"detail":"automation not found"}`, http.StatusNotFound)
		}))
		defer ts.Close()

		client := NewClient(ts.URL, 5*time.Second)
		_, err := client.GetAutomation("non-existent")
		if err == nil {
			t.Fatalf("expected error for 404 response, got nil")
		}
		if !strings.Contains(err.Error(), "404") {
			t.Errorf("expected error message to contain status 404, got %v", err)
		}
	})
}

func TestClient_DeleteAutomation(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/automations/auto-del" || r.Method != http.MethodDelete {
			t.Errorf("unexpected request: %s %s", r.Method, r.URL.Path)
		}
		w.WriteHeader(http.StatusNoContent)
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)
	err := client.DeleteAutomation("auto-del")
	if err != nil {
		t.Fatalf("DeleteAutomation() error = %v", err)
	}
}

func TestClient_RunAutomation_And_GetRun(t *testing.T) {
	condMatched := true
	condMsg := "Price < 400000 NGN"
	mockRun := RunOut{
		ID:               "run-999",
		AutomationID:     "auto-123",
		Status:           "completed",
		StartedAt:        "2026-08-23T12:00:00Z",
		ExtractedCount:   3,
		ValidatedCount:   3,
		ConditionMatched: &condMatched,
		ConditionMessage: &condMsg,
		SourcesFound:     []string{"https://store1.com/item", "https://store2.com/item"},
		Results: []ResultOut{
			{
				ID:    "res-1",
				URL:   "https://store1.com/item",
				Valid: true,
				Data: map[string]interface{}{
					"title": "PS5 Console",
					"price": 375000,
				},
			},
		},
	}

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/v1/automations/auto-123/run":
			_ = json.NewEncoder(w).Encode(mockRun)
		case "/api/v1/runs/run-999":
			_ = json.NewEncoder(w).Encode(mockRun)
		case "/api/v1/automations/auto-123/runs":
			_ = json.NewEncoder(w).Encode([]RunOut{mockRun})
		default:
			http.NotFound(w, r)
		}
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)

	// Test RunAutomation
	run, err := client.RunAutomation("auto-123")
	if err != nil {
		t.Fatalf("RunAutomation() error = %v", err)
	}
	if run.ID != "run-999" || run.Status != "completed" || len(run.Results) != 1 {
		t.Errorf("unexpected run output: %+v", run)
	}

	// Test GetRun
	runDetails, err := client.GetRun("run-999")
	if err != nil {
		t.Fatalf("GetRun() error = %v", err)
	}
	if runDetails.ID != "run-999" || *runDetails.ConditionMatched != true {
		t.Errorf("unexpected run details: %+v", runDetails)
	}

	// Test ListRuns
	runsList, err := client.ListRuns("auto-123")
	if err != nil {
		t.Fatalf("ListRuns() error = %v", err)
	}
	if len(runsList) != 1 || runsList[0].ID != "run-999" {
		t.Errorf("unexpected list runs: %+v", runsList)
	}
}

func TestClient_ErrorMatrix(t *testing.T) {
	t.Run("server 500 error", func(t *testing.T) {
		ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			http.Error(w, `{"error":"internal agent crash"}`, http.StatusInternalServerError)
		}))
		defer ts.Close()

		client := NewClient(ts.URL, 5*time.Second)
		_, err := client.Health()
		if err == nil {
			t.Fatalf("expected error on 500 response, got nil")
		}
		if !strings.Contains(err.Error(), "500") {
			t.Errorf("expected error to mention status 500, got %v", err)
		}
	})

	t.Run("timeout handling", func(t *testing.T) {
		ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			time.Sleep(50 * time.Millisecond)
			w.WriteHeader(http.StatusOK)
		}))
		defer ts.Close()

		// Set client timeout lower than server delay
		client := NewClient(ts.URL, 10*time.Millisecond)
		_, err := client.Health()
		if err == nil {
			t.Fatalf("expected timeout error, got nil")
		}
	})
}

func TestClient_SchedulerEndpoints(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/v1/scheduler/status":
			if r.Header.Get("X-Scheduler-Secret") != "test-secret" {
				http.Error(w, `{"detail":"unauthorized"}`, http.StatusUnauthorized)
				return
			}
			_ = json.NewEncoder(w).Encode(SchedulerStatusResponse{
				ServerTimeUTC:       "2026-08-23T12:00:00Z",
				ActiveScheduleCount: 1,
				Schedules: []ScheduledItem{
					{
						AutomationID: "auto-101",
						Objective:    "Track Gold Prices",
						Frequency:    "daily",
						Timezone:     "UTC",
						IsDue:        true,
					},
				},
			})
		case "/api/v1/scheduler/trigger-due":
			_ = json.NewEncoder(w).Encode(SchedulerTriggerResponse{
				Status:                 "success",
				DueCount:               1,
				TriggeredAutomationIDs: []string{"auto-101"},
				Wait:                   false,
				ServerTimeUTC:          "2026-08-23T12:00:00Z",
			})
		default:
			http.NotFound(w, r)
		}
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)

	// Test GetSchedulerStatus
	status, err := client.GetSchedulerStatus("test-secret")
	if err != nil {
		t.Fatalf("GetSchedulerStatus() error = %v", err)
	}
	if status.ActiveScheduleCount != 1 || len(status.Schedules) != 1 || status.Schedules[0].AutomationID != "auto-101" {
		t.Errorf("unexpected scheduler status: %+v", status)
	}

	// Test TriggerDueAutomations
	triggerResp, err := client.TriggerDueAutomations(false, "test-secret")
	if err != nil {
		t.Fatalf("TriggerDueAutomations() error = %v", err)
	}
	if triggerResp.Status != "success" || triggerResp.DueCount != 1 {
		t.Errorf("unexpected trigger response: %+v", triggerResp)
	}
}

func TestClient_WorkflowEndpoints(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/v1/workflows/pipeline":
			_ = json.NewEncoder(w).Encode([]map[string]interface{}{
				{"id": "node-1", "stage": "trigger"},
			})
		case "/api/v1/workflows/deploy":
			_ = json.NewEncoder(w).Encode(WorkflowDeployResponse{
				Status:     "deployed",
				Message:    "Pipeline updated with 1 active adapter stages.",
				DeployedAt: "2026-08-23T12:00:00Z",
			})
		case "/api/v1/workflows/test-connection":
			_ = json.NewEncoder(w).Encode(TestConnectionResponse{
				Success: true,
				Message: "Connection successful",
			})
		case "/api/v1/workflows/adapters/slack/config":
			_ = json.NewEncoder(w).Encode(SaveAdapterConfigResponse{
				Status:    "saved",
				AdapterID: "slack",
				Message:   "Configuration saved",
				SavedAt:   "2026-08-23T12:00:00Z",
			})
		default:
			http.NotFound(w, r)
		}
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)

	// Pipeline
	pipeline, err := client.GetDeployedPipeline()
	if err != nil || len(pipeline) != 1 {
		t.Fatalf("GetDeployedPipeline() error = %v, pipeline = %+v", err, pipeline)
	}

	// Deploy
	deployResp, err := client.DeployWorkflow([]map[string]interface{}{{"id": "node-1"}})
	if err != nil || deployResp.Status != "deployed" {
		t.Fatalf("DeployWorkflow() error = %v, resp = %+v", err, deployResp)
	}

	// Test connection
	connResp, err := client.TestAdapterConnection("slack", map[string]interface{}{"url": "https://hooks.slack.com/xxx"})
	if err != nil || !connResp.Success {
		t.Fatalf("TestAdapterConnection() error = %v, resp = %+v", err, connResp)
	}

	// Save adapter config
	saveResp, err := client.SaveAdapterConfig("slack", map[string]interface{}{"url": "https://hooks.slack.com/xxx"})
	if err != nil || saveResp.Status != "saved" {
		t.Fatalf("SaveAdapterConfig() error = %v, resp = %+v", err, saveResp)
	}
}

func TestClient_GetRunDossier(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v1/runs/run-123/dossier" {
			w.Header().Set("Content-Type", "application/pdf")
			_, _ = w.Write([]byte("%PDF-1.4 mock content"))
			return
		}
		http.NotFound(w, r)
	}))
	defer ts.Close()

	client := NewClient(ts.URL, 5*time.Second)
	content, contentType, err := client.GetRunDossier("run-123")
	if err != nil {
		t.Fatalf("GetRunDossier() error = %v", err)
	}
	if contentType != "application/pdf" || string(content) != "%PDF-1.4 mock content" {
		t.Errorf("unexpected dossier response: type=%s, content=%s", contentType, string(content))
	}
}
