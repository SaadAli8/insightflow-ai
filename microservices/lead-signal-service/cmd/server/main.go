package main

import (
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

const maxBodyBytes int64 = 1500000

type WebsiteSignalRequest struct {
	WebsiteURL  string `json:"website_url"`
	CompanyName string `json:"company_name"`
}

type WebsiteSignalResponse struct {
	WebsiteURL         string   `json:"website_url"`
	FinalURL           string   `json:"final_url"`
	Domain             string   `json:"domain"`
	FinalDomain        string   `json:"final_domain"`
	Reachable          bool     `json:"reachable"`
	Redirected         bool     `json:"redirected"`
	StatusCode         int      `json:"status_code"`
	VerificationStatus string   `json:"verification_status"`
	VerificationReason string   `json:"verification_reason"`
	Confidence         int      `json:"confidence"`
	Title              string   `json:"title"`
	Description        string   `json:"description"`
	Summary            string   `json:"summary"`
	LogoURL            string   `json:"logo_url"`
	Emails             []string `json:"emails"`
	Phones             []string `json:"phones"`
	LinkedInURLs       []string `json:"linkedin_urls"`
	Keywords           []string `json:"keywords"`
	Error              string   `json:"error,omitempty"`
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", healthHandler)
	mux.HandleFunc("POST /signals/website", websiteSignalHandler)

	port := env("PORT", "8090")
	log.Printf("lead-signal-service listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func websiteSignalHandler(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	var req WebsiteSignalRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	normalized, domain, err := normalizeWebsiteURL(req.WebsiteURL)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	result := inspectWebsite(normalized, domain, req.CompanyName)
	writeJSON(w, http.StatusOK, result)
}

func inspectWebsite(target string, domain string, companyName string) WebsiteSignalResponse {
	client := &http.Client{
		Timeout: time.Duration(envInt("SIGNAL_HTTP_TIMEOUT_SECONDS", 20)) * time.Second,
	}

	request, err := http.NewRequest(http.MethodGet, target, nil)
	if err != nil {
		return unreachable(target, domain, err)
	}
	request.Header.Set("User-Agent", env("SIGNAL_USER_AGENT", "InsightFlowAILeadSignal/1.0"))
	request.Header.Set("Accept", "text/html,application/xhtml+xml")

	response, err := client.Do(request)
	if err != nil {
		return unreachable(target, domain, err)
	}
	defer response.Body.Close()

	limited := io.LimitReader(response.Body, maxBodyBytes)
	body, err := io.ReadAll(limited)
	if err != nil {
		return unreachable(target, domain, err)
	}

	html := string(body)
	text := visibleText(html)
	description := firstNonEmpty(
		metaContent(html, "description"),
		metaProperty(html, "og:description"),
	)
	title := firstNonEmpty(
		cleanText(tagContent(html, "title")),
		metaProperty(html, "og:title"),
		companyName,
	)
	finalURL := response.Request.URL.String()
	finalDomain := normalizeHost(response.Request.URL.Hostname())
	redirected := finalDomain != "" && baseDomain(finalDomain) != baseDomain(domain)
	blocked := isBlockedResponse(response.StatusCode, title, text)
	verificationStatus, verificationReason, confidence := verificationResult(response.StatusCode, redirected, blocked, domain, finalDomain)
	reachable := response.StatusCode >= 200 && response.StatusCode < 400 && !redirected && !blocked

	return WebsiteSignalResponse{
		WebsiteURL:         target,
		FinalURL:           finalURL,
		Domain:             domain,
		FinalDomain:        finalDomain,
		Reachable:          reachable,
		Redirected:         redirected,
		StatusCode:         response.StatusCode,
		VerificationStatus: verificationStatus,
		VerificationReason: verificationReason,
		Confidence:         confidence,
		Title:              title,
		Description:        cleanText(description),
		Summary:            buildSummary(title, description, text),
		LogoURL:            absoluteURL(response.Request.URL, logoURL(html)),
		Emails:             uniqueMatches(emailRegexp(), html),
		Phones:             uniqueMatches(phoneRegexp(), text),
		LinkedInURLs:       uniqueLinkedInURLs(html),
		Keywords:           extractKeywords(text),
	}
}

func normalizeWebsiteURL(raw string) (string, string, error) {
	value := strings.TrimSpace(raw)
	if value == "" {
		return "", "", errors.New("website_url is required")
	}
	if !strings.HasPrefix(value, "http://") && !strings.HasPrefix(value, "https://") {
		value = "https://" + value
	}
	parsed, err := url.Parse(value)
	if err != nil || parsed.Host == "" {
		return "", "", errors.New("website_url must be a valid URL")
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return "", "", errors.New("website_url must use http or https")
	}
	domain := strings.TrimPrefix(strings.ToLower(parsed.Hostname()), "www.")
	if domain == "" || !strings.Contains(domain, ".") {
		return "", "", errors.New("website_url must include a valid domain")
	}
	return parsed.String(), domain, nil
}

func unreachable(target string, domain string, err error) WebsiteSignalResponse {
	return WebsiteSignalResponse{
		WebsiteURL:         target,
		Domain:             domain,
		Reachable:          false,
		VerificationStatus: "unreachable",
		VerificationReason: err.Error(),
		Confidence:         10,
		Error:              err.Error(),
	}
}

func verificationResult(statusCode int, redirected bool, blocked bool, domain string, finalDomain string) (string, string, int) {
	if blocked {
		return "blocked", "Website returned a block, captcha, or access-denied response.", 20
	}
	if redirected {
		return "redirected", "Website redirected from " + domain + " to " + finalDomain + ".", 35
	}
	if statusCode >= 200 && statusCode < 400 {
		return "verified", "Official website responded successfully.", 90
	}
	return "not_verified", "Website returned HTTP " + strconv.Itoa(statusCode) + ".", 45
}

func isBlockedResponse(statusCode int, title string, text string) bool {
	if statusCode == http.StatusForbidden || statusCode == http.StatusUnauthorized || statusCode == http.StatusTooManyRequests {
		return true
	}
	haystack := strings.ToLower(title + " " + text)
	blockTerms := []string{
		"access denied",
		"verify you are human",
		"captcha",
		"blocked",
		"cloudflare",
		"temporarily unavailable",
		"request unsuccessful",
	}
	for _, term := range blockTerms {
		if strings.Contains(haystack, term) {
			return true
		}
	}
	return false
}

func metaContent(html string, name string) string {
	pattern := `(?is)<meta[^>]+name=["']` + regexp.QuoteMeta(name) + `["'][^>]+content=["']([^"']+)["'][^>]*>`
	return regexGroup(pattern, html)
}

func metaProperty(html string, property string) string {
	pattern := `(?is)<meta[^>]+property=["']` + regexp.QuoteMeta(property) + `["'][^>]+content=["']([^"']+)["'][^>]*>`
	return regexGroup(pattern, html)
}

func logoURL(html string) string {
	return firstNonEmpty(
		metaProperty(html, "og:image"),
		metaContent(html, "twitter:image"),
		linkHref(html, "apple-touch-icon"),
		linkHref(html, "icon"),
		linkHref(html, "shortcut icon"),
	)
}

func linkHref(html string, rel string) string {
	pattern := `(?is)<link[^>]+rel=["'][^"']*` + regexp.QuoteMeta(rel) + `[^"']*["'][^>]+href=["']([^"']+)["'][^>]*>`
	return regexGroup(pattern, html)
}

func absoluteURL(base *url.URL, raw string) string {
	value := strings.TrimSpace(raw)
	if value == "" || base == nil {
		return ""
	}
	if strings.HasPrefix(strings.ToLower(value), "data:") || strings.HasPrefix(strings.ToLower(value), "javascript:") {
		return ""
	}
	parsed, err := url.Parse(value)
	if err != nil {
		return ""
	}
	resolved := base.ResolveReference(parsed)
	if resolved.Scheme != "http" && resolved.Scheme != "https" {
		return ""
	}
	return resolved.String()
}

func tagContent(html string, tag string) string {
	pattern := `(?is)<` + regexp.QuoteMeta(tag) + `[^>]*>(.*?)</` + regexp.QuoteMeta(tag) + `>`
	return regexGroup(pattern, html)
}

func regexGroup(pattern string, value string) string {
	match := regexp.MustCompile(pattern).FindStringSubmatch(value)
	if len(match) < 2 {
		return ""
	}
	return htmlDecode(match[1])
}

func visibleText(html string) string {
	text := regexp.MustCompile(`(?is)<script.*?</script>`).ReplaceAllString(html, " ")
	text = regexp.MustCompile(`(?is)<style.*?</style>`).ReplaceAllString(text, " ")
	text = regexp.MustCompile(`(?is)<[^>]+>`).ReplaceAllString(text, " ")
	return cleanText(htmlDecode(text))
}

func buildSummary(title string, description string, text string) string {
	source := firstNonEmpty(description, text, title)
	if len(source) <= 280 {
		return source
	}
	return strings.TrimSpace(source[:280])
}

func cleanText(value string) string {
	value = strings.ReplaceAll(value, "\n", " ")
	value = strings.ReplaceAll(value, "\t", " ")
	return strings.Join(strings.Fields(value), " ")
}

func htmlDecode(value string) string {
	replacements := map[string]string{
		"&amp;":  "&",
		"&quot;": "\"",
		"&#34;":  "\"",
		"&#39;":  "'",
		"&apos;": "'",
		"&lt;":   "<",
		"&gt;":   ">",
	}
	for old, replacement := range replacements {
		value = strings.ReplaceAll(value, old, replacement)
	}
	return value
}

func emailRegexp() *regexp.Regexp {
	return regexp.MustCompile(`[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}`)
}

func phoneRegexp() *regexp.Regexp {
	return regexp.MustCompile(`(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}`)
}

func uniqueMatches(pattern *regexp.Regexp, value string) []string {
	seen := map[string]bool{}
	var items []string
	for _, match := range pattern.FindAllString(value, -1) {
		cleaned := strings.Trim(match, " .,;:")
		key := strings.ToLower(cleaned)
		if cleaned == "" || seen[key] {
			continue
		}
		seen[key] = true
		items = append(items, cleaned)
		if len(items) >= 10 {
			break
		}
	}
	return items
}

func uniqueLinkedInURLs(html string) []string {
	pattern := regexp.MustCompile(`https?://(?:www\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9_\-/%]+`)
	matches := uniqueMatches(pattern, html)
	for i := range matches {
		matches[i] = strings.TrimRight(matches[i], `/)"'<>`)
	}
	return matches
}

func normalizeHost(host string) string {
	return strings.TrimPrefix(strings.ToLower(strings.TrimSpace(host)), "www.")
}

func baseDomain(host string) string {
	cleaned := normalizeHost(host)
	parts := strings.Split(cleaned, ".")
	if len(parts) < 2 {
		return cleaned
	}
	return strings.Join(parts[len(parts)-2:], ".")
}

func extractKeywords(text string) []string {
	vocabulary := []string{
		"construction", "contractor", "commercial", "residential", "roofing", "remodeling",
		"concrete", "plumbing", "electrical", "hvac", "engineering", "architecture",
		"general contractor", "project management", "design build", "preconstruction",
		"saas", "software", "platform", "automation", "ai", "analytics",
	}
	lower := strings.ToLower(text)
	var found []string
	for _, word := range vocabulary {
		if strings.Contains(lower, word) {
			found = append(found, word)
		}
	}
	sort.Strings(found)
	return found
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		cleaned := cleanText(value)
		if cleaned != "" {
			return cleaned
		}
	}
	return ""
}

func env(key string, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}

func envInt(key string, fallback int) int {
	value, err := strconv.Atoi(strings.TrimSpace(os.Getenv(key)))
	if err != nil || value <= 0 {
		return fallback
	}
	return value
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
