package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"
)

type cashDepositRequest struct {
	UserID    string `json:"user_id"`
	Currency  string `json:"currency"`
	Amount    string `json:"amount"`
	Note      string `json:"note"`
	CreatedBy string `json:"created_by"`
}

type cashConfirmRequest struct {
	ConfirmedBy string `json:"confirmed_by"`
	Note        string `json:"note"`
}

func (h *Handler) handleCashDeposits(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req cashDepositRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}

	if err := validateCashDeposit(req); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	var id string
	query := `
		INSERT INTO cash_deposits (user_id, currency, amount, status, note, created_by)
		VALUES ($1, $2, $3, 'pending', $4, $5)
		RETURNING id
	`
	if err := h.pool.QueryRow(ctx, query, req.UserID, strings.ToUpper(req.Currency), req.Amount, req.Note, req.CreatedBy).Scan(&id); err != nil {
		h.logger.Printf("cash deposit insert failed: %v", err)
		writeError(w, http.StatusInternalServerError, "could not create deposit")
		return
	}

	writeJSON(w, http.StatusCreated, map[string]string{"id": id, "status": "pending"})
}

func (h *Handler) handleCashDepositAction(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/cash/deposits/")
	parts := strings.Split(path, "/")
	if len(parts) != 2 || parts[1] != "confirm" {
		writeError(w, http.StatusNotFound, "not found")
		return
	}

	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	depositID := parts[0]
	if depositID == "" {
		writeError(w, http.StatusBadRequest, "deposit id required")
		return
	}

	var req cashConfirmRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	if req.ConfirmedBy == "" {
		writeError(w, http.StatusBadRequest, "confirmed_by is required")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	commandTag, err := h.pool.Exec(ctx, `
		UPDATE cash_deposits
		SET status = 'confirmed', confirmed_at = NOW(), confirmed_by = $2, note = COALESCE($3, note)
		WHERE id = $1 AND status = 'pending'
	`, depositID, req.ConfirmedBy, req.Note)
	if err != nil {
		h.logger.Printf("cash deposit confirm failed: %v", err)
		writeError(w, http.StatusInternalServerError, "could not confirm deposit")
		return
	}
	if commandTag.RowsAffected() == 0 {
		writeError(w, http.StatusBadRequest, "deposit not found or already confirmed")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"id": depositID, "status": "confirmed"})
}

func validateCashDeposit(req cashDepositRequest) error {
	switch {
	case req.UserID == "":
		return errors.New("user_id is required")
	case req.Currency == "":
		return errors.New("currency is required")
	case req.Amount == "":
		return errors.New("amount is required")
	case req.CreatedBy == "":
		return errors.New("created_by is required")
	default:
		return nil
	}
}
