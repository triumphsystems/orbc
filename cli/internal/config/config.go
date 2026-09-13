package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// Config holds all CLI user preferences and connection info.
type Config struct {
	APIURL          string        `mapstructure:"api_url"`
	Timeout         time.Duration `mapstructure:"timeout"`
	Format          string        `mapstructure:"format"`
	SchedulerSecret string        `mapstructure:"scheduler_secret"`
}

// NormalizeKey normalizes configuration keys across kebab-case, snake_case, and aliases.
func NormalizeKey(key string) string {
	k := strings.ToLower(strings.TrimSpace(key))
	k = strings.ReplaceAll(k, "-", "_")
	switch k {
	case "api_url", "apiurl", "url", "api", "endpoint", "base_url":
		return "api_url"
	case "timeout":
		return "timeout"
	case "format":
		return "format"
	case "scheduler_secret", "schedulersecret", "secret":
		return "scheduler_secret"
	default:
		return k
	}
}

// LoadConfig loads the CLI configuration from ~/.orbc/config.yaml or environment variables.
func LoadConfig() (*Config, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, fmt.Errorf("failed to get user home directory: %w", err)
	}

	configDir := filepath.Join(home, ".orbc")

	viper.AddConfigPath(configDir)
	// Also check fallback ~/.orbit for backward compatibility
	viper.AddConfigPath(filepath.Join(home, ".orbit"))
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")

	viper.SetDefault("api_url", DefaultAPIURL)
	viper.SetDefault("timeout", DefaultTimeout)
	viper.SetDefault("format", DefaultFormat)
	viper.SetDefault("scheduler_secret", "")

	viper.RegisterAlias("api-url", "api_url")
	viper.RegisterAlias("scheduler-secret", "scheduler_secret")

	viper.SetEnvPrefix("ORBC")
	viper.AutomaticEnv()

	// Read config file if it exists, otherwise use defaults and environment variables
	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok && !os.IsNotExist(err) {
			return nil, fmt.Errorf("error reading config file: %w", err)
		}
	}

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unable to decode config: %w", err)
	}

	// Handle fallback if api-url or other aliases were saved in config file without underscore
	if v := viper.GetString("api-url"); v != "" && (cfg.APIURL == "" || cfg.APIURL == DefaultAPIURL) {
		cfg.APIURL = v
	}
	if v := viper.GetString("scheduler-secret"); v != "" && cfg.SchedulerSecret == "" {
		cfg.SchedulerSecret = v
	}

	return &cfg, nil
}

// GetKey retrieves a specific configuration parameter by key name or alias.
func GetKey(key string) (string, error) {
	cfg, err := LoadConfig()
	if err != nil {
		return "", err
	}
	normKey := NormalizeKey(key)
	switch normKey {
	case "api_url":
		return cfg.APIURL, nil
	case "timeout":
		return cfg.Timeout.String(), nil
	case "format":
		return cfg.Format, nil
	case "scheduler_secret":
		return cfg.SchedulerSecret, nil
	default:
		val := viper.GetString(normKey)
		if val != "" {
			return val, nil
		}
		return "", fmt.Errorf("unknown configuration key '%s'", key)
	}
}

// SetKey updates a configuration key and saves to ~/.orbc/config.yaml.
func SetKey(key, value string) error {
	home, err := os.UserHomeDir()
	if err != nil {
		return err
	}

	configDir := filepath.Join(home, ".orbc")
	_ = os.MkdirAll(configDir, 0755)
	configFile := filepath.Join(configDir, "config.yaml")

	normKey := NormalizeKey(key)

	// Validate timeout duration if setting timeout
	if normKey == "timeout" {
		if _, err := time.ParseDuration(value); err != nil {
			return fmt.Errorf("invalid timeout duration '%s' (example: '30s', '2m'): %w", value, err)
		}
	}

	viper.Set(normKey, value)
	if _, err := os.Stat(configFile); err == nil {
		return viper.WriteConfig()
	}
	return viper.WriteConfigAs(configFile)
}

