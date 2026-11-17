"""Minimal GitHub Git Data API client: read files at a commit, write many files in ONE commit."""
from __future__ import annotations

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor

import requests

API = "https://api.github.com"


class GitHubError(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


class Repo:
    def __init__(self, full_name: str, branch: str, token: str | None, dry_run: bool = False):
        self.full_name, self.branch, self.token, self.dry_run = full_name, branch, token, dry_run
        self.s = requests.Session()
        self.s.headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                               "User-Agent": "eslavia-admin"})
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"
        self._tree: dict[str, str] | None = None
        self._by_sha: dict[str, str] | None = None
        self.head: str | None = None

    # -- low level --------------------------------------------------------
    def _req(self, method, path, **kw):
        url = path if path.startswith("http") else f"{API}/repos/{self.full_name}{path}"
        for attempt in range(4):
            try:
                r = self.s.request(method, url, timeout=(10, 60), **kw)
            except requests.RequestException as e:
                if attempt == 3:
                    raise GitHubError(f"GitHub недоступен: {e.__class__.__name__}")
                time.sleep(1 + attempt * 2)
                continue
            if r.status_code >= 500 and attempt < 3:
                time.sleep(1 + attempt * 2)
                continue
            if r.status_code >= 400:
                try:
                    msg = r.json().get("message", "")
                except ValueError:
                    msg = r.text[:200]
                raise GitHubError(f"GitHub {r.status_code}: {msg}", r.status_code)
            return r
        raise GitHubError("GitHub: нет ответа")

    # -- reading ----------------------------------------------------------
    def load_head(self) -> str:
        r = self._req("GET", f"/git/ref/heads/{self.branch}")
        self.head = r.json()["object"]["sha"]
        c = self._req("GET", f"/git/commits/{self.head}").json()
        t = self._req("GET", f"/git/trees/{c['tree']['sha']}?recursive=1").json()
        if t.get("truncated"):
            raise GitHubError("Дерево репозитория слишком большое для API")
        self._tree = {e["path"]: e["sha"] for e in t["tree"] if e["type"] == "blob"}
        self._by_sha = None
        self.tree_sha = c["tree"]["sha"]
        return self.head

    @property
    def tree(self) -> dict[str, str]:
        if self._tree is None:
            self.load_head()
        return self._tree

    def exists(self, path: str) -> bool:
        return path in self.tree

    def read(self, path: str) -> bytes:
        sha = self.tree.get(path)
        if not sha:
            raise GitHubError(f"нет файла {path}", 404)
        # raw.githubusercontent.com is not subject to the REST API rate limit
        try:
            r = self._req("GET", f"https://raw.githubusercontent.com/{self.full_name}/{self.head}/{path}")
            return r.content
        except GitHubError:
            return self.read_blob(sha, raw_ok=False)

    def read_blob(self, sha: str, raw_ok: bool = True) -> bytes:
        if raw_ok:
            if self._by_sha is None:
                self._by_sha = {v: k for k, v in self.tree.items()}
            path = self._by_sha.get(sha)
            if path:
                return self.read(path)
        r = self._req("GET", f"/git/blobs/{sha}", headers={"Accept": "application/vnd.github.raw+json"})
        return r.content

    def read_json(self, path: str, default=None):
        if default is not None and path not in self.tree:
            return default
        return json.loads(self.read(path).decode("utf-8"))

    def read_many(self, paths: list[str], workers: int = 12) -> dict[str, bytes | None]:
        def one(p):
            try:
                return p, self.read(p)
            except GitHubError:
                return p, None
        with ThreadPoolExecutor(workers) as ex:
            return dict(ex.map(one, paths))

    # -- writing ----------------------------------------------------------
    def commit(self, files: dict[str, bytes | None], message: str) -> dict:
        """files: path -> bytes (create/update) or None (delete). One commit, fast-forward only."""
        if self.head is None:
            self.load_head()
        changed = {p: b for p, b in files.items() if isinstance(b, (bytes, bytearray))}
        refs = {p: b["sha"] for p, b in files.items() if isinstance(b, dict)}
        deleted = [p for p, b in files.items() if b is None and p in self.tree]
        if self.dry_run:
            return {"sha": "dry-run", "dry_run": True, "files": sorted(set(changed) | set(refs)), "deleted": sorted(deleted),
                    "bytes": sum(len(b) for b in changed.values())}

        def blob(item):
            p, data = item
            r = self._req("POST", "/git/blobs", json={"content": base64.b64encode(data).decode(), "encoding": "base64"})
            return p, r.json()["sha"]
        with ThreadPoolExecutor(8) as ex:
            shas = dict(ex.map(blob, changed.items()))
        shas.update(refs)
        entries = [{"path": p, "mode": "100644", "type": "blob", "sha": s} for p, s in shas.items()
                   if self.tree.get(p) != s]
        entries += [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in deleted]
        if not entries:
            return {"sha": self.head, "unchanged": True, "files": [], "deleted": []}
        tree = self._req("POST", "/git/trees", json={"base_tree": self.tree_sha, "tree": entries}).json()
        commit = self._req("POST", "/git/commits", json={"message": message, "tree": tree["sha"],
                                                          "parents": [self.head]}).json()
        self._req("PATCH", f"/git/refs/heads/{self.branch}", json={"sha": commit["sha"], "force": False})
        self.head = commit["sha"]
        return {"sha": commit["sha"], "url": commit.get("html_url"), "files": sorted(p for p in shas),
                "deleted": sorted(deleted)}

    def pages_status(self, sha: str) -> dict:
        try:
            runs = self._req("GET", f"/actions/runs?head_sha={sha}&per_page=5").json().get("workflow_runs", [])
        except GitHubError as e:
            return {"state": "unknown", "error": str(e)}
        if not runs:
            return {"state": "queued"}
        r = runs[0]
        return {"state": r.get("status"), "conclusion": r.get("conclusion"), "url": r.get("html_url")}
