package orbc

import (
	"bufio"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/go-resty/resty/v2"
)

type Client struct {
	http    *resty.Client
	baseURL string
}

func NewClient(baseURL string, timeout time.Duration) *Client {
	baseURL = strings.TrimRight(baseURL, "/")
	baseURL = strings.TrimSuffix(baseURL, "/api/v1")
	baseURL = strings.TrimRight(baseURL, "/")
	r := resty.New().
		SetBaseURL(baseURL).
		SetTimeout(timeout).
		SetHeader("Accept", "application/json").
		SetHeader("User-Agent", "Orbit-CLI/0.2.0")

	return &Client{http: r, baseURL: baseURL}
}

func (c *Client) BaseURL() string {
	return c.baseURL
}

func (c *Client) Health() (*HealthResponse, error) {
	var resp HealthResponse
	r, err := c.http.R().SetResult(&resp).Get("/api/v1/health")
	if err != nil {
		return nil, fmt.Errorf("health check failed: %w", err)
	}
	if r.IsError() {
		return nil, fmt.Errorf("server error: %s (status %d)", r.String(), r.StatusCode())
	}
	return &resp, nil
}

func (c *Client) CreateAutomation(goal string) (*AutomationOut, error) {
	var out AutomationOut
	r, err := c.http.R().SetBody(GoalRequest{Goal: goal}).SetResult(&out).Post("/api/v1/automations")
	if err != nil {
		return nil, fmt.Errorf("failed to create automation: %w", err)
	}
	if r.IsError() {
		return nil, fmt.Errorf("failed to create automation: %s (status %d)", r.String(), r.StatusCode())
	}
	return &out, nil
}

func (c *Client) ListAutomations() (*AutomationListOut, error) {
	var out AutomationListOut
	r, err := c.http.R().SetResult(&out).Get("/api/v1/automations")
	if err != nil {
		return nil, fmt.Errorf("failed to list automations: %w", err)
	}
	if r.IsError() {
		return nil, fmt.Errorf("failed to list automations: %s (status %d)", r.String(), r.StatusCode())
	}
	return &out, nil
}

func (c *Client) GetAutomation(id string) (*AutomationOut, error) {
	var out AutomationOut
	r, err := c.http.R().SetResult(&out).Get(fmt.Sprintf("/api/v1/automations/%s", id))
	if err != nil {
		return nil, fmt.Errorf("failed to get automation %s: %w", id, err)
	}
	if r.IsError() {
		return nil, fmt.Errorf("automation not found: %s (status %d)", r.String(), r.StatusCode())
	}
	return &out, nil
}

func (c *Client) DeleteAutomation(id string) error {
	r, err := c.http.R().Delete(fmt.Sprintf("/api/v1/automations/%s", id))
	if err != nil {
		return fmt.Errorf("failed to delete automation %s: %w", id, err)
	}
	if r.IsError() {
		return fmt.Errorf("failed to delete automation: %s (status %d)", r.String(), r.StatusCode())
	}
	return nil
}

func (c *Client) StreamGoalPlan(goal string, handler func(event string, data string) error) error {
	url := fmt.Sprintf("%s/api/v1/automations/plan/stream?goal=%s", c.baseURL, strings.ReplaceAll(goal, " ", "+"))
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("User-Agent", "Orbit-CLI/0.2.0")

	httpClient := &http.Client{Timeout: 0}
	resp, err := httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to connect to plan stream: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("plan stream failed with HTTP status %d", resp.StatusCode)
	}

	scanner := bufio.NewScanner(resp.Body)
	var currentEvent string
	var dataLines []string

	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "event:") {
			currentEvent = strings.TrimSpace(strings.TrimPrefix(line, "event:"))
		} else if strings.HasPrefix(line, "data:") {
			dataLines = append(dataLines, strings.TrimPrefix(line, "data:"))
		} else if line == "" {
			if len(dataLines) > 0 {
				joinedData := strings.Join(dataLines, "\n")
				if err := handler(currentEvent, joinedData); err != nil {
					return err
				}
				if currentEvent == "complete" || currentEvent == "error" {
					return nil
				}
				currentEvent = ""
				dataLines = nil
			}
		}
	}

	return scanner.Err()
}

func (c *Client) GetSchedulerStatus(secret string) (*SchedulerStatusResponse, error) {
	var out SchedulerStatusResponse
	req := c.http.R().SetResult(&out)
	if secret != "" {
		req.SetHeader("X-Scheduler-Secret", secret)
	}
	r, err := req.Get("/api/v1/scheduler/status")
	if err != nil {
		return nil, fmt.Errorf("failed to get scheduler status: %w", err)
	}
	if r.IsError() {
		return nil, fmt.Errorf("failed to get scheduler status: %s (status %d)", r.String(), r.StatusCode())
	}
	return &out, nil
}

func (c *Client) TriggerDueAutomations(wait bool, secret string) (*SchedulerTriggerResponse, error) {
	var out SchedulerTriggerResponse
	req := c.http.R().SetResult(&out).SetQueryParam("wait", fmt.Sprintf("%t", wait))
	if secret != "" {
		req.SetHeader("X-Scheduler-Secret", secret)
	}
	r, err := req.Post("/api/v1/scheduler/trigger-due")
	if err != nil {
		return nil, fmt.Errorf("failed to trigger due automations: %w", err)
	}
	if r.IsError() {
		return nil, fmt.Errorf("failed to trigger due automations: %s (status %d)", r.String(), r.StatusCode())
	}
	return &out, nil
}

