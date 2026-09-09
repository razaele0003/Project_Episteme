// Hosted progress is scoped to this browser. The local Python workspace is unchanged.
export const browserWorkspace = import.meta.env.MODE === 'browser';
const dbName = 'episteme-workspace-v1';
let opening;
function database() {
  if (!opening) opening = new Promise((resolve, reject) => {
    const request = indexedDB.open(dbName, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('records');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error('Browser storage is unavailable. Allow site storage, then reload.'));
  });
  return opening;
}
async function read(key) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const request = db.transaction('records').objectStore('records').get(key);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error('Saved progress could not be read.'));
  });
}
async function saveSnapshot(snapshot) {
  const db = await database();
  const key = snapshot.repository.toLowerCase() + ':' + snapshot.root;
  const previous = await read('binding:' + key);
  const events = [...snapshot.activity, ...(previous?.activity || [])];
  snapshot.activity = events.filter((event, index) => events.findIndex(item => item.sha === event.sha) === index);
  return new Promise((resolve, reject) => {
    const tx = db.transaction('records', 'readwrite');
    const records = tx.objectStore('records');
    records.put(snapshot, 'binding:' + key);
    records.put(snapshot, 'snapshot:' + key + ':' + snapshot.last_sync.sha);
    records.put(key, 'active');
    tx.oncomplete = () => resolve(snapshot);
    tx.onerror = () => reject(new Error('Could not save progress in this browser. Free some site storage and retry. Previous progress was kept.'));
    tx.onabort = () => reject(new Error('Saving was interrupted. Previous progress was kept.'));
  });
}
let blank;
async function current() {
  const key = await read('active');
  if (key) {
    const saved = await read('binding:' + key);
    if (saved) return saved;
  }
  if (!blank) {
    const response = await fetch('/api/browser-bootstrap');
    if (!response.ok) throw new Error('The curriculum could not be loaded. Please retry.');
    blank = await response.json();
  }
  return blank;
}
const response = (body, status = 200) => new Response(JSON.stringify(body), {status, headers: {'Content-Type': 'application/json'}});
export async function workspaceFetch(path, options = {}) {
  if (!browserWorkspace) return fetch(path, options);
  try {
    if (path === '/api/progress') return response(await current());
    if (path.startsWith('/api/projects/')) {
      const state = await current();
      if (options.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
      const id = decodeURIComponent(path.slice('/api/projects/'.length));
      const project = state.projects.find(item => item.id === id);
      if (!project) return response({detail: 'Project not found.'}, 404);
      const navigation = state.projects.filter(item => Boolean(item.historical) === Boolean(project.historical));
      const index = navigation.findIndex(item => item.id === id);
      return response({...project, previous_project: navigation[index - 1] || null, next_project: navigation[index + 1] || null});
    }
    if (path === '/api/connection' || path === '/api/sync') {
      const state = await current();
      const binding = options.body ? JSON.parse(String(options.body)) : {repository: state.repository, root: state.root};
      const result = await fetch('/api/browser-sync', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Episteme-Client': 'dashboard'}, body: JSON.stringify(binding)});
      const body = await result.json();
      if (!result.ok) return response(body, result.status);
      await saveSnapshot(body);
      return response({sha: body.last_sync.sha});
    }
    return response({detail: 'This action is unavailable in the browser workspace.'}, 404);
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    return response({detail: error.message || 'Workspace unavailable. Previous progress was kept.'}, 503);
  }
}
