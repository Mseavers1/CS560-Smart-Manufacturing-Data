// const API_URL = import.meta.env.VITE_API_URL;

// async function handleResponse(response) {
//     if (!response.ok) {
//         let errorMessage = `API request failed with status ${response.status}`;

//         try {
//             const errorData = await response.json();
//             if (errorData?.error) {
//                 errorMessage = errorData.error;
//             }
//         } catch {
//             // Ignore JSON parsing errors and keep default message
//         }

//         throw new Error(errorMessage);
//     }

//     return response.json();
// }

// export async function apiGet(path) {
//     const response = await fetch(`${API_URL}${path}`, {
//         method: "GET",
//     });

//     return handleResponse(response);
// }

// export async function apiPost(path, body) {
//     const response = await fetch(`${API_URL}${path}`, {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json",
//         },
//         body: JSON.stringify(body),
//     });

//     return handleResponse(response);
// }


// testing

const API_URL = import.meta.env.VITE_API_URL;
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";

function mockResponse(path, method = "GET", body = null) {
    if (method === "GET" && path === "/session") {
        return { data: false };
    }

    if (method === "GET" && path === "/sessions") {
        return {
            data: [
                { id: 305 },
                { id: 304 },
                { id: 303 },
            ],
        };
    }

    if (method === "GET" && path.startsWith("/session/start/")) {
        return { success: true };
    }

    if (method === "GET" && path === "/session/stop/") {
        return { success: true };
    }

    if (method === "POST" && path.startsWith("/send/")) {
        return { success: true, echo: body };
    }

    return { success: true, data: null };
}

async function handleResponse(response) {
    if (!response.ok) {
        let errorMessage = `API request failed with status ${response.status}`;

        try {
            const errorData = await response.json();
            if (errorData?.error) {
                errorMessage = errorData.error;
            }
        } catch {
            // Ignore JSON parsing errors and keep default message
        }

        throw new Error(errorMessage);
    }

    return response.json();
}

function resolveApiUrl(path) {
    if (/^https?:\/\//i.test(path)) {
        return path;
    }

    if (!API_URL) {
        throw new Error("VITE_API_URL is not configured.");
    }

    return `${API_URL}${path}`;
}

export function getApiBaseUrl() {
    return API_URL || "";
}

export function isMockApiEnabled() {
    return USE_MOCK_API;
}

export async function apiRequest(path, options = {}) {
    const { method = "GET", body } = options;

    if (USE_MOCK_API) {
        return mockResponse(path, method, body);
    }

    const requestOptions = {
        method,
        headers: {},
    };

    if (body !== undefined) {
        requestOptions.headers["Content-Type"] = "application/json";
        requestOptions.body = typeof body === "string" ? body : JSON.stringify(body);
    }

    const response = await fetch(resolveApiUrl(path), requestOptions);

    return handleResponse(response);
}

export async function apiGet(path) {
    return apiRequest(path, { method: "GET" });
}

export async function apiPost(path, body) {
    return apiRequest(path, { method: "POST", body });
}
