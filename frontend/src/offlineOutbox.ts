export type OfflineExpensePayload = {
  supplier: number | null;
  category: number;
  period: number;
  expense_date: string;
  description: string;
  amount: string;
  payment_method: string;
  reference: string;
};

type StoredDraft = {
  idempotencyKey: string;
  scope: string;
  userId: number;
  schoolId: number;
  createdAt: string;
  iv: ArrayBuffer;
  ciphertext: ArrayBuffer;
  resourceType?: "expense" | "purchase_order";
  state: "queued" | "needs_attention";
  lastError?: string;
};

type StoredKey = { scope: string; key: CryptoKey };
const DB_NAME = "precious-schoolbooks-offline-v1";
const DB_VERSION = 1;

function scopeFor(userId: number, schoolId: number) {
  return `${userId}:${schoolId}`;
}

function openDatabase(): Promise<IDBDatabase> {
  if (!globalThis.indexedDB || !globalThis.crypto?.subtle) {
    return Promise.reject(new Error("Secure offline storage is unavailable in this browser. Use a supported browser over HTTPS."));
  }
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("drafts")) {
        const store = db.createObjectStore("drafts", { keyPath: "idempotencyKey" });
        store.createIndex("scope", "scope", { unique: false });
      }
      if (!db.objectStoreNames.contains("keys")) db.createObjectStore("keys", { keyPath: "scope" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Could not open offline storage."));
  });
}

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Offline storage request failed."));
  });
}

async function encryptionKey(db: IDBDatabase, scope: string): Promise<CryptoKey> {
  const read = db.transaction("keys", "readonly");
  const saved = await requestResult(read.objectStore("keys").get(scope)) as StoredKey | undefined;
  if (saved?.key) return saved.key;
  const key = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
  const write = db.transaction("keys", "readwrite");
  write.objectStore("keys").put({ scope, key } satisfies StoredKey);
  await new Promise<void>((resolve, reject) => {
    write.oncomplete = () => resolve();
    write.onerror = () => reject(write.error || new Error("Could not store offline encryption key."));
    write.onabort = () => reject(write.error || new Error("Offline key storage was interrupted."));
  });
  return key;
}

export async function queueExpenseDraft(payload: OfflineExpensePayload, userId: number, schoolId: number) {
  return queueDraft("expense", payload, userId, schoolId);
}

export type OfflinePurchaseOrderPayload = {
  supplier: number;
  period: number;
  order_date: string;
  expected_date?: string | null;
  description: string;
  lines: { description: string; quantity: string; unit_cost: string }[];
};

export async function queuePurchaseOrderDraft(payload: OfflinePurchaseOrderPayload, userId: number, schoolId: number) {
  return queueDraft("purchase_order", payload, userId, schoolId);
}

async function queueDraft(resourceType: "expense" | "purchase_order", payload: OfflineExpensePayload | OfflinePurchaseOrderPayload, userId: number, schoolId: number) {
  const db = await openDatabase();
  try {
    const scope = scopeFor(userId, schoolId);
    const key = await encryptionKey(db, scope);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const plaintext = new TextEncoder().encode(JSON.stringify(payload));
    const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext);
    const draft: StoredDraft = {
      idempotencyKey: crypto.randomUUID(), scope, userId, schoolId,
      createdAt: new Date().toISOString(), iv: iv.buffer.slice(0), ciphertext,
      resourceType, state: "queued",
    };
    const tx = db.transaction("drafts", "readwrite");
    tx.objectStore("drafts").add(draft);
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error("Could not save offline draft."));
      tx.onabort = () => reject(tx.error || new Error("Offline draft save was interrupted."));
    });
    return draft.idempotencyKey;
  } finally { db.close(); }
}

