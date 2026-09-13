package commands

import (
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
	"github.com/leoemaxie/orbit/cli/pkg/orbc"
	"github.com/spf13/cobra"
)

var (
	scheduleWaitFlag   bool
	scheduleSecretFlag string
)

var scheduleCmd = &cobra.Command{
	Use:   "schedule",
	Short: "Manage and inspect recurring automation schedules",
}

var scheduleListCmd = &cobra.Command{
	Use:   "list",
	Short: "List active recurring schedules",
	RunE: func(cmd *cobra.Command, args []string) error {
		// Attempt to query dedicated scheduler status endpoint first
		statusResp, err := client.GetSchedulerStatus(scheduleSecretFlag)
		if err == nil {
			if jsonFlag {
				return formatters.PrintJSON(statusResp)
			}

			ui.PrintBanner()
			ui.Info("Recurring Schedules Daemon (Server Time: %s, Active: %d):", statusResp.ServerTimeUTC, statusResp.ActiveScheduleCount)
			if len(statusResp.Schedules) == 0 {
				ui.Info("No active recurring schedules registered.")
				return nil
			}

			headers := []string{"Automation ID", "Objective", "Frequency", "Timezone", "Next Run (UTC)", "Due"}
			var rows [][]string
			for _, s := range statusResp.Schedules {
				nextRun := "-"
				if s.NextRunAt != nil {
					nextRun = *s.NextRunAt
				}
				dueStr := ui.Gray("false")
				if s.IsDue {
					dueStr = ui.Green("true")
				}
				rows = append(rows, []string{
					ui.Cyan(ui.ShortID(s.AutomationID)),
					s.Objective,
					ui.Magenta(s.Frequency),
					s.Timezone,
					nextRun,
					dueStr,
				})
			}
			formatters.RenderTable(headers, rows)
			return nil
		}

		// Fallback to ListAutomations
		list, err := client.ListAutomations()
		if err != nil {
			ui.Error("Failed to list schedules: %v", err)
			return err
		}

		scheduled := make([]orbc.AutomationOut, 0)
		for _, a := range list.Items {
			if a.Active && a.Plan.Frequency != "once" {
				scheduled = append(scheduled, a)
			}
		}

		if jsonFlag {
			return formatters.PrintJSON(scheduled)
		}

		ui.PrintBanner()
		ui.Info("Recurring Schedules Daemon:")
		formatters.RenderAutomationsTable(scheduled, noTruncFlag)
		return nil
	},
}

var scheduleTriggerCmd = &cobra.Command{
	Use:     "trigger",
	Aliases: []string{"tick", "run-due"},
	Short:   "Trigger execution of all currently due scheduled automations",
	RunE: func(cmd *cobra.Command, args []string) error {
		resp, err := client.TriggerDueAutomations(scheduleWaitFlag, scheduleSecretFlag)
		if err != nil {
			if jsonFlag {
				return formatters.PrintJSON(map[string]interface{}{
					"status": "error",
					"error":  err.Error(),
				})
			}
			ui.Error("Failed to trigger due automations: %v", err)
			return err
		}

		if jsonFlag {
			return formatters.PrintJSON(resp)
		}

		ui.PrintBanner()
		ui.Success("Scheduler hook triggered successfully!")
		ui.Info("Due Automations   : %d", resp.DueCount)
		ui.Info("Triggered IDs     : %v", resp.TriggeredAutomationIDs)
		ui.Info("Server Time (UTC) : %s", resp.ServerTimeUTC)
		if resp.Wait && len(resp.Executions) > 0 {
			ui.Info("Execution Results : %v", resp.Executions)
		}
		return nil
	},
}

func init() {
	scheduleListCmd.Flags().StringVar(&scheduleSecretFlag, "secret", "", "Scheduler authentication secret")
	scheduleTriggerCmd.Flags().BoolVar(&scheduleWaitFlag, "wait", false, "Wait for executions to complete before returning")
	scheduleTriggerCmd.Flags().StringVar(&scheduleSecretFlag, "secret", "", "Scheduler authentication secret")

	scheduleCmd.AddCommand(scheduleListCmd)
	scheduleCmd.AddCommand(scheduleTriggerCmd)
}
