package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"math/big"
	"net/http"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
)

type orderRequest struct {
	UserID string `json:"user_id"`
	Side   string `json:"side"`
	Market string `json:"market"`
	Price  string `json:"price"`
	Amount string `json:"amount"`
}

type orderCancelRequest struct {
	CancelledBy string `json:"cancelled_by"`
}

type orderRow struct {
	ID        string
	Side      string
	Market    string
	Price     string
	Remaining string
}

type transactioner interface {
	QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
	Exec(ctx context.Context, sql string, arguments ...any) (pgx.CommandTag, error)
}

func (h *Handler) handleOrders(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req orderRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	if err := validateOrderRequest(req); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	var id string
	query := `
		INSERT INTO orders (user_id, side, market, price, amount, remaining, status)
		VALUES ($1, $2, $3, $4, $5, $5, 'open')
		RETURNING id
	`
	if err := h.pool.QueryRow(ctx, query, req.UserID, strings.ToLower(req.Side), strings.ToUpper(req.Market), req.Price, req.Amount).Scan(&id); err != nil {
		h.logger.Printf("order insert failed: %v", err)
		writeError(w, http.StatusInternalServerError, "could not create order")
		return
	}

	writeJSON(w, http.StatusCreated, map[string]string{"id": id, "status": "open"})
}

func (h *Handler) handleOrderAction(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/orders/")
	parts := strings.Split(path, "/")
	if len(parts) != 2 || parts[1] != "cancel" {
		writeError(w, http.StatusNotFound, "not found")
		return
	}

	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	orderID := parts[0]
	if orderID == "" {
		writeError(w, http.StatusBadRequest, "order id required")
		return
	}

	var req orderCancelRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json")
		return
	}
	if req.CancelledBy == "" {
		writeError(w, http.StatusBadRequest, "cancelled_by is required")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	commandTag, err := h.pool.Exec(ctx, `
		UPDATE orders
		SET status = 'cancelled', cancelled_at = NOW(), cancelled_by = $2
		WHERE id = $1 AND status = 'open'
	`, orderID, req.CancelledBy)
	if err != nil {
		h.logger.Printf("order cancel failed: %v", err)
		writeError(w, http.StatusInternalServerError, "could not cancel order")
		return
	}
	if commandTag.RowsAffected() == 0 {
		writeError(w, http.StatusBadRequest, "order not found or already closed")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"id": orderID, "status": "cancelled"})
}

func (h *Handler) handleOrderMatch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	market := r.URL.Query().Get("market")
	if market == "" {
		writeError(w, http.StatusBadRequest, "market is required")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	trade, err := h.matchOnce(ctx, strings.ToUpper(market))
	if err != nil {
		h.logger.Printf("match failed: %v", err)
		writeError(w, http.StatusInternalServerError, "match failed")
		return
	}
	if trade == nil {
		writeJSON(w, http.StatusOK, map[string]string{"status": "no_match"})
		return
	}

	writeJSON(w, http.StatusOK, trade)
}

func (h *Handler) matchOnce(ctx context.Context, market string) (map[string]string, error) {
	tx, err := h.pool.Begin(ctx)
	if err != nil {
		return nil, err
	}
	defer func() {
		if err != nil {
			_ = tx.Rollback(ctx)
		}
	}()

	buy, err := fetchBestOrder(ctx, tx, market, "buy")
	if err != nil || buy == nil {
		_ = tx.Rollback(ctx)
		return nil, err
	}

	sell, err := fetchBestOrder(ctx, tx, market, "sell")
	if err != nil || sell == nil {
		_ = tx.Rollback(ctx)
		return nil, err
	}

	compare, err := compareNumeric(buy.Price, sell.Price)
	if err != nil {
		_ = tx.Rollback(ctx)
		return nil, err
	}
	if compare < 0 {
		_ = tx.Rollback(ctx)
		return nil, nil
	}

	amount, err := minNumeric(buy.Remaining, sell.Remaining)
	if err != nil {
		_ = tx.Rollback(ctx)
		return nil, err
	}

	var tradeID string
	tradeQuery := `
		INSERT INTO trades (buy_order_id, sell_order_id, market, price, amount)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id
	`
	if err := tx.QueryRow(ctx, tradeQuery, buy.ID, sell.ID, market, sell.Price, amount).Scan(&tradeID); err != nil {
		_ = tx.Rollback(ctx)
		return nil, err
	}

	if err := updateOrderFill(ctx, tx, buy.ID, amount); err != nil {
		_ = tx.Rollback(ctx)
		return nil, err
	}
	if err := updateOrderFill(ctx, tx, sell.ID, amount); err != nil {
		_ = tx.Rollback(ctx)
		return nil, err
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, err
	}

	return map[string]string{
		"id":     tradeID,
		"market": market,
		"price":  sell.Price,
		"amount": amount,
	}, nil
}

func fetchBestOrder(ctx context.Context, tx transactioner, market string, side string) (*orderRow, error) {
	query := `
		SELECT id, side, market, price, remaining
		FROM orders
		WHERE market = $1 AND side = $2 AND status = 'open'
		ORDER BY
			CASE WHEN $2 = 'buy' THEN price END DESC,
			CASE WHEN $2 = 'sell' THEN price END ASC,
			created_at ASC
		LIMIT 1
		FOR UPDATE SKIP LOCKED
	`

	var row orderRow
	if err := tx.QueryRow(ctx, query, market, side).Scan(&row.ID, &row.Side, &row.Market, &row.Price, &row.Remaining); err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			return nil, err
		}
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &row, nil
}

func updateOrderFill(ctx context.Context, tx transactioner, orderID string, amount string) error {
	query := `
		UPDATE orders
		SET remaining = remaining - $2::numeric,
			status = CASE WHEN remaining - $2::numeric <= 0 THEN 'filled' ELSE status END,
			filled_at = CASE WHEN remaining - $2::numeric <= 0 THEN NOW() ELSE filled_at END
		WHERE id = $1
	`
	_, err := tx.Exec(ctx, query, orderID, amount)
	return err
}

func validateOrderRequest(req orderRequest) error {
	switch {
	case req.UserID == "":
		return errors.New("user_id is required")
	case req.Side == "":
		return errors.New("side is required")
	case req.Market == "":
		return errors.New("market is required")
	case req.Price == "":
		return errors.New("price is required")
	case req.Amount == "":
		return errors.New("amount is required")
	}

	side := strings.ToLower(req.Side)
	if side != "buy" && side != "sell" {
		return errors.New("side must be buy or sell")
	}
	if _, ok := new(big.Rat).SetString(req.Price); !ok {
		return errors.New("price must be numeric")
	}
	if _, ok := new(big.Rat).SetString(req.Amount); !ok {
		return errors.New("amount must be numeric")
	}
	return nil
}

func compareNumeric(left string, right string) (int, error) {
	l, ok := new(big.Rat).SetString(left)
	if !ok {
		return 0, errors.New("invalid numeric value")
	}
	r, ok := new(big.Rat).SetString(right)
	if !ok {
		return 0, errors.New("invalid numeric value")
	}
	return l.Cmp(r), nil
}

func minNumeric(left string, right string) (string, error) {
	l, ok := new(big.Rat).SetString(left)
	if !ok {
		return "", errors.New("invalid numeric value")
	}
	r, ok := new(big.Rat).SetString(right)
	if !ok {
		return "", errors.New("invalid numeric value")
	}
	if l.Cmp(r) <= 0 {
		return left, nil
	}
	return right, nil
}
