package commands

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/leoemaxie/orbit/cli/internal/config"
	"github.com/leoemaxie/orbit/cli/internal/formatters"
	"github.com/leoemaxie/orbit/cli/internal/ui"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage CLI configuration and preferences",
}

var configSetCmd = &cobra.Command{
	Use:   "set <key> <value>",
	Short: "Set a configuration parameter (e.g. api_url, format, timeout)",
	Args:  cobra.ExactArgs(2),
	RunE: func(cmd *cobra.Command, args []string) error {
		key, val := args[0], args[1]
		if err := config.SetKey(key, val); err != nil {
			ui.Error("Failed to save config: %v", err)
			return err
		}
		normKey := config.NormalizeKey(key)
		ui.Success("Configuration updated: %s = %s", normKey, val)
		return nil
	},
}

var configShowCmd = &cobra.Command{
	Use:     "show [key]",
	Aliases: []string{"get"},
	Short:   "Show current configuration or a specific key value",
	Example: `  orbc config show
  orbc config show api_url
  orbc config get timeout
  orbc config show --json`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) == 1 {
			key := args[0]
			val, err := config.GetKey(key)
			if err != nil {
				ui.Error("Failed to get config key: %v", err)
				return err
			}
			if jsonFlag {
				return formatters.PrintJSON(map[string]string{
					config.NormalizeKey(key): val,
				})
			}
			fmt.Println(val)
			return nil
		}

		c, err := config.LoadConfig()
		if err != nil {
			return err
		}
		if jsonFlag {
			return formatters.PrintJSON(c)
		}
		ui.PrintBanner()
		fmt.Printf("API URL : %s\n", ui.Cyan(c.APIURL))
		fmt.Printf("Timeout : %s\n", ui.Cyan(fmt.Sprintf("%v", c.Timeout)))
		fmt.Printf("Format  : %s\n", ui.Cyan(c.Format))
		if c.SchedulerSecret != "" {
			fmt.Printf("Secret  : %s\n", ui.Cyan(c.SchedulerSecret))
		}
		return nil
	},
}

func init() {
	configCmd.AddCommand(configSetCmd)
	configCmd.AddCommand(configShowCmd)
}

