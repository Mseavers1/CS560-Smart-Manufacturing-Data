import { useEffect, useMemo, useState } from "react";
import { apiRequest, getApiBaseUrl } from "./api/apiClient";

const TEXT_FILE_TYPES = new Set(["md", "txt", "json", "csv", "log"]);
const IMAGE_FILE_TYPES = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg"]);

const API_ENDPOINTS = [
    {
        id: "session-status",
        method: "GET",
        path: "/session",
        title: "Session Status",
        description: "Returns whether a session is currently active.",
        tags: ["status", "session", "dashboard"],
    },
    {
        id: "session-list",
        method: "GET",
        path: "/sessions",
        title: "Session History",
        description: "Lists recent sessions so operators can inspect the latest run.",
        tags: ["history", "session", "records"],
    },
    {
        id: "session-start",
        method: "GET",
        path: "/session/start/demo-session?is_test_session=false",
        title: "Start Session",
        description: "Starts a new session; set is_test_session=false for real runs.",
        tags: ["start", "session", "control", "is_test_session"],
    },
    {
        id: "session-stop",
        method: "GET",
        path: "/session/stop",
        title: "Stop Session",
        description: "Stops the currently active session.",
        tags: ["stop", "session", "control"],
    },
    {
        id: "backup-list",
        method: "GET",
        path: "/backup/list",
        title: "List Backups",
        description: "Returns available backup files from mounted backup storage.",
        tags: ["backup", "list", "storage"],
    },
    {
        id: "backup-run",
        method: "GET",
        path: "/backup",
        title: "Run Backup",
        description: "Creates a backup snapshot and returns status plus file path.",
        tags: ["backup", "create", "database"],
    },
    {
        id: "backup-restore",
        method: "POST",
        path: "/backup/restore/backup-file.dump",
        title: "Restore Backup",
        description: "Restores a specific backup file by filename.",
        tags: ["backup", "restore", "recovery"],
    },
    {
        id: "send-message",
        method: "POST",
        path: "/send/misc",
        title: "Send Dashboard Message",
        description: "Posts an operator message to one of the dashboard channels.",
        tags: ["message", "post", "dashboard"],
        bodyTemplate: '{\n  "type": "info",\n  "text": "Hello from the Info page"\n}',
    },
];

function getFileType(path = "") {
    const match = path.toLowerCase().match(/\.([a-z0-9]+)$/);
    return match ? match[1] : "file";
}

function formatFileTypeLabel(type) {
    return type.toUpperCase();
}

function matchesQuery(fields, query) {
    if (!query) {
        return true;
    }

    const haystack = fields
        .flat()
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

    return haystack.includes(query.toLowerCase());
}

function renderInlineMarkdown(text) {
    const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);

    return tokens.map((token, index) => {
        if (token.startsWith("`") && token.endsWith("`")) {
            return (
                <code
                    key={`${token}-${index}`}
                    className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.92em] text-slate-700"
                >
                    {token.slice(1, -1)}
                </code>
            );
        }

        if (token.startsWith("**") && token.endsWith("**")) {
            return (
                <strong key={`${token}-${index}`} className="font-semibold text-slate-900">
                    {token.slice(2, -2)}
                </strong>
            );
        }

        return token;
    });
}

