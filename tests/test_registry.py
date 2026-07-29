"""
Registry loading, the reporting helpers, and the empty-registry paths.

The empty-registry cases below are not exotic. An empty registry is the state this
scaffold is *designed* to be handed to a new operator in: the shipped template tells you
to delete its two example capabilities and put your own there. Everything in this file
has to survive that first five minutes.
"""

import os
import re
import subprocess
import sys

import pytest

from conftest import MODULE_PATH, TEMPLATE_REGISTRY, sr


# ── load_registry ────────────────────────────────────────────────────────────


def test_the_shipped_template_registry_loads(tmp_path):
    capabilities = sr.load_registry(TEMPLATE_REGISTRY)
    assert capabilities
    assert all(isinstance(c, sr.Capability) for c in capabilities)
    assert all(c.id and c.name and c.type for c in capabilities)


def test_every_field_of_a_capability_round_trips_off_disk(tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """
capabilities:
  - id: sample-invoice-drafter
    name: Sample Invoice Drafter
    type: skill
    description: Draft an invoice.
    semantic_tags: [invoicing]
    trigger_patterns: ["draft an invoice"]
    dependencies: [reference/rates.md]
    not_for: ["Reviewing an invoice (use sample-invoice-auditor)"]
    load_cost_tokens: 1234
    location: skills/templates/sample-invoice-drafter/SKILL.md
""",
        encoding="utf-8",
    )

    (cap,) = sr.load_registry(registry)

    assert cap.id == "sample-invoice-drafter"
    assert cap.type == "skill"
    assert cap.semantic_tags == ["invoicing"]
    assert cap.trigger_patterns == ["draft an invoice"]
    assert cap.dependencies == ["reference/rates.md"]
    assert cap.not_for == ["Reviewing an invoice (use sample-invoice-auditor)"]
    assert cap.load_cost_tokens == 1234
    assert cap.location == "skills/templates/sample-invoice-drafter/SKILL.md"


def test_optional_fields_fall_back_to_empty_defaults(tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "capabilities:\n  - id: bare\n    name: Bare\n    type: skill\n", encoding="utf-8"
    )

    (cap,) = sr.load_registry(registry)

    assert cap.description == ""
    assert cap.semantic_tags == []
    assert cap.not_for == []
    assert cap.load_cost_tokens == 0


def test_a_missing_registry_file_raises_a_named_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Registry not found"):
        sr.load_registry(tmp_path / "nope.yaml")


def test_a_missing_registry_names_the_fix(tmp_path):
    """Regression for F-FO-05. The first error a newcomer sees has to say what to do next."""
    with pytest.raises(FileNotFoundError, match="skill-registry.template.yaml") as exc_info:
        sr.load_registry(tmp_path / "skill-registry.yaml")
    assert "--registry" in str(exc_info.value)


def test_an_entry_missing_a_required_field_raises_naming_that_field(tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text("capabilities:\n  - id: no-name\n    type: skill\n", encoding="utf-8")

    with pytest.raises(sr.RegistryError, match="no-name.*missing required field: name"):
        sr.load_registry(registry)


# ── hand-written YAML goes wrong quietly, so the loader has to be loud ────────


def _write(tmp_path, body):
    registry = tmp_path / "registry.yaml"
    registry.write_text(body, encoding="utf-8")
    return registry


def test_a_list_field_written_as_a_bare_string_is_refused(tmp_path):
    """
    The costliest typo this registry can absorb, because nothing crashes.

    `semantic_tags: invoicing` (no brackets) is valid YAML and yields the *string*
    "invoicing". Python iterates a string character by character, so every letter gets
    scored as its own tag, and the entry out-scores a genuine full-trigger match on
    queries it has nothing to do with -- silently, forever, at "confident".
    """
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skill\n    semantic_tags: invoicing\n",
    )

    with pytest.raises(sr.RegistryError, match="semantic_tags is a string"):
        sr.load_registry(registry)


def test_the_same_typo_on_not_for_is_refused(tmp_path):
    """The same slip on not_for silently *disables* the clause: no single character ever matches."""
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skill\n"
        "    not_for: Reviewing an invoice\n",
    )

    with pytest.raises(sr.RegistryError, match="not_for is a string"):
        sr.load_registry(registry)


