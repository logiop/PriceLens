const TOKEN_KEY = "pricelens_token";
const TEAM_KEY = "pricelens_team";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthed(): boolean {
  return Boolean(getToken());
}

export function getTeamId(): string | null {
  return localStorage.getItem(TEAM_KEY);
}

export function setTeamId(teamId: number): void {
  localStorage.setItem(TEAM_KEY, String(teamId));
}

export function clearTeamId(): void {
  localStorage.removeItem(TEAM_KEY);
}
