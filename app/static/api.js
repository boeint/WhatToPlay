// The only file that talks to the backend. Every function returns a Promise
// with the server's reply, or throws an ApiError with a readable message.

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// FastAPI errors come as {"detail": "text"} or {"detail": [{loc, msg}, ...]}.
function describe(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((e) => `${e.loc.filter((p) => p !== "body").join(".")}: ${e.msg}`).join("; ");
  }
  return "Unexpected error";
}

async function request(method, path, body) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new ApiError(0, "Can't reach the server. Is it running?");
  }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      message = describe((await response.json()).detail);
    } catch { /* body wasn't JSON: keep the status text */ }
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  platforms: () => request("GET", "/api/platforms"),
  franchises: () => request("GET", "/api/franchises"),
  createFranchise: (data) => request("POST", "/api/franchises", data),
  updateFranchise: (id, changes) => request("PATCH", `/api/franchises/${id}`, changes),
  deleteFranchise: (id) => request("DELETE", `/api/franchises/${id}`),
  createGame: (franchiseId, data) => request("POST", `/api/franchises/${franchiseId}/games`, data),
  updateGame: (id, changes) => request("PATCH", `/api/games/${id}`, changes),
  deleteGame: (id) => request("DELETE", `/api/games/${id}`),
  setGameOrder: (franchiseId, gameIds) => request("PUT", `/api/franchises/${franchiseId}/game-order`, gameIds),
  setFranchiseOrder: (franchiseIds) => request("PUT", "/api/franchise-order", franchiseIds),
  importAll: (exportFile) => request("POST", "/api/import?replace=true", exportFile),

  // The export as a file to save: { blob, filename }.
  async exportAll() {
    let response;
    try {
      response = await fetch("/api/export");
    } catch {
      throw new ApiError(0, "Can't reach the server. Is it running?");
    }
    if (!response.ok) throw new ApiError(response.status, `${response.status} ${response.statusText}`);
    const filename = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") || "")?.[1]
      || "whattoplay-export.json";
    return { blob: await response.blob(), filename };
  },
};
