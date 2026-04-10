import { apiGet } from "./apiClient";

export async function getSessionStatus() {
    return apiGet("/session");
}

export async function getSessions() {
    return apiGet("/sessions");
}

export async function startSessionByLabel(label) {
    const encodedLabel = encodeURIComponent(label);
    return apiGet(`/session/start/${encodedLabel}`);
}

export async function stopSessionRequest() {
    return apiGet("/session/stop/");
}