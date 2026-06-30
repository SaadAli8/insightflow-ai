package main

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"
)

type Lead struct {
	ID          string    `json:"id"`
	FullName    string    `json:"full_name"`
	Role        string    `json:"role"`
	Company     string    `json:"company"`
	LinkedInURL string    `json:"linkedin_url"`
	WebsiteURL  string    `json:"website_url"`
	Source      string    `json:"source"`
	Notes       string    `json:"notes"`
	CreatedAt   time.Time `json:"created_at"`
}

type leadStore struct {
	mu    sync.RWMutex
	items []Lead
}

func main() {
	store := &leadStore{}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", healthHandler)
	mux.HandleFunc("GET /leads", store.listLeads)
	mux.HandleFunc("POST /leads", store.createLead)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8090"
	}

	log.Printf("lead-intake-service listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *leadStore) listLeads(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	writeJSON(w, http.StatusOK, s.items)
}

func (s *leadStore) createLead(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	var lead Lead
	if err := json.NewDecoder(r.Body).Decode(&lead); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	if err := validateLead(lead); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	lead.ID = time.Now().UTC().Format("20060102150405.000000000")
	lead.CreatedAt = time.Now().UTC()
	if lead.Source == "" {
		lead.Source = "manual"
	}

	s.mu.Lock()
	s.items = append(s.items, lead)
	s.mu.Unlock()

	writeJSON(w, http.StatusCreated, lead)
}

func validateLead(lead Lead) error {
	if strings.TrimSpace(lead.Company) == "" {
		return errors.New("company is required")
	}
	if strings.TrimSpace(lead.Role) == "" {
		return errors.New("role is required")
	}
	if lead.LinkedInURL != "" && !isLinkedInProfileURL(lead.LinkedInURL) {
		return errors.New("linkedin_url must be a valid linkedin.com/in or linkedin.com/company URL")
	}
	if lead.WebsiteURL != "" && !isHTTPURL(lead.WebsiteURL) {
		return errors.New("website_url must be a valid http(s) URL")
	}
	return nil
}

func isLinkedInProfileURL(raw string) bool {
	parsed, err := url.Parse(raw)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return false
	}
	host := strings.ToLower(strings.TrimPrefix(parsed.Host, "www."))
	path := strings.ToLower(parsed.Path)
	return host == "linkedin.com" && (strings.HasPrefix(path, "/in/") || strings.HasPrefix(path, "/company/"))
}

func isHTTPURL(raw string) bool {
	parsed, err := url.Parse(raw)
	return err == nil && (parsed.Scheme == "http" || parsed.Scheme == "https") && parsed.Host != ""
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
