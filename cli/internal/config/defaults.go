package config

import "time"

var (
	DefaultAPIURL  = "http://localhost:8000"
	DefaultTimeout = 120 * time.Second
	DefaultFormat  = "table"
)