export async function listExpenseDrafts(userId: number, schoolId: number) {
  const db = await openDatabase();
  try {
    const tx = db.transaction("drafts", "readonly");
    const rows = await requestResult(tx.objectStore("drafts").index("scope").getAll(scopeFor(userId, schoolId))) as StoredDraft[];
    return rows.sort((a, b) => a.createdAt.localeCompare(b.createdAt)).map(({ idempotencyKey, createdAt, resourceType, state, lastError }) => ({ idempotencyKey, createdAt, resourceType: resourceType || "expense", state, lastError }));
  } finally { db.close(); }
}

export async function syncExpenseDrafts(
  userId: number,
  schoolId: number,
  send: (idempotencyKey: string, payload: OfflineExpensePayload | OfflinePurchaseOrderPayload, resourceType: "expense" | "purchase_order") => Promise<{ status: string }>,
) {
  const db = await openDatabase();
  let synced = 0;
  try {
    const scope = scopeFor(userId, schoolId);
    const draftsTx = db.transaction("drafts", "readonly");
    const drafts = await requestResult(draftsTx.objectStore("drafts").index("scope").getAll(scope)) as StoredDraft[];
    const keysTx = db.transaction("keys", "readonly");
    const saved = await requestResult(keysTx.objectStore("keys").get(scope)) as StoredKey | undefined;
    if (!drafts.length) return { synced, remaining: 0 };
    if (!saved?.key) throw new Error("Offline encryption key is missing. Keep this device secure and contact support before clearing its storage.");
    for (const draft of drafts) {
      if (draft.state === "needs_attention") continue;
      try {
        const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv: new Uint8Array(draft.iv) }, saved.key, draft.ciphertext);
        const payload = JSON.parse(new TextDecoder().decode(plaintext)) as OfflineExpensePayload | OfflinePurchaseOrderPayload;
        const resourceType = draft.resourceType || "expense";
        const result = await send(draft.idempotencyKey, payload, resourceType);
        if (!["accepted", "already_applied"].includes(result.status)) {
          await markNeedsAttention(db, draft, "The server returned an unresolved sync state.");
          continue;
        }
        const remove = db.transaction("drafts", "readwrite");
        remove.objectStore("drafts").delete(draft.idempotencyKey);
        await new Promise<void>((resolve, reject) => {
          remove.oncomplete = () => resolve();
          remove.onerror = () => reject(remove.error || new Error("Could not clear synced draft."));
        });
        synced += 1;
      } catch (error) {
        if (error instanceof SyntaxError || error instanceof DOMException && error.name === "OperationError") {
          await markNeedsAttention(db, draft, "Draft could not be decrypted or read. It has been retained for review.");
          continue;
        }
        const httpStatus = error && typeof error === "object" && "status" in error
          ? Number((error as { status?: unknown }).status) : 0;
        if (httpStatus >= 400 && httpStatus < 500) {
          await markNeedsAttention(db, draft, error instanceof Error ? error.message : "Server rejected this draft. It has been retained for review.");
          continue;
        }
        throw error;
      }
    }
    const remaining = await requestResult(db.transaction("drafts", "readonly").objectStore("drafts").index("scope").count(scope));
    return { synced, remaining };
  } finally { db.close(); }
}

async function markNeedsAttention(db: IDBDatabase, draft: StoredDraft, message: string) {
  const tx = db.transaction("drafts", "readwrite");
  tx.objectStore("drafts").put({ ...draft, state: "needs_attention", lastError: message });
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error || new Error("Could not update offline draft state."));
  });
}

export async function discardExpenseDraft(userId: number, schoolId: number, idempotencyKey: string) {
  const db = await openDatabase();
  try {
    const read = db.transaction("drafts", "readonly");
    const draft = await requestResult(read.objectStore("drafts").get(idempotencyKey)) as StoredDraft | undefined;
    if (!draft || draft.scope !== scopeFor(userId, schoolId)) return;
    const tx = db.transaction("drafts", "readwrite");
    tx.objectStore("drafts").delete(idempotencyKey);
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error("Could not discard offline draft."));
      tx.onabort = () => reject(tx.error || new Error("Offline draft discard was interrupted."));
    });
  } finally { db.close(); }
}