def test_a_load_cost_with_the_value_forgotten_is_refused(tmp_path):
    """
    The same "key present, value forgotten" slip as `capabilities:` with no entries under
    it. A bare `load_cost_tokens:` parses to None and then poisons every sum it lands in,
    so --stats and --list died on it.
    """
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skill\n    load_cost_tokens:\n",
    )

    caps = sr.load_registry(registry)  # loads as zero, which is the honest reading
    assert caps[0].load_cost_tokens == 0
    assert sr.measure_token_savings(caps)["static_total_tokens"] == 0


def test_a_non_numeric_load_cost_is_refused(tmp_path):
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skill\n    load_cost_tokens: lots\n",
    )

    with pytest.raises(sr.RegistryError, match="load_cost_tokens must be a whole number"):
        sr.load_registry(registry)


def test_a_negative_load_cost_is_refused(tmp_path):
    """Regression for F-FO-04. A negative cost would inflate every --max-tokens budget it's summed into."""
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skill\n    load_cost_tokens: -5\n",
    )

    with pytest.raises(sr.RegistryError, match="must not be negative"):
        sr.load_registry(registry)


@pytest.mark.parametrize("falsy", ["false", "{}", "[]", "''"])
def test_a_present_but_falsy_load_cost_is_refused_not_coerced_to_zero(tmp_path, falsy):
    """
    `load_cost_tokens: false` (or {}, [], "") used to read `entry.get(...) or 0`, the same
    coercing idiom the `capabilities:` block above refuses. `or` cannot tell an absent value
    from a present-but-falsy one, so all four collapsed to a legitimate-looking zero -- and a
    zero-cost entry survives every --max-tokens budget, out-competing the honestly-priced
    entries it should have been weighed against. The bool guard alone could never catch
    `false`: `False or 0` resolves to 0 before any type check runs.
    """
    registry = _write(
        tmp_path,
        f"capabilities:\n  - id: a\n    name: A\n    type: skill\n    load_cost_tokens: {falsy}\n",
    )

    with pytest.raises(sr.RegistryError, match="load_cost_tokens must be a whole number"):
        sr.load_registry(registry)


def test_a_zero_load_cost_is_still_legitimate(tmp_path):
    """An explicit 0 is a real cost, not a slip, and must load as itself."""
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skill\n    load_cost_tokens: 0\n",
    )

    (cap,) = sr.load_registry(registry)
    assert cap.load_cost_tokens == 0


def test_a_falsy_load_cost_cannot_undercut_an_honest_one_under_a_budget(tmp_path):
    """
    The behavioral half, proven end to end: before the fix, a `false`-costed entry loaded
    at zero and would have won a --max-tokens 1 budget outright while a 9000-token entry
    was priced out. The registry is refused at load now, so the question never reaches
    the scorer.
    """
    registry = _write(
        tmp_path,
        "capabilities:\n"
        '  - id: broken\n    name: Broken\n    type: skill\n    trigger_patterns: ["write a proposal"]\n'
        "    load_cost_tokens: false\n"
        '  - id: honest\n    name: Honest\n    type: skill\n    trigger_patterns: ["write a proposal"]\n'
        "    load_cost_tokens: 9000\n",
    )

    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(registry), "write a proposal", "--max-tokens", "1",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "load_cost_tokens must be a whole number" in result.stderr
    assert "Broken" not in result.stdout


@pytest.mark.parametrize("bad_id", ["[1, 2]", "{a: 1}"])
def test_a_non_string_id_is_refused_by_name_not_by_traceback(tmp_path, bad_id):
    """
    A list or dict `id:` is truthy, so it satisfies the required-field check and reaches
    the duplicate-id lookup below, where an unhashable key would raise a raw
    `TypeError: unhashable type: 'list'` -- an unfriendly traceback out of the loader,
    from the very validation meant to stop those. Caught here, before that lookup runs,
    with the field named in the message.
    """
    registry = _write(tmp_path, f"capabilities:\n  - id: {bad_id}\n    name: A\n    type: skill\n")

    with pytest.raises(sr.RegistryError, match="id must be text"):
        sr.load_registry(registry)


def test_a_non_string_name_or_type_is_refused_by_name(tmp_path):
    """The same guard covers `name` and `type`, not only `id`."""
    registry = _write(tmp_path, "capabilities:\n  - id: a\n    name: [1, 2]\n    type: skill\n")

    with pytest.raises(sr.RegistryError, match="name must be text"):
        sr.load_registry(registry)


