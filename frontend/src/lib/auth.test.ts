import { describe, expect, it, beforeEach } from "vitest";
import {
  clearTeamId,
  clearToken,
  getTeamId,
  getToken,
  isAuthed,
  setTeamId,
  setToken,
} from "./auth";

beforeEach(() => {
  localStorage.clear();
});

describe("auth storage", () => {
  it("stores and clears the token", () => {
    expect(isAuthed()).toBe(false);
    setToken("jwt-token");
    expect(getToken()).toBe("jwt-token");
    expect(isAuthed()).toBe(true);
    clearToken();
    expect(isAuthed()).toBe(false);
    expect(getToken()).toBeNull();
  });

  it("stores and clears the active team", () => {
    expect(getTeamId()).toBeNull();
    setTeamId(7);
    expect(getTeamId()).toBe("7");
    clearTeamId();
    expect(getTeamId()).toBeNull();
  });
});
