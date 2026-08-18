from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gemma_qat_bench.orchestration.domain import (
    CommandEvidence,
    CommandId,
    CommandStatus,
    DomainError,
    TaskId,
)
from gemma_qat_bench.orchestration.evidence import EvidenceBinding, EvidenceLedger
from gemma_qat_bench.orchestration.fingerprint import (
    FingerprintService,
    GitContentIdentityProvider,
)
from gemma_qat_bench.orchestration.scope import GitWorkspaceChangeDetector, changed_since


class Identities:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def identity(self, relative_path: str) -> str:
        return self.values[relative_path]


def evidence(command_id: str, fingerprint: str) -> CommandEvidence:
    return CommandEvidence(
        CommandId(command_id),
        ("pytest", "-q"),
        ".",
        CommandStatus.SUCCEEDED,
        0,
        "1 passed",
        False,
        True,
        fingerprint,
    )


def test_fingerprint_v1_golden_vector_and_path_order(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text(
        "content is represented by provider", encoding="utf-8"
    )
    service = FingerprintService(tmp_path, Identities({"a.txt": "blob-a"}))
    result = service.capture(("b.txt", "a.txt"))
    assert result.manifest == (
        "present\ta.txt\tblob-a",
        "deleted\tb.txt\tDELETED",
    )
    assert (
        result.digest
        == "c17590e417f91a63a8eac302034c66ef17aecd4fd95fbf39a88e630c3b98d618"
    )
    assert service.is_current(result)


def test_fingerprint_detects_content_drift(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("a", encoding="utf-8")
    identities = Identities({"a.txt": "first"})
    service = FingerprintService(tmp_path, identities)
    first = service.capture(("a.txt",))
    identities.values["a.txt"] = "second"
    assert not service.is_current(first)


def test_workspace_delta_detects_new_deleted_and_reedited_baseline_paths() -> None:
    baseline = {"already-modified.py": "old", "deleted-later.py": "present"}
    current = {"already-modified.py": "new", "new.py": "new"}
    assert changed_since(baseline, current) == (
        "already-modified.py",
        "deleted-later.py",
        "new.py",
    )


def test_git_scope_detector_covers_tracked_deleted_untracked_and_reedited(
    tmp_path: Path,
) -> None:
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    subprocess.run(
        ("git", "config", "user.email", "v3-test@example.invalid"),
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(("git", "config", "user.name", "V3 Test"), cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    subprocess.run(("git", "add", "a.txt", "b.txt"), cwd=tmp_path, check=True)
    subprocess.run(("git", "commit", "-qm", "base"), cwd=tmp_path, check=True)

    detector = GitWorkspaceChangeDetector(tmp_path)
    assert detector.capture() == {}
    (tmp_path / "a.txt").write_text("first edit", encoding="utf-8")
    baseline = detector.capture()
    (tmp_path / "a.txt").write_text("second edit", encoding="utf-8")
    (tmp_path / "b.txt").unlink()
    (tmp_path / "c.txt").write_text("new", encoding="utf-8")
    current = detector.capture()

    assert set(current) == {"a.txt", "b.txt", "c.txt"}
    assert current["b.txt"] == "DELETED"
    assert changed_since(baseline, current) == ("a.txt", "b.txt", "c.txt")


def test_unlaunchable_git_binary_fails_closed_as_domain_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    def unavailable(
        *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        raise FileNotFoundError("git is unavailable")

    monkeypatch.setattr(subprocess, "run", unavailable)

    with pytest.raises(DomainError, match="Git workspace inspection"):
        GitWorkspaceChangeDetector(tmp_path).capture()
    with pytest.raises(DomainError, match="git hash-object"):
        GitContentIdentityProvider(tmp_path).identity("a.txt")


def test_non_utf8_git_output_fails_closed_as_domain_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    def undecodable(
        *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        argv = args[0] if args else ()
        return subprocess.CompletedProcess(argv, 0, stdout=b"\xff\x00", stderr=b"")

    monkeypatch.setattr(subprocess, "run", undecodable)

    with pytest.raises(DomainError, match="UTF-8"):
        GitWorkspaceChangeDetector(tmp_path).capture()
    with pytest.raises(DomainError, match="UTF-8"):
        GitContentIdentityProvider(tmp_path).identity("a.txt")


def test_evidence_ledger_rejects_competing_or_stale_records() -> None:
    binding = EvidenceBinding(TaskId("T"), "PLAN-1", 1, 1, "task", "abc")
    ledger = EvidenceLedger(binding, ("CMD-001",))
    with pytest.raises(DomainError, match="unknown"):
        ledger.record(evidence("CMD-X", "abc"))
    with pytest.raises(DomainError, match="fingerprint"):
        ledger.record(evidence("CMD-001", "stale"))
    ledger.record(evidence("CMD-001", "abc"))
    with pytest.raises(DomainError, match="duplicate"):
        ledger.record(evidence("CMD-001", "abc"))
    assert ledger.complete
    assert ledger.verifier_view()[0].successful
    ledger.invalidate()
    with pytest.raises(DomainError, match="stale"):
        ledger.verifier_view()