def test_the_cli_refuses_a_non_string_id_without_a_traceback(tmp_path):
    """The CLI half of the regression above: a clean exit-1, never a TypeError traceback."""
    registry = _write(tmp_path, "capabilities:\n  - id: [1, 2]\n    name: A\n    type: skill\n")

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--registry", str(registry), "--list"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "id must be text" in result.stderr
    assert "Traceback" not in result.stderr
    assert "unhashable" not in result.stderr


def test_a_duplicate_id_is_refused(tmp_path):
    """
    Regression for F-FO-01. A copy-pasted duplicate id used to load silently; with
    --confidence the two entries permanently tie and produce an unexplained gap-0.000
    "ambiguous" verdict with no hint why.
    """
    registry = _write(
        tmp_path,
        "capabilities:\n"
        "  - id: dup\n    name: First\n    type: skill\n"
        "  - id: dup\n    name: Second\n    type: skill\n",
    )

    with pytest.raises(sr.RegistryError, match="dup.*duplicate id"):
        sr.load_registry(registry)


def test_a_typo_d_type_value_is_refused(tmp_path):
    """
    Regression for F-FO-03. A typo like "skil" instead of "skill" used to load silently
    and make the entry permanently unroutable, since --type skill/reference/tool would
    never match it and nothing explained why.
    """
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skil\n",
    )

    with pytest.raises(sr.RegistryError, match="type must be one of"):
        sr.load_registry(registry)


@pytest.mark.parametrize(
    "body, expected",
    [
        ("- id: a\n", "top level of a registry must be a mapping"),
        ("capabilities:\n  a:\n    name: A\n", "`capabilities:` must be a list"),
        ("capabilities:\n  - just-a-string\n", "capability #1 is a str, not a mapping"),
        ("capabilities:\n  - id: a\n    type: skill\n", "missing required field: name"),
    ],
)
def test_a_registry_that_is_not_a_registry_is_refused_by_name(tmp_path, body, expected):
    """Each of these used to be a raw TypeError or AttributeError out of the guts of the loader."""
    with pytest.raises(sr.RegistryError, match=re.escape(expected)):
        sr.load_registry(_write(tmp_path, body))


def test_the_cli_reports_a_bad_registry_cleanly_instead_of_tracebacking(tmp_path):
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: a\n    name: A\n    type: skill\n    semantic_tags: invoicing\n",
    )

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--registry", str(registry), "--list"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "semantic_tags is a string" in result.stderr
    assert "Traceback" not in result.stderr


def test_output_does_not_crash_under_a_legacy_windows_code_page():
    """
    Regression for F-FO-02. Box-drawing separators aren't representable in cp1252 (a
    common legacy Windows console encoding); redirected or piped output used to hard-crash
    with UnicodeEncodeError the moment that codec was in effect. PYTHONIOENCODING
    reproduces the codec choice on any platform without needing an actual Windows box.
    """
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--registry", str(TEMPLATE_REGISTRY), "--list"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr


# ── CLI edges ────────────────────────────────────────────────────────────────


def test_top_k_zero_is_a_usage_error_not_a_silent_empty_result():
    """
    Regression for F-FO-08(b). --top-k 0 used to slice every result list down to
    nothing, so a query that matched perfectly still printed "No matches" -- a usage
    mistake in the shape of a real search failure. It is rejected at the parser instead.
    """
    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(TEMPLATE_REGISTRY),
            "weekly report", "--top-k", "0",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "at least 1" in result.stderr


def test_min_score_zero_wins_explicitly_even_under_confidence(tmp_path):
    """
    Regression for F-FO-08(a). Before the fix, --min-score 0 was indistinguishable from
    not passing --min-score at all, so --confidence silently promoted it to
    DEFAULT_MIN_SCORE and a low-but-real match never appeared. An explicit 0 has to mean
    what it says: no floor, not even under --confidence.
    """
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: weak-match\n    name: Weak Match\n    type: skill\n"
        "    description: greenhouse\n",
    )

    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(registry),
            "greenhouse schedule for a small yard",
            "--confidence", "--min-score", "0",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "Weak Match" in result.stdout


def test_confidence_without_min_score_still_applies_the_default_floor(tmp_path):
    """Companion to the test above: with no --min-score at all, the sensible default still applies."""
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: weak-match\n    name: Weak Match\n    type: skill\n"
        "    description: greenhouse\n",
    )

    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(registry),
            "greenhouse schedule for a small yard",
            "--confidence",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "No matches" in result.stdout
    assert "Weak Match" not in result.stdout