function renderMarkdown(content) {
    const lines = content.split(/\r?\n/);
    const blocks = [];
    let paragraph = [];
    let listItems = [];
    let codeLines = [];
    let inCodeBlock = false;

    const flushParagraph = () => {
        if (!paragraph.length) {
            return;
        }

        blocks.push({
            type: "paragraph",
            content: paragraph.join(" "),
        });
        paragraph = [];
    };

    const flushList = () => {
        if (!listItems.length) {
            return;
        }

        blocks.push({
            type: "list",
            items: [...listItems],
        });
        listItems = [];
    };

    const flushCode = () => {
        if (!codeLines.length) {
            return;
        }

        blocks.push({
            type: "code",
            content: codeLines.join("\n"),
        });
        codeLines = [];
    };

    lines.forEach((line) => {
        const trimmed = line.trimEnd();

        if (trimmed.startsWith("```")) {
            flushParagraph();
            flushList();

            if (inCodeBlock) {
                flushCode();
                inCodeBlock = false;
            } else {
                inCodeBlock = true;
            }

            return;
        }

        if (inCodeBlock) {
            codeLines.push(line);
            return;
        }

        if (!trimmed) {
            flushParagraph();
            flushList();
            return;
        }

        if (trimmed.startsWith("# ")) {
            flushParagraph();
            flushList();
            blocks.push({ type: "h1", content: trimmed.slice(2) });
            return;
        }

        if (trimmed.startsWith("## ")) {
            flushParagraph();
            flushList();
            blocks.push({ type: "h2", content: trimmed.slice(3) });
            return;
        }

        if (trimmed.startsWith("### ")) {
            flushParagraph();
            flushList();
            blocks.push({ type: "h3", content: trimmed.slice(4) });
            return;
        }

        if (/^[-*]\s+/.test(trimmed)) {
            flushParagraph();
            listItems.push(trimmed.replace(/^[-*]\s+/, ""));
            return;
        }

        paragraph.push(trimmed);
    });

    flushParagraph();
    flushList();
    flushCode();

    return blocks.map((block, index) => {
        if (block.type === "h1") {
            return (
                <h1 key={index} className="text-2xl font-semibold tracking-tight text-slate-900">
                    {renderInlineMarkdown(block.content)}
                </h1>
            );
        }

        if (block.type === "h2") {
            return (
                <h2
                    key={index}
                    className="mt-6 border-t border-slate-200 pt-5 text-xl font-semibold text-slate-900"
                >
                    {renderInlineMarkdown(block.content)}
                </h2>
            );
        }

        if (block.type === "h3") {
            return (
                <h3 key={index} className="mt-5 text-lg font-semibold text-slate-800">
                    {renderInlineMarkdown(block.content)}
                </h3>
            );
        }

        if (block.type === "list") {
            return (
                <ul key={index} className="space-y-2 pl-5 text-sm leading-7 text-slate-700">
                    {block.items.map((item, itemIndex) => (
                        <li key={`${item}-${itemIndex}`} className="list-disc">
                            {renderInlineMarkdown(item)}
                        </li>
                    ))}
                </ul>
            );
        }

        if (block.type === "code") {
            return (
                <pre
                    key={index}
                    className="overflow-x-auto rounded-2xl bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-100"
                >
                    <code>{block.content}</code>
                </pre>
            );
        }

        return (
            <p key={index} className="text-sm leading-7 text-slate-700">
                {renderInlineMarkdown(block.content)}
            </p>
        );
    });
}

function DocumentViewer({ document, content, isLoading, error }) {
    const type = document?.type || getFileType(document?.path);

    if (!document) {
        return (
            <div className="flex min-h-[24rem] items-center justify-center rounded-[28px] border border-dashed border-slate-300 bg-white/80 p-8 text-center text-sm text-slate-500">
                Select a document to preview it here.
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="flex min-h-[24rem] items-center justify-center rounded-[28px] border border-slate-200 bg-white/90 p-8 text-sm text-slate-500">
                Loading {document.title}...
            </div>
        );
    }

    if (error) {
        return (
            <div className="rounded-[28px] border border-red-200 bg-red-50 p-6 text-sm text-red-700">
                {error}
            </div>
        );
    }

    if (type === "md") {
        return (
            <article className="min-h-[24rem] space-y-4 rounded-[28px] border border-slate-200 bg-white/95 p-6 shadow-sm">
                {renderMarkdown(content)}
            </article>
        );
    }

    if (TEXT_FILE_TYPES.has(type)) {
        return (
            <div className="min-h-[24rem] rounded-[28px] border border-slate-200 bg-white/95 p-6 shadow-sm">
                <pre className="whitespace-pre-wrap break-words font-mono text-sm leading-6 text-slate-700">
                    {content}
                </pre>
            </div>
        );
    }

    if (type === "pdf") {
        return (
            <div className="space-y-4 rounded-[28px] border border-slate-200 bg-white/95 p-4 shadow-sm">
                <iframe
                    title={document.title}
                    src={document.path}
                    className="min-h-[30rem] w-full rounded-2xl border border-slate-200"
                />
                <a
                    href={document.path}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                >
                    Open PDF in a new tab
                </a>
            </div>
        );
    }

    if (IMAGE_FILE_TYPES.has(type)) {
        return (
            <div className="space-y-4 rounded-[28px] border border-slate-200 bg-white/95 p-4 shadow-sm">
                <img
                    src={document.path}
                    alt={document.title}
                    className="max-h-[32rem] w-full rounded-2xl border border-slate-200 object-contain"
                />
                <a
                    href={document.path}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                >
                    Open file
                </a>
            </div>
        );
    }

    return (
        <div className="space-y-4 rounded-[28px] border border-slate-200 bg-white/95 p-6 shadow-sm">
            <p className="text-sm leading-7 text-slate-700">
                This file type does not have an inline preview yet, but it is ready to open or
                download.
            </p>
            <a
                href={document.path}
                target="_blank"
                rel="noreferrer"
                className="inline-flex rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
            >
                Open {document.title}
            </a>
        </div>
    );
}

