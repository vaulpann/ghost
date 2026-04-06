const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

// Packages
export const getPackages = (params?: string) =>
  fetchAPI<{ items: any[]; total: number; page: number; per_page: number }>(
    `/api/v1/packages${params ? `?${params}` : ""}`
  );

export const getPackage = (id: string) => fetchAPI<any>(`/api/v1/packages/${id}`);

export const createPackage = (data: any) =>
  fetchAPI<any>("/api/v1/packages", { method: "POST", body: JSON.stringify(data) });

export const seedPackages = (registry: string, count: number) =>
  fetchAPI<any>("/api/v1/packages/seed", {
    method: "POST",
    body: JSON.stringify({ registry, count }),
  });

// Versions
export const getVersions = (packageId: string) =>
  fetchAPI<{ items: any[]; total: number }>(`/api/v1/packages/${packageId}/versions`);

export const getVersionDiff = (versionId: string) =>
  fetchAPI<{ diff: string; file_count: number }>(`/api/v1/versions/${versionId}/diff`);

export const reanalyzeVersion = (versionId: string) =>
  fetchAPI<any>(`/api/v1/versions/${versionId}/reanalyze`, { method: "POST" });

// Analyses
export const getAnalyses = (params?: string) =>
  fetchAPI<{ items: any[]; total: number; page: number; per_page: number }>(
    `/api/v1/analyses${params ? `?${params}` : ""}`
  );

export const getAnalysis = (id: string) => fetchAPI<any>(`/api/v1/analyses/${id}`);

// Feed & Stats
export const getFeed = (page: number = 1, perPage: number = 20) =>
  fetchAPI<{ items: any[]; total: number; page: number; per_page: number }>(
    `/api/v1/feed?page=${page}&per_page=${perPage}`
  );

export const getStats = () => fetchAPI<any>("/api/v1/stats");

// Findings
export const getFindings = (analysisId: string) =>
  fetchAPI<any[]>(`/api/v1/analyses/${analysisId}/findings`);

export const updateFinding = (findingId: string, data: any) =>
  fetchAPI<any>(`/api/v1/findings/${findingId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

// Alerts
export const getAlerts = () => fetchAPI<any[]>("/api/v1/alerts");

export const createAlert = (data: any) =>
  fetchAPI<any>("/api/v1/alerts", { method: "POST", body: JSON.stringify(data) });

export const updateAlert = (id: string, data: any) =>
  fetchAPI<any>(`/api/v1/alerts/${id}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteAlert = (id: string) =>
  fetchAPI<void>(`/api/v1/alerts/${id}`, { method: "DELETE" });

// Polling trigger
export const triggerPoll = () =>
  fetchAPI<any>("/api/v1/webhooks/poll", { method: "POST" });

// Vulnerabilities
export const getVulnerabilities = (params?: string) =>
  fetchAPI<{ items: any[]; total: number; page: number; per_page: number }>(
    `/api/v1/vulnerabilities${params ? `?${params}` : ""}`
  );

export const getVulnerability = (id: string) =>
  fetchAPI<any>(`/api/v1/vulnerabilities/${id}`);

export const getVulnerabilityScans = (params?: string) =>
  fetchAPI<{ items: any[]; total: number; page: number; per_page: number }>(
    `/api/v1/vulnerability-scans${params ? `?${params}` : ""}`
  );

export const getPackageVulnerabilities = (packageId: string) =>
  fetchAPI<any[]>(`/api/v1/packages/${packageId}/vulnerabilities`);

// Puzzles
export const getPuzzles = (params?: string) =>
  fetchAPI<{ items: any[]; total: number; page: number; per_page: number }>(
    `/api/v1/puzzles${params ? `?${params}` : ""}`
  );

export const getPuzzle = (id: string) => fetchAPI<any>(`/api/v1/puzzles/${id}`);

export const votePuzzle = (id: string, data: { selected_index: number; confidence: number; time_taken_secs?: number; session_id: string }) =>
  fetchAPI<any>(`/api/v1/puzzles/${id}/vote`, { method: "POST", body: JSON.stringify(data) });

export const getPuzzleResults = (id: string, sessionId: string) =>
  fetchAPI<any>(`/api/v1/puzzles/${id}/results?session_id=${sessionId}`);