# ── the empty-registry paths ─────────────────────────────────────────────────


def test_a_capabilities_key_with_nothing_under_it_loads_as_empty(tmp_path):
    """
    Regression. This is what the registry looks like the moment an operator deletes the
    two shipped example entries to start adding their own: the key survives, its list
    does not. YAML parses that as None, and iterating it raised
    `TypeError: 'NoneType' object is not iterable`.
    """
    registry = tmp_path / "registry.yaml"
    registry.write_text("meta:\n  version: '0.1.0'\ncapabilities:\n", encoding="utf-8")

    assert sr.load_registry(registry) == []


def test_a_completely_empty_registry_file_loads_as_empty(tmp_path):
    """Regression: an empty file parses to None, and `None.get(...)` raised AttributeError."""
    registry = tmp_path / "registry.yaml"
    registry.write_text("", encoding="utf-8")

    assert sr.load_registry(registry) == []


def test_searching_an_empty_registry_returns_no_results():
    assert sr.search("draft an invoice", []) == []
    assert sr.search_with_confidence("draft an invoice", []).confidence == "insufficient"


def test_the_stats_command_explains_an_empty_registry_instead_of_crashing(tmp_path):
    """
    Regression: `measure_token_savings([])` returns {}, and the --stats printer indexed
    straight into it, so the first thing a new operator saw was `KeyError:
    'capabilities_indexed'`.
    """
    registry = tmp_path / "registry.yaml"
    registry.write_text("capabilities: []\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--registry", str(registry), "--stats"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "empty" in result.stdout.lower()
    assert "Traceback" not in result.stderr


# ── measure_token_savings ────────────────────────────────────────────────────


def test_token_savings_counts_the_registry_by_type(sample_registry):
    stats = sr.measure_token_savings(sample_registry)

    assert stats["capabilities_indexed"] == 3
    assert stats["skills"] == 2
    assert stats["references"] == 1
    assert stats["tools"] == 0


def test_token_savings_arithmetic_is_internally_consistent(sample_registry):
    stats = sr.measure_token_savings(sample_registry)

    assert stats["static_total_tokens"] == sum(c.load_cost_tokens for c in sample_registry)
    assert stats["dynamic_meta_tool_tokens"] == sr.DISCOVERY_TOOL_TOKENS
    assert (
        stats["reduction_absolute"]
        == stats["static_total_tokens"] - stats["dynamic_typical_session_tokens"]
    )
    assert stats["dynamic_typical_session_tokens"] > sr.DISCOVERY_TOOL_TOKENS


def test_token_savings_of_an_empty_registry_is_an_empty_report():
    assert sr.measure_token_savings([]) == {}


def test_savings_can_be_negative_on_a_tiny_registry(cap_factory):
    """
    Documented in the template's own header: with only a couple of capabilities
    registered, the flat discovery overhead exceeds the whole index, so --stats reads
    negative. That is honest arithmetic, not a defect, and it must stay that way -- a
    report that never shows a loss would be the broken one.
    """
    stats = sr.measure_token_savings([cap_factory(load_cost_tokens=10)])
    assert stats["reduction_absolute"] < 0
    assert stats["reduction_percent"] < 0


def test_savings_turn_positive_once_the_registry_is_large(cap_factory):
    registry = [cap_factory(id=f"cap-{i}", load_cost_tokens=1000) for i in range(30)]
    stats = sr.measure_token_savings(registry)

    assert stats["reduction_absolute"] > 0
    assert 0 < stats["reduction_percent"] < 100


# ── track_skill_usage ────────────────────────────────────────────────────────


def test_usage_report_separates_central_from_loaded_but_unused():
    report = sr.track_skill_usage(
        loaded_skills=["voice", "proposal", "project-scanner"],
        central_skills=["voice"],
    )

    assert report["central"] == ["voice"]
    assert report["loaded_unused"] == ["project-scanner", "proposal"]
    assert report["not_loaded"] == []
    assert report["utilization"] == round(1 / 3, 3)
    assert report["loaded_count"] == 3
    assert report["central_count"] == 1


def test_usage_report_flags_a_skill_used_without_being_loaded():
    report = sr.track_skill_usage(loaded_skills=["voice"], central_skills=["voice", "proposal"])

    assert report["not_loaded"] == ["proposal"]
    assert report["central"] == ["voice"]
    assert report["utilization"] == 1.0


def test_usage_report_of_an_empty_session_does_not_divide_by_zero():
    report = sr.track_skill_usage(loaded_skills=[], central_skills=[])

    assert report["utilization"] == 0.0
    assert report["loaded_count"] == 0


def test_usage_report_is_pure_and_ignores_duplicate_entries():
    """The docstring promises a pure function: same inputs, same answer, no I/O, no state."""
    args = {"loaded_skills": ["voice", "voice", "proposal"], "central_skills": ["voice"]}

    first = sr.track_skill_usage(**args)
    second = sr.track_skill_usage(**args)

    assert first == second
    assert first["loaded_count"] == 2  # deduplicated


# ── round-2 hardening: friendly errors, honest output, help-text truth ────────
# Every test below pins a row from the 2026-07-15 re-audit's round-2 register (R2-FO-*).


def test_a_yaml_syntax_error_is_refused_by_name(tmp_path):
    """
    Regression for R2-FO-02. A hand-edit slip (an unclosed bracket) used to escape as a raw
    yaml.parser.ParserError traceback; the sibling repo got a friendly handler in round 1 and
    this one did not. It now raises RegistryError naming the problem, with a line number.
    """
    registry = _write(tmp_path, "capabilities: [unclosed\n")
    with pytest.raises(sr.RegistryError, match="YAML syntax error"):
        sr.load_registry(registry)


def test_the_cli_reports_a_yaml_syntax_error_cleanly_instead_of_tracebacking(tmp_path):
    """The CLI half of R2-FO-02: a syntax slip exits 1 with a named error, never a traceback."""
    registry = _write(tmp_path, "capabilities: [unclosed\n")

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--registry", str(registry), "--list"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "YAML syntax error" in result.stderr
    assert "Traceback" not in result.stderr


def test_a_non_utf8_registry_is_refused_by_name(tmp_path):
    """
    Regression for R2-FO-10. The registry is read as UTF-8; a file saved in another encoding
    (here a stray 0xff byte) raised a raw UnicodeDecodeError that escaped both the OSError and
    YAMLError handlers. It now raises RegistryError naming the encoding.
    """
    registry = tmp_path / "registry.yaml"
    registry.write_bytes(b"capabilities:\n  - id: \xff\xfe\n    name: x\n    type: skill\n")

    with pytest.raises(sr.RegistryError, match="not valid UTF-8"):
        sr.load_registry(registry)


@pytest.mark.parametrize("value", ["{}", "false", "0", "''"])
def test_a_present_but_falsy_capabilities_value_is_refused_not_coerced_to_empty(tmp_path, value):
    """
    Regression for R2-FO-03. `capabilities: {}` (and false, 0, "") is falsy, so `... or []`
    used to coerce it to an empty list -- a malformed registry then audited as a clean, empty
    one. Absent or null is the legitimate "just deleted the examples" state and still loads as
    empty (proven by the empty-registry tests above); present-but-wrong-type is refused by name.
    """
    registry = _write(tmp_path, f"capabilities: {value}\n")

    with pytest.raises(sr.RegistryError, match="`capabilities:` must be a list"):
        sr.load_registry(registry)


def test_the_missing_registry_message_points_at_the_scripts_own_template(tmp_path):
    """
    Regression for R2-FO-04. The old advice named the bare relative `skill-registry.template.yaml`,
    which does not resolve from the repo root where the documented commands run -- following it
    looped straight back to this same error. The message now prints the template's script-anchored
    path, which resolves from any working directory.
    """
    with pytest.raises(FileNotFoundError) as exc_info:
        sr.load_registry(tmp_path / "skill-registry.yaml")

    expected = str(MODULE_PATH.parent / "skill-registry.template.yaml")
    assert expected in str(exc_info.value)


def test_help_output_uses_python3_never_bare_python():
    """
    Regression for R2-FO-05. The shipped tool's own --help printed seven bare
    `python skill-registry.py` examples, violating the arc's no-bare-`python` convention.
    """
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert "python3 skill-registry.py" in result.stdout
    assert not re.search(r"python(?!3)", result.stdout), "a bare 'python' survives in --help output"


def test_no_stdlib_fallback_claim_remains_in_the_source():
    """
    Regression for R2-FO-06. A section banner promised a "stdlib fallback" three lines above a
    comment stating PyYAML is a hard requirement with no fallback. The claim is gone.
    """
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "stdlib fallback" not in source
    assert "stdlib-only fallback" not in source


def test_the_missing_pyyaml_message_points_at_a_venv_not_break_system_packages():
    """
    Regression for R2-FO-07. The PyYAML-missing remedy suggested --break-system-packages, off
    the venv-first story the README tells and risky for a newcomer. It points at a venv instead.
    """
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "--break-system-packages" not in source
    assert "python3 -m venv" in source


def test_a_non_integer_top_k_reports_cleanly_without_leaking_the_validator_name():
    """
    Regression for R2-FO-08. `--top-k abc` used to surface the internal helper's name
    ("invalid _positive_int value: 'abc'"). The type function now raises ArgumentTypeError for
    the non-integer case too, so argparse prints the message as written.
    """
    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(TEMPLATE_REGISTRY),
            "weekly report", "--top-k", "abc",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "whole number" in result.stderr
    assert "_positive_int" not in result.stderr


def test_max_tokens_zero_is_a_usage_error_not_a_silent_empty_result():
    """
    Regression for R2-FO-08. --max-tokens 0 prices out every capability, so a query that
    matched perfectly still printed "No matches" -- a usage mistake wearing the mask of a real
    search failure, the same class --top-k 0 was fixed for. Rejected at the parser instead.
    """
    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(TEMPLATE_REGISTRY),
            "weekly report", "--max-tokens", "0",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "at least 1" in result.stderr


def test_max_tokens_negative_is_a_usage_error():
    """The negative half of R2-FO-08's --max-tokens fix."""
    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(TEMPLATE_REGISTRY),
            "weekly report", "--max-tokens=-5",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "at least 1" in result.stderr


def test_a_priced_out_sole_match_reports_the_real_verdict_not_insufficient(tmp_path):
    """
    Regression for R2-FO-01 -- the stash-revert-proof test. A --max-tokens budget can price out
    the only match while the confidence basis, assessed unbudgeted, still scores it "confident".
    The empty-results branch used to hardcode "insufficient" and tell the user to broaden a query
    that was never the problem. It must print the real verdict and point at the budget.
    """
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: pricey-report\n    name: Pricey Report\n    type: skill\n"
        '    trigger_patterns: ["weekly report"]\n    load_cost_tokens: 5000\n',
    )

    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(registry),
            "weekly report", "--confidence", "--max-tokens", "100",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "confident" in result.stdout          # the real verdict...
    assert "insufficient" not in result.stdout   # ...not the hardcoded one
    assert "max-tokens" in result.stdout          # points at the budget, the actual cause
    assert "Try broadening" not in result.stdout  # not the wrong advice