export default function HomePage() {
    const [documents, setDocuments] = useState([]);
    const [manifestError, setManifestError] = useState("");
    const [selectedDocumentId, setSelectedDocumentId] = useState("");
    const [documentSearch, setDocumentSearch] = useState("");
    const [apiSearch, setApiSearch] = useState("");
    const [documentContent, setDocumentContent] = useState("");
    const [contentError, setContentError] = useState("");
    const [isContentLoading, setIsContentLoading] = useState(false);
    const [apiMethod, setApiMethod] = useState("GET");
    const [apiPath, setApiPath] = useState("/session");
    const [apiBody, setApiBody] = useState("");
    const [apiResult, setApiResult] = useState("");
    const [apiError, setApiError] = useState("");
    const [isApiLoading, setIsApiLoading] = useState(false);

    useEffect(() => {
        let ignore = false;

        const loadManifest = async () => {
            try {
                const response = await fetch(`/info/manifest.json?v=${Date.now()}`, {
                    cache: "no-store",
                });

                if (!response.ok) {
                    throw new Error(`Manifest request failed with status ${response.status}`);
                }

                const manifest = await response.json();
                const manifestDocuments = Array.isArray(manifest.documents) ? manifest.documents : [];

                if (!ignore) {
                    setDocuments(manifestDocuments);
                    setSelectedDocumentId(manifestDocuments[0]?.id || "");
                    setManifestError("");
                }
            } catch (error) {
                if (!ignore) {
                    setManifestError(
                        error instanceof Error ? error.message : "Unable to load Info documents.",
                    );
                }
            }
        };

        loadManifest();

        return () => {
            ignore = true;
        };
    }, []);

    const filteredDocuments = useMemo(() => {
        return documents.filter((document) =>
            matchesQuery(
                [
                    document.title,
                    document.description,
                    document.category,
                    document.path,
                    document.tags || [],
                ],
                documentSearch,
            ),
        );
    }, [documentSearch, documents]);

    const selectedDocument =
        filteredDocuments.find((document) => document.id === selectedDocumentId) ||
        documents.find((document) => document.id === selectedDocumentId) ||
        filteredDocuments[0] ||
        documents[0] ||
        null;

    useEffect(() => {
        if (!selectedDocument || selectedDocument.id === selectedDocumentId) {
            return;
        }

        setSelectedDocumentId(selectedDocument.id);
    }, [selectedDocument, selectedDocumentId]);

    useEffect(() => {
        let ignore = false;

        const loadContent = async () => {
            if (!selectedDocument) {
                setDocumentContent("");
                setContentError("");
                return;
            }

            const type = selectedDocument.type || getFileType(selectedDocument.path);

            if (!TEXT_FILE_TYPES.has(type)) {
                setDocumentContent("");
                setContentError("");
                return;
            }

            setIsContentLoading(true);
            setContentError("");

            try {
                const response = await fetch(selectedDocument.path);

                if (!response.ok) {
                    throw new Error(`Document request failed with status ${response.status}`);
                }

                const text = await response.text();

                if (!ignore) {
                    setDocumentContent(text);
                }
            } catch (error) {
                if (!ignore) {
                    setContentError(
                        error instanceof Error
                            ? error.message
                            : "Unable to load the selected document.",
                    );
                }
            } finally {
                if (!ignore) {
                    setIsContentLoading(false);
                }
            }
        };

        loadContent();

        return () => {
            ignore = true;
        };
    }, [selectedDocument]);

    const filteredEndpoints = useMemo(() => {
        return API_ENDPOINTS.filter((endpoint) =>
            matchesQuery(
                [endpoint.title, endpoint.description, endpoint.method, endpoint.path, endpoint.tags],
                apiSearch,
            ),
        );
    }, [apiSearch]);

    const handleEndpointPick = (endpoint) => {
        setApiMethod(endpoint.method);
        setApiPath(endpoint.path);
        setApiBody(endpoint.bodyTemplate || "");
        setApiError("");
    };

    const handleApiRequest = async (event) => {
        event.preventDefault();
        setIsApiLoading(true);
        setApiError("");
        setApiResult("");

        try {
            let parsedBody;

            if (apiMethod !== "GET" && apiBody.trim()) {
                parsedBody = JSON.parse(apiBody);
            }

            const response = await apiRequest(apiPath, {
                method: apiMethod,
                body: apiMethod === "GET" ? undefined : parsedBody,
            });

            setApiResult(JSON.stringify(response, null, 2));
        } catch (error) {
            setApiError(
                error instanceof Error ? error.message : "Unable to complete the API request.",
            );
        } finally {
            setIsApiLoading(false);
        }
    };

    const documentCountLabel = `${filteredDocuments.length} of ${documents.length || 0} files`;
    const apiBaseLabel = getApiBaseUrl() || "No API base URL configured";

    return (
        <div className="min-h-screen bg-transparent text-slate-900">
            <div className="mx-auto w-full max-w-7xl px-4 pb-10 pt-24 sm:px-6 lg:px-8">
                <section className="animate-fade-up overflow-hidden rounded-[32px] border border-slate-200/70 bg-[linear-gradient(135deg,rgba(255,255,255,0.92),rgba(242,246,244,0.92))] shadow-[0_24px_80px_rgba(15,23,42,0.08)]">
                    <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1.4fr_0.9fr] lg:px-8 lg:py-10">
                        <div className="space-y-5">
                            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">
                                Info Center
                            </div>
                            <div className="space-y-3">
                                <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
                                    SOPs, references, and live API access in one place.
                                </h1>
                                <p className="max-w-2xl text-sm leading-7 text-slate-600 sm:text-base">
                                    This page now works as an operations library. Teams can browse
                                    plain-text guides, preview markdown and PDF files, and run quick
                                    API checks without leaving the dashboard.
                                </p>
                            </div>
                        </div>

                        <div className="animate-fade-up-delayed rounded-[28px] border border-slate-200 bg-slate-950 p-5 text-left text-slate-50 shadow-lg">
                            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
                                Access Snapshot
                            </p>
                            <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                <div className="rounded-2xl bg-white/10 p-4">
                                    <div className="text-2xl font-semibold">{documents.length}</div>
                                    <div className="mt-1 text-sm text-slate-300">Indexed files</div>
                                </div>
                                <div className="rounded-2xl bg-white/10 p-4">
                                    <div className="text-2xl font-semibold">{API_ENDPOINTS.length}</div>
                                    <div className="mt-1 text-sm text-slate-300">Saved endpoints</div>
                                </div>
                            </div>
                            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-slate-300">
                                Base connection: <span className="font-medium text-white">{apiBaseLabel}</span>
                            </div>
                        </div>
                    </div>
                </section>

                <div className="mt-8 grid gap-6 xl:grid-cols-[0.95fr_1.35fr_1fr]">
                    <section className="animate-fade-up rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                                    Library
                                </p>
                                <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                                    Info files
                                </h2>
                            </div>
                            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                                {documentCountLabel}
                            </span>
                        </div>

                        <label className="mt-5 block">
                            <span className="sr-only">Search files</span>
                            <input
                                type="search"
                                value={documentSearch}
                                onChange={(event) => setDocumentSearch(event.target.value)}
                                placeholder="Search SOPs, tags, filenames..."
                                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
                            />
                        </label>

                        {manifestError ? (
                            <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                                {manifestError}
                            </div>
                        ) : null}

                        <div className="mt-5 space-y-3">
                            {filteredDocuments.map((document) => {
                                const type = document.type || getFileType(document.path);
                                const isActive = selectedDocument?.id === document.id;

                                return (
                                    <button
                                        type="button"
                                        key={document.id}
                                        onClick={() => setSelectedDocumentId(document.id)}
                                        className={`w-full rounded-3xl border p-4 text-left transition ${
                                            isActive
                                                ? "border-slate-900 bg-slate-900 text-white shadow-lg"
                                                : "border-slate-200 bg-slate-50 hover:border-cyan-300 hover:bg-cyan-50"
                                        }`}
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <div className="text-base font-semibold">
                                                    {document.title}
                                                </div>
                                                <div
                                                    className={`mt-1 text-sm ${
                                                        isActive ? "text-slate-300" : "text-slate-600"
                                                    }`}
                                                >
                                                    {document.description}
                                                </div>
                                            </div>
                                            <span
                                                className={`rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-[0.16em] ${
                                                    isActive
                                                        ? "bg-white/10 text-cyan-200"
                                                        : "bg-white text-slate-600"
                                                }`}
                                            >
                                                {formatFileTypeLabel(type)}
                                            </span>
                                        </div>
                                        <div
                                            className={`mt-3 flex flex-wrap gap-2 text-xs ${
                                                isActive ? "text-slate-300" : "text-slate-500"
                                            }`}
                                        >
                                            <span>{document.category}</span>
                                            {(document.tags || []).slice(0, 3).map((tag) => (
                                                <span
                                                    key={tag}
                                                    className={`rounded-full px-2 py-1 ${
                                                        isActive
                                                            ? "bg-white/10"
                                                            : "bg-slate-200/70"
                                                    }`}
                                                >
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    </button>
                                );
                            })}

                            {!filteredDocuments.length ? (
                                <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                                    No files matched that search. Update `public/info/manifest.json`
                                    to add more SOPs, PDFs, or reference files.
                                </div>
                            ) : null}
                        </div>
                    </section>

                    <section className="animate-fade-up-delayed space-y-4">
                        <div className="rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-sm">
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                                        Preview
                                    </p>
                                    <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                                        {selectedDocument?.title || "Document viewer"}
                                    </h2>
                                </div>
                                {selectedDocument ? (
                                    <a
                                        href={selectedDocument.path}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-900 hover:bg-slate-900 hover:text-white"
                                    >
                                        Open source file
                                    </a>
                                ) : null}
                            </div>
                            {selectedDocument?.notes ? (
                                <p className="mt-3 text-sm leading-7 text-slate-600">
                                    {selectedDocument.notes}
                                </p>
                            ) : null}
                        </div>

                        <DocumentViewer
                            document={selectedDocument}
                            content={documentContent}
                            isLoading={isContentLoading}
                            error={contentError}
                        />
                    </section>

                    <section className="animate-fade-up rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-sm">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                                API Explorer
                            </p>
                            <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                                Search and run endpoints
                            </h2>
                            <p className="mt-2 text-sm leading-7 text-slate-600">
                                Filter the saved endpoint catalog, then launch a quick request to
                                confirm the backend is responding.
                            </p>
                        </div>

                        <label className="mt-5 block">
                            <span className="sr-only">Search API catalog</span>
                            <input
                                type="search"
                                value={apiSearch}
                                onChange={(event) => setApiSearch(event.target.value)}
                                placeholder="Search session, message, control..."
                                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
                            />
                        </label>

                        <div className="mt-5 space-y-3">
                            {filteredEndpoints.map((endpoint) => (
                                <button
                                    type="button"
                                    key={endpoint.id}
                                    onClick={() => handleEndpointPick(endpoint)}
                                    className="w-full rounded-3xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-cyan-300 hover:bg-cyan-50"
                                >
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="text-sm font-semibold text-slate-900">
                                            {endpoint.title}
                                        </div>
                                        <span className="rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-semibold tracking-[0.16em] text-white">
                                            {endpoint.method}
                                        </span>
                                    </div>
                                    <div className="mt-2 font-mono text-xs text-slate-600">
                                        {endpoint.path}
                                    </div>
                                    <p className="mt-2 text-sm text-slate-600">
                                        {endpoint.description}
                                    </p>
                                </button>
                            ))}
                        </div>

                        <form className="mt-6 space-y-4" onSubmit={handleApiRequest}>
                            <div className="grid gap-3 sm:grid-cols-[9rem_1fr]">
                                <label className="space-y-2">
                                    <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                        Method
                                    </span>
                                    <select
                                        value={apiMethod}
                                        onChange={(event) => setApiMethod(event.target.value)}
                                        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
                                    >
                                        <option value="GET">GET</option>
                                        <option value="POST">POST</option>
                                    </select>
                                </label>

                                <label className="space-y-2">
                                    <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                        Path
                                    </span>
                                    <input
                                        type="text"
                                        value={apiPath}
                                        onChange={(event) => setApiPath(event.target.value)}
                                        placeholder="/session"
                                        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm text-slate-700 outline-none transition focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
                                    />
                                </label>
                            </div>

                            <label className="block space-y-2">
                                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                                    JSON body
                                </span>
                                <textarea
                                    value={apiBody}
                                    onChange={(event) => setApiBody(event.target.value)}
                                    placeholder='{"type": "info", "text": "Hello"}'
                                    rows={6}
                                    className="w-full rounded-3xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm text-slate-700 outline-none transition focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100"
                                />
                            </label>

                            <button
                                type="submit"
                                disabled={isApiLoading}
                                className="inline-flex rounded-full bg-cyan-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:bg-slate-400"
                            >
                                {isApiLoading ? "Running request..." : "Run request"}
                            </button>
                        </form>

                        {apiError ? (
                            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                                {apiError}
                            </div>
                        ) : null}

                        <div className="mt-4 rounded-[28px] border border-slate-200 bg-slate-950 p-4">
                            <div className="flex items-center justify-between gap-3">
                                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
                                    Response
                                </p>
                                <span className="text-xs text-slate-400">{apiBaseLabel}</span>
                            </div>
                            <pre className="mt-3 min-h-[16rem] whitespace-pre-wrap break-words font-mono text-sm leading-6 text-slate-100">
                                {apiResult || "Run a request to inspect the JSON response here."}
                            </pre>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}
