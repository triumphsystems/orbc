package config

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/spf13/viper"
)

func TestConfig_Defaults(t *testing.T) {
	viper.Reset()
	tmpHome := t.TempDir()
	t.Setenv("USERPROFILE", tmpHome)
	t.Setenv("HOME", tmpHome)

	cfg, err := LoadConfig()
	if err != nil {
		t.Fatalf("LoadConfig() failed: %v", err)
	}

	if cfg.APIURL != DefaultAPIURL {
		t.Errorf("expected APIURL %q, got %q", DefaultAPIURL, cfg.APIURL)
	}
	if cfg.Timeout != DefaultTimeout {
		t.Errorf("expected Timeout %v, got %v", DefaultTimeout, cfg.Timeout)
	}
	if cfg.Format != DefaultFormat {
		t.Errorf("expected Format %q, got %q", DefaultFormat, cfg.Format)
	}

	// Verify that ~/.orbc/config.yaml is NOT eagerly generated on read
	configFile := filepath.Join(tmpHome, ".orbc", "config.yaml")
	if _, err := os.Stat(configFile); !os.IsNotExist(err) {
		t.Errorf("expected config file %q to not exist on default read, but it was created", configFile)
	}
}

func TestConfig_EnvOverrides(t *testing.T) {
	viper.Reset()
	tmpHome := t.TempDir()
	t.Setenv("USERPROFILE", tmpHome)
	t.Setenv("HOME", tmpHome)

	t.Setenv("ORBC_API_URL", "http://custom-orbit-host:9090")
	t.Setenv("ORBC_FORMAT", "json")
	t.Setenv("ORBC_TIMEOUT", "45s")

	cfg, err := LoadConfig()
	if err != nil {
		t.Fatalf("LoadConfig() with env overrides failed: %v", err)
	}

	if cfg.APIURL != "http://custom-orbit-host:9090" {
		t.Errorf("expected APIURL override, got %q", cfg.APIURL)
	}
	if cfg.Format != "json" {
		t.Errorf("expected Format override, got %q", cfg.Format)
	}
	if cfg.Timeout != 45*time.Second {
		t.Errorf("expected Timeout override 45s, got %v", cfg.Timeout)
	}
}

func TestConfig_SetKey(t *testing.T) {
	viper.Reset()
	tmpHome := t.TempDir()
	t.Setenv("USERPROFILE", tmpHome)
	t.Setenv("HOME", tmpHome)

	t.Run("set key with underscore", func(t *testing.T) {
		err := SetKey("api_url", "http://updated-daemon:8080")
		if err != nil {
			t.Fatalf("SetKey failed: %v", err)
		}

		cfg, err := LoadConfig()
		if err != nil {
			t.Fatalf("LoadConfig after SetKey failed: %v", err)
		}

		if cfg.APIURL != "http://updated-daemon:8080" {
			t.Errorf("expected updated APIURL, got %q", cfg.APIURL)
		}
	})

	t.Run("set key with hyphen and retrieve with GetKey", func(t *testing.T) {
		err := SetKey("api-url", "http://localhost:8000")
		if err != nil {
			t.Fatalf("SetKey with hyphen failed: %v", err)
		}

		cfg, err := LoadConfig()
		if err != nil {
			t.Fatalf("LoadConfig after SetKey failed: %v", err)
		}

		if cfg.APIURL != "http://localhost:8000" {
			t.Errorf("expected updated APIURL %q, got %q", "http://localhost:8000", cfg.APIURL)
		}

		val, err := GetKey("api-url")
		if err != nil || val != "http://localhost:8000" {
			t.Errorf("GetKey('api-url') failed: %v, val: %s", err, val)
		}

		val2, err := GetKey("api_url")
		if err != nil || val2 != "http://localhost:8000" {
			t.Errorf("GetKey('api_url') failed: %v, val: %s", err, val2)
		}
	})
}