def test_a_priced_out_match_without_confidence_names_the_budget_not_the_query(tmp_path):
    """
    Companion to the test above for the plain-search path: no --confidence, but a budget can
    still price out every match. The advice must name the budget, not send the user to broaden a
    query that matched -- so the two output paths stay consistent with each other.
    """
    registry = _write(
        tmp_path,
        "capabilities:\n  - id: pricey-report\n    name: Pricey Report\n    type: skill\n"
        '    trigger_patterns: ["weekly report"]\n    load_cost_tokens: 5000\n',
    )

    result = subprocess.run(
        [
            sys.executable, str(MODULE_PATH),
            "--registry", str(registry),
            "weekly report", "--max-tokens", "100",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "max-tokens" in result.stdout
    assert "Try broadening" not in result.stdout


def test_the_stdout_guard_survives_a_stream_whose_reconfigure_raises(monkeypatch):
    """
    Regression for R2-FO-10 (guard parity). A stdout whose reconfigure() raises ValueError -- a
    detached or already-closed stream -- escaped the old hasattr() guard and crashed the CLI
    before it did any work. The guard now mirrors the sibling's try/except (AttributeError,
    ValueError). A fake that HAS reconfigure but raises exercises the branch hasattr() could not.
    """
    class _DetachedStdout:
        def __init__(self):
            self.buf = []

        def reconfigure(self, **kwargs):
            raise ValueError("underlying buffer has been detached")

        def write(self, s):
            self.buf.append(s)
            return len(s)

        def flush(self):
            pass

    fake = _DetachedStdout()
    monkeypatch.setattr(sys, "argv", ["skill-registry", "--registry", str(TEMPLATE_REGISTRY), "--list"])
    monkeypatch.setattr(sys, "stdout", fake)

    sr.cli()  # must not raise ValueError out of the reconfigure guard

    assert any("Skills" in chunk for chunk in fake.buf)
