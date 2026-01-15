package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/farcovka/ledger/internal/db"
	"github.com/farcovka/ledger/internal/httpapi"
)

const (
	defaultAddr = ":8080"
	shutdownTimeout = 10 * time.Second
)

func main() {
	logger := log.New(os.Stdout, "ledger ", log.LstdFlags|log.LUTC)

	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		logger.Fatal("DATABASE_URL is required")
	}

	ctx := context.Background()
	pool, err := db.NewPool(ctx, databaseURL)
	if err != nil {
		logger.Fatalf("connect to database: %v", err)
	}
	defer pool.Close()

	addr := os.Getenv("LEDGER_ADDR")
	if addr == "" {
		addr = defaultAddr
	}

	handler := httpapi.NewHandler(pool, logger)
	server := &http.Server{
		Addr:              addr,
		Handler:           handler.Router(),
		ReadHeaderTimeout: 5 * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		logger.Printf("listening on %s", addr)
		errCh <- server.ListenAndServe()
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)

	select {
	case <-stop:
		logger.Println("shutting down")
	case err := <-errCh:
		logger.Fatalf("server stopped: %v", err)
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		logger.Fatalf("shutdown error: %v", err)
	}
}
