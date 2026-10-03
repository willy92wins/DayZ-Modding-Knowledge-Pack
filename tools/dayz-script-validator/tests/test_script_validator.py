# Test suite — rules CANDIDATE-1..7 implemented in top-5; CANDIDATE-8/9/10 added 2026-05-19.
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import script_validator
from shared import vanilla_tree


_MODULE_PATCHES = []


def setUpModule():
    # run() looks for the vanilla tree in DAYZ_VANILLA_ROOT, then P:\scripts.
    # A unit test must not change verdict with what this machine has mounted,
    # so neither is visible here; tests that need a tree pass --vanilla-root.
    env = mock.patch.dict(os.environ)
    env.start()
    _MODULE_PATCHES.append(env)
    os.environ.pop("DAYZ_VANILLA_ROOT", None)
    pdrive = mock.patch.object(
        vanilla_tree, "PDRIVE_SCRIPTS", FIXTURES / "no_vanilla_tree_in_unit_tests"
    )
    pdrive.start()
    _MODULE_PATCHES.append(pdrive)


def tearDownModule():
    while _MODULE_PATCHES:
        _MODULE_PATCHES.pop().stop()


REQUIRED_FINDING_KEYS = {"check", "file", "line", "message", "severity", "rule_id"}


def assert_standard_findings(testcase, result):
    for collection_name in ("errors", "warnings"):
        for finding in result[collection_name]:
            testcase.assertTrue(
                REQUIRED_FINDING_KEYS.issubset(finding.keys()),
                f"{collection_name} finding has non-standard schema: {finding}",
            )


class TestSkeleton(unittest.TestCase):
    def test_empty_fixture_passes(self):
        exit_code, result = script_validator.run([str(FIXTURES / "empty")])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(0, result["info"]["files_scanned"])
        json.dumps(result)

    def test_nonexistent_path_fails(self):
        missing_path = "C:/this/path/does/not/exist"
        exit_code, result = script_validator.run([missing_path])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual(0, result["info"]["files_scanned"])
        self.assertEqual("INPUT-NOT-FOUND", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(str(pathlib.Path(missing_path)), result["errors"][0]["file"])
        self.assertIsNone(result["errors"][0]["line"])
        self.assertIn(str(pathlib.Path(missing_path)), result["errors"][0]["message"])

    def test_nonexistent_path_emits_standard_schema(self):
        exit_code, result = script_validator.run(["C:/this/path/does/not/exist"])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        assert_standard_findings(self, result)

    def test_non_utf8_source_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            bad_file = temp_path / "bad_cp1252.c"
            bad_file.write_bytes(b"// caf\xe9\n")

            exit_code, result = script_validator.run([str(temp_path)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])
        self.assertEqual("INPUT-ENCODING-ERROR", result["errors"][0]["rule_id"])
        self.assertEqual("INPUT-ENCODING-ERROR", result["errors"][0]["check"])
        self.assertEqual("bad_cp1252.c", result["errors"][0]["file"])
        self.assertEqual(1, result["errors"][0]["line"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertIn("file is not valid UTF-8", result["errors"][0]["message"])
        self.assertIn("Decode error at byte", result["errors"][0]["message"])
        assert_standard_findings(self, result)
        json.dumps(result)


class TestStripper(unittest.TestCase):
    def stripped_fixture(self, name):
        source = (FIXTURES / "es" / name).read_text(encoding="utf-8")
        stripped, warnings = script_validator.strip_enforce_comments_and_strings(
            source, name
        )
        return source, stripped, warnings

    def test_delete_in_string_literal_removed(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_delete_in_string_literal.c"
        )

        self.assertNotIn("delete", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_delete_in_block_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_delete_in_block_comment.c"
        )

        self.assertNotIn("delete", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_ctx_read_in_block_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_ctx_read_in_block_comment.c"
        )

        self.assertNotIn("ctx.Read", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_delete_in_line_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_delete_in_line_comment.c"
        )

        self.assertNotIn("delete", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_ctx_read_in_line_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_ctx_read_in_line_comment.c"
        )

        self.assertNotIn("ctx.Read", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_unterminated_string_emits_warning(self):
        source, stripped, warnings = self.stripped_fixture("bad_unterminated_string.c")

        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual(1, len(warnings))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-STRING", warnings[0]["rule_id"]
        )
        self.assertEqual("WARN", warnings[0]["severity"])
        self.assertIn("bad_unterminated_string.c", warnings[0]["message"])

    def test_unterminated_block_comment_emits_warning(self):
        source, stripped, warnings = self.stripped_fixture(
            "bad_unterminated_block_comment.c"
        )

        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual(1, len(warnings))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-BLOCK-COMMENT", warnings[0]["rule_id"]
        )
        self.assertEqual("WARN", warnings[0]["severity"])
        self.assertIn("bad_unterminated_block_comment.c", warnings[0]["message"])


class TestRvmat(unittest.TestCase):
    def test_super_shader_passes(self):
        exit_code, result = script_validator.run(
            [str(FIXTURES / "rvmat" / "ok_super_shader.rvmat")]
        )

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_normalmapmacro_fails(self):
        fixture = FIXTURES / "rvmat" / "bad_normalmapmacro.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_normalmapmacro.rvmat line 3: rvmat uses "
            "'shader = NormalMapMacro;'. Causes dedicated server crash at model "
            "load (pitfalls-advanced.md:99). Replace with 'shader = Super;'."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("RVMAT-NO-NORMALMAPMACRO", result["errors"][0]["rule_id"])
        self.assertEqual("bad_normalmapmacro.rvmat", result["errors"][0]["file"])
        self.assertEqual(3, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_normalmapmacro_in_line_comment_passes(self):
        fixture = FIXTURES / "rvmat" / "ok_normalmapmacro_in_comment.rvmat"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_normalmapmacro_with_trailing_comment_fails(self):
        fixture = FIXTURES / "rvmat" / "bad_normalmapmacro_with_trailing_comment.rvmat"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual(
            "RVMAT-NO-NORMALMAPMACRO", result["errors"][0]["rule_id"]
        )
        self.assertEqual(
            "bad_normalmapmacro_with_trailing_comment.rvmat",
            result["errors"][0]["file"],
        )
        self.assertEqual(3, result["errors"][0]["line"])

    def test_directory_with_rvmat_reports_errors(self):
        exit_code, result = script_validator.run([str(FIXTURES / "rvmat")])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(4, result["info"]["files_scanned"])
        self.assertEqual(2, len(result["errors"]))
        error_files = {error["file"] for error in result["errors"]}
        self.assertEqual(
            {
                "bad_normalmapmacro.rvmat",
                "bad_normalmapmacro_with_trailing_comment.rvmat",
            },
            error_files,
        )
        for error in result["errors"]:
            self.assertEqual("RVMAT-NO-NORMALMAPMACRO", error["rule_id"])


class TestEsNoDelete(unittest.TestCase):
    def test_no_delete_passes(self):
        fixture = FIXTURES / "es" / "ok_no_delete.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_widget_unlink_does_not_trigger_delete_rule(self):
        fixture = FIXTURES / "es" / "ok_widget_unlink.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_delete_in_string_literal_still_passes_end_to_end(self):
        fixture = FIXTURES / "es" / "ok_delete_in_string_literal.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_delete_in_block_comment_still_passes_end_to_end(self):
        fixture = FIXTURES / "es" / "ok_delete_in_block_comment.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_delete_in_line_comment_still_passes_end_to_end(self):
        fixture = FIXTURES / "es" / "ok_delete_in_line_comment.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_unterminated_string_emits_warn_no_delete_finding(self):
        fixture = FIXTURES / "es" / "bad_unterminated_string.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-STRING", result["warnings"][0]["rule_id"]
        )

    def test_unterminated_block_comment_emits_warn_no_delete_finding(self):
        fixture = FIXTURES / "es" / "bad_unterminated_block_comment.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-BLOCK-COMMENT",
            result["warnings"][0]["rule_id"],
        )

    def test_directory_with_fail_and_warn_returns_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            (temp_path / "bad_local_var_redeclare.c").write_text(
                "\n".join(
                    [
                        "class BadLocalFixture",
                        "{",
                        "    void Check(bool c)",
                        "    {",
                        "        if (c)",
                        "        {",
                        "            int x = 5;",
                        "        }",
                        "        else",
                        "        {",
                        "            int x = 10;",
                        "        }",
                        "    }",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            (temp_path / "bad_unterminated_string.c").write_text(
                "\n".join(
                    [
                        "class BadStringFixture",
                        "{",
                        "    void Broken()",
                        "    {",
                        '        string value = "unterminated;',
                        "    }",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            exit_code, result = script_validator.run([str(temp_path)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual(
            "ES-LOCAL-VAR-REDECLARE", result["errors"][0]["rule_id"]
        )
        self.assertGreaterEqual(len(result["warnings"]), 1)
        warning_rule_ids = {warning["rule_id"] for warning in result["warnings"]}
        self.assertIn("ES-SOURCE-UNTERMINATED-STRING", warning_rule_ids)
        self.assertEqual(2, result["info"]["files_scanned"])
        assert_standard_findings(self, result)


class TestEsEmptyIfdef(unittest.TestCase):
    def test_ifdef_with_statement_passes(self):
        fixture = FIXTURES / "es" / "ok_ifdef_with_statement.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ifndef_with_statement_passes(self):
        fixture = FIXTURES / "es" / "ok_ifndef_with_statement.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_empty_ifdef_with_comments_fails(self):
        fixture = FIXTURES / "es" / "bad_empty_ifdef_with_comments.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_empty_ifdef_with_comments.c line 1: '#ifdef MY_MOD' "
            "block contains no statements (comments do not count). Documented "
            "segfault per pitfalls-advanced.md:66 (\"Empty #ifdef Blocks Cause "
            "Segfault\"). Add at least one statement (e.g., 'int _placeholder;')."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-EMPTY-IFDEF", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual("bad_empty_ifdef_with_comments.c", result["errors"][0]["file"])
        self.assertEqual(1, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_empty_ifndef_with_comments_fails(self):
        fixture = FIXTURES / "es" / "bad_empty_ifndef_with_comments.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_empty_ifndef_with_comments.c line 1: '#ifndef SERVER' "
            "block contains no statements (comments do not count). Documented "
            "segfault per pitfalls-advanced.md:66 (\"Empty #ifdef Blocks Cause "
            "Segfault\"). Add at least one statement (e.g., 'int _placeholder;')."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-EMPTY-IFDEF", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual("bad_empty_ifndef_with_comments.c", result["errors"][0]["file"])
        self.assertEqual(1, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ifdef_nested_passes(self):
        fixture = FIXTURES / "es" / "ok_ifdef_nested.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ifdef_with_unsupported_inner_passes_with_warning(self):
        fixture = FIXTURES / "es" / "ok_ifdef_with_unsupported_inner.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertGreaterEqual(len(result["warnings"]), 1)
        warning_rule_ids = {warning["rule_id"] for warning in result["warnings"]}
        self.assertIn("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", warning_rule_ids)

    def test_ifdef_empty_with_only_unsupported_passes_with_warning(self):
        fixture = FIXTURES / "es" / "bad_ifdef_empty_with_unsupported_only.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertGreaterEqual(len(result["warnings"]), 1)
        warning_rule_ids = {warning["rule_id"] for warning in result["warnings"]}
        self.assertIn("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", warning_rule_ids)

    def test_ifdef_unterminated_warns(self):
        fixture = FIXTURES / "es" / "warn_ifdef_unterminated.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_ifdef_unterminated.c", result["warnings"][0]["file"])
        self.assertEqual(1, result["warnings"][0]["line"])
        self.assertIn("unterminated #ifdef MY_MOD", result["warnings"][0]["message"])

    def test_endif_stray_warns(self):
        fixture = FIXTURES / "es" / "warn_endif_stray.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_endif_stray.c", result["warnings"][0]["file"])
        self.assertEqual(2, result["warnings"][0]["line"])
        self.assertIn("stray #endif without matching #ifdef", result["warnings"][0]["message"])


class TestEsCtxReadUnchecked(unittest.TestCase):
    def test_ctx_read_checked_passes(self):
        fixture = FIXTURES / "es" / "ok_ctx_read_checked.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ctx_read_pattern_b_passes(self):
        fixture = FIXTURES / "es" / "ok_ctx_read_pattern_b.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ctx_read_bool_local_passes(self):
        fixture = FIXTURES / "es" / "ok_ctx_read_bool_local.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ctx_read_unchecked_onstoreload_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_onstoreload.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_onstoreload.c line 7: ctx.Read() "
            "return not checked inside OnStoreLoad (fail-closed context). "
            "Required: 'if (!ctx.Read(...)) return false;' (SKILL.md rule 18, "
            "networking.md:169). Silent corruption on truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_onstoreload.c", result["errors"][0]["file"]
        )
        self.assertEqual(7, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_multiline_signature_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_onstoreload_multiline.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_onstoreload_multiline.c line 10: "
            "ctx.Read() return not checked inside OnStoreLoad (fail-closed "
            "context). Required: 'if (!ctx.Read(...)) return false;' "
            "(SKILL.md rule 18, networking.md:169). Silent corruption on "
            "truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_onstoreload_multiline.c",
            result["errors"][0]["file"],
        )
        self.assertEqual(10, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_with_renamed_param_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_with_renamed_param.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_with_renamed_param.c line 7: "
            "ctx.Read() return not checked inside OnStoreLoad (fail-closed "
            "context). Required: 'if (!ctx.Read(...)) return false;' "
            "(SKILL.md rule 18, networking.md:169). Silent corruption on "
            "truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_with_renamed_param.c",
            result["errors"][0]["file"],
        )
        self.assertEqual(7, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_in_rpc_server_guard_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_in_rpc.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_in_rpc.c line 8: ctx.Read() return "
            "not checked inside OnRPC (fail-closed context). Required: "
            "'if (!ctx.Read(...)) return false;' (SKILL.md rule 18, "
            "networking.md:169). Silent corruption on truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual("bad_ctx_read_unchecked_in_rpc.c", result["errors"][0]["file"])
        self.assertEqual(8, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_in_rpc_outer_server_guard_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_in_rpc_outer_server_guard.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_in_rpc_outer_server_guard.c line 8: "
            "ctx.Read() return not checked inside OnRPC (fail-closed context). "
            "Required: 'if (!ctx.Read(...)) return false;' (SKILL.md rule 18, "
            "networking.md:169). Silent corruption on truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_in_rpc_outer_server_guard.c",
            result["errors"][0]["file"],
        )
        self.assertEqual(8, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_under_ifndef_server_warns(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_in_rpc_ifndef_server.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] warn_ctx_read_unchecked_in_rpc_ifndef_server.c line 8: "
            "ctx.Read() return not checked. Recommended: "
            "'if (!ctx.Read(...)) ...'."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_in_rpc_ifndef_server.c",
            result["warnings"][0]["file"],
        )
        self.assertEqual(8, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])

    def test_ctx_read_unchecked_in_onvarsync_warns(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_in_onvarsync.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] warn_ctx_read_unchecked_in_onvarsync.c line 7: ctx.Read() "
            "return not checked. Recommended: 'if (!ctx.Read(...)) ...'."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_in_onvarsync.c", result["warnings"][0]["file"]
        )
        self.assertEqual(7, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])

    def test_ctx_read_combined_condition_emits_unsupported_warning(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_combined_condition.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-CTX-READ-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_combined_condition.c",
            result["warnings"][0]["file"],
        )
        self.assertEqual(7, result["warnings"][0]["line"])
        self.assertIn("combined condition", result["warnings"][0]["message"])

    def test_ctx_read_in_try_catch_emits_unsupported_warning(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_in_try_catch.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-CTX-READ-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_ctx_read_in_try_catch.c", result["warnings"][0]["file"])
        self.assertEqual(8, result["warnings"][0]["line"])
        self.assertIn("inside try/catch block", result["warnings"][0]["message"])

    def test_ctx_read_unchecked_in_rpc_no_guard_warns(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_in_rpc_no_guard.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] warn_ctx_read_unchecked_in_rpc_no_guard.c line 7: ctx.Read() "
            "return not checked. Recommended: 'if (!ctx.Read(...)) ...'."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_in_rpc_no_guard.c",
            result["warnings"][0]["file"],
        )
        self.assertEqual(7, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])


class TestEsSyncvarContract(unittest.TestCase):
    def run_fixture(self, name):
        fixture = FIXTURES / "es" / name
        return script_validator.run([str(fixture)])

    def assert_syncvar_passes(self, name):
        exit_code, result = self.run_fixture(name)

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def assert_syncvar_error(self, name, line_number, expected_message):
        exit_code, result = self.run_fixture(name)

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-SYNCVAR-CONTRACT", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(name, result["errors"][0]["file"])
        self.assertEqual(line_number, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def assert_syncvar_unsupported_warning(self, name, line_number, expected_text):
        exit_code, result = self.run_fixture(name)

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        matching = [
            warning
            for warning in result["warnings"]
            if warning["rule_id"] == "ES-SYNCVAR-UNSUPPORTED-PATTERN"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("WARN", matching[0]["severity"])
        self.assertEqual(name, matching[0]["file"])
        self.assertEqual(line_number, matching[0]["line"])
        self.assertIn(expected_text, matching[0]["message"])

    def test_syncvar_full_contract_passes(self):
        self.assert_syncvar_passes("ok_syncvar_full.c")

    def test_syncvar_modded_class_passes(self):
        self.assert_syncvar_passes("ok_modded_class_syncvar.c")

    def test_syncvar_long_server_block_single_dirty_passes(self):
        self.assert_syncvar_passes("ok_syncvar_long_server_block.c")

    def test_syncvar_class_brace_next_line_passes(self):
        self.assert_syncvar_passes("ok_syncvar_class_brace_next_line.c")

    def test_syncvar_extends_class_passes(self):
        self.assert_syncvar_passes("ok_syncvar_extends_class.c")

    def test_syncvar_init_item_variables_passes(self):
        self.assert_syncvar_passes("ok_syncvar_init_item_variables.c")

    def test_syncvar_other_prefix_does_not_trigger_write_rule(self):
        self.assert_syncvar_passes("ok_syncvar_other_prefix.c")

    def test_syncvar_field_declaration_with_initializer_passes(self):
        self.assert_syncvar_passes("ok_syncvar_field_declaration_with_initializer.c")

    def test_syncvar_register_outside_constructor_fails(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_outside_ctor.c line 6: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_outside_ctor.c", 6, expected_message
        )

    def test_syncvar_write_without_dirty_fails(self):
        expected_message = (
            "[FAIL] bad_syncvar_write_no_dirty.c line 12: SyncVar 'm_X' "
            "assigned inside '#ifdef SERVER' but missing 'SetSynchDirty()' "
            "in the same block. Clients won't see the change (networking.md:59)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_write_no_dirty.c", 12, expected_message
        )

    def test_syncvar_dirty_in_other_method_does_not_cover_write(self):
        expected_message = (
            "[FAIL] bad_syncvar_dirty_in_other_method.c line 17: SyncVar 'm_X' "
            "assigned inside '#ifdef SERVER' but missing 'SetSynchDirty()' "
            "in the same block. Clients won't see the change (networking.md:59)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_dirty_in_other_method.c", 17, expected_message
        )

    def test_syncvar_template_class_warns_unknown(self):
        exit_code, result = self.run_fixture("warn_syncvar_class_template.c")
        expected_message = (
            "[WARN] warn_syncvar_class_template.c line 1: class declaration not "
            "recognized; SyncVar checks skipped for this block (rule_id: "
            "ES-SYNCVAR-CLASS-UNKNOWN)."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-SYNCVAR-CLASS-UNKNOWN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_syncvar_class_template.c", result["warnings"][0]["file"])
        self.assertEqual(1, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])

    def test_syncvar_else_branch_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "bad_syncvar_in_else_branch.c",
            14,
            "unsupported preprocessor branch",
        )

    def test_syncvar_alternative_guard_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "warn_syncvar_alternative_guard.c",
            13,
            "alternative guard 'if (GetGame().IsServer())'",
        )

    def test_syncvar_ggame_is_server_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "warn_syncvar_ggame_is_server.c",
            13,
            "alternative guard",
        )

    def test_syncvar_generic_return_method_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "warn_syncvar_method_generic_return.c",
            12,
            "method enclosing the assignment could not be parsed",
        )


class TestEsIntMinCompare(unittest.TestCase):
    def test_no_int_min_compare_passes(self):
        fixture = FIXTURES / "es" / "ok_int_min_no_compare.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_int_min_symbolic_warns(self):
        fixture = FIXTURES / "es" / "warn_int_min_compare_symbolic.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-INT-MIN-COMPARISON", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_int_min_compare_symbolic.c", warning["file"])
        self.assertEqual(5, warning["line"])
        self.assertIn("int.MIN", warning["message"])
        self.assertIn("pitfalls-advanced.md:5-14", warning["message"])
        assert_standard_findings(self, result)

    def test_int_min_literal_warns(self):
        fixture = FIXTURES / "es" / "warn_int_min_compare_literal.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-INT-MIN-COMPARISON", warning["rule_id"])
        self.assertEqual("warn_int_min_compare_literal.c", warning["file"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_int_min_inside_string_literal_passes(self):
        fixture = FIXTURES / "es" / "ok_int_min_string_literal.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])


class TestEsGettypeExactMatch(unittest.TestCase):
    def test_iskindof_passes(self):
        fixture = FIXTURES / "es" / "ok_gettype_iskindof.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_gettype_enum_compare_passes(self):
        fixture = FIXTURES / "es" / "ok_gettype_enum_compare.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_gettype_not_equal_warns(self):
        fixture = FIXTURES / "es" / "warn_gettype_equality.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-GETTYPE-EXACT-MATCH", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_gettype_equality.c", warning["file"])
        self.assertEqual(5, warning["line"])
        self.assertIn("IsKindOf", warning["message"])
        self.assertIn("rules 31-32", warning["message"])
        assert_standard_findings(self, result)

    def test_gettype_equal_warns(self):
        fixture = FIXTURES / "es" / "warn_gettype_equality_eq.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-GETTYPE-EXACT-MATCH", warning["rule_id"])
        self.assertEqual("warn_gettype_equality_eq.c", warning["file"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_gettype_typename_uppercase_warns(self):
        fixture = FIXTURES / "es" / "warn_gettype_typename_uppercase.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-GETTYPE-EXACT-MATCH", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_gettype_typename_uppercase.c", warning["file"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_gettype_inside_string_literal_passes(self):
        fixture = FIXTURES / "es" / "ok_gettype_in_string.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])


class TestEsLayoutPathPboprefix(unittest.TestCase):
    def test_layout_path_match_passes(self):
        addon_root = FIXTURES / "layout_pboprefix" / "ok_match"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(2, result["info"]["files_scanned"])

    def test_layout_path_mismatch_fails(self):
        addon_root = FIXTURES / "layout_pboprefix" / "bad_mismatch"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-LAYOUT-PATH-PBOPREFIX-MISMATCH", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("dialog.c", error["file"])
        self.assertEqual(5, error["line"])
        self.assertIn("SimpleGroup", error["message"])
        self.assertIn("LFPG_Territory", error["message"])
        self.assertIn("rule 34", error["message"])
        assert_standard_findings(self, result)

    def test_no_pboprefix_skips_check(self):
        # When $PBOPREFIX$ is missing, the check is skipped silently — phase 1
        # does not bootstrap the prefix from other sources. The .c file uses a
        # layout path that would normally fail; without the prefix anchor, the
        # detector returns no findings.
        addon_root = FIXTURES / "layout_pboprefix" / "ok_no_prefix"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

class TestLayoutLeafMissingBraces(unittest.TestCase):
    # LAYOUT-LEAF-MISSING-BRACES is quarantined (BUG-029): a leaf widget
    # without a child { } block is valid Enfusion layout syntax. The detector
    # file remains on disk but is not imported or called. These tests assert
    # the run loop no longer emits that rule, including on the former
    # "bad_*" fixtures that the false rule used to fail.

    def run_layout_fixture(self, fixture_name):
        fixture = FIXTURES / "layout_braces" / fixture_name
        return script_validator.run([str(fixture)])

    def assert_layout_passes(self, fixture_name):
        exit_code, result = self.run_layout_fixture(fixture_name)

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])
        assert_standard_findings(self, result)

    def test_leaf_with_empty_braces_passes(self):
        self.assert_layout_passes("ok_leaf_with_empty_braces.layout")

    def test_leaf_missing_braces_is_valid_syntax(self):
        self.assert_layout_passes("bad_leaf_missing_braces.layout")

    def test_inline_widget_passes(self):
        self.assert_layout_passes("ok_inline_widget.layout")

    def test_inline_missing_braces_is_valid_syntax(self):
        self.assert_layout_passes("bad_inline_missing_braces.layout")

    def test_fp_traps_pass(self):
        for fixture_name in (
            "ok_nested_widgets.layout",
            "ok_scriptparams_double_block.layout",
            "ok_string_with_brace_literal.layout",
        ):
            with self.subTest(fixture_name=fixture_name):
                self.assert_layout_passes(fixture_name)

class TestEsRefAutoptrCombined(unittest.TestCase):
    def test_separate_qualifiers_and_generics_pass(self):
        fixture = FIXTURES / "es" / "ok_ref_autoptr_generics.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ref_autoptr_combined_warns(self):
        fixture = FIXTURES / "es" / "warn_ref_autoptr_combined.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-REF-AUTOPTR-COMBINED", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_ref_autoptr_combined.c", warning["file"])
        self.assertEqual(3, warning["line"])
        self.assertIn("SKILL.md:38", warning["message"])
        assert_standard_findings(self, result)

    def test_autoptr_ref_combined_warns(self):
        fixture = FIXTURES / "es" / "warn_autoptr_ref_combined.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-REF-AUTOPTR-COMBINED", warning["rule_id"])
        self.assertEqual("warn_autoptr_ref_combined.c", warning["file"])
        self.assertEqual(3, warning["line"])
        assert_standard_findings(self, result)


class TestEsOnMouseLeaveParamCount(unittest.TestCase):
    def test_four_param_declaration_and_calls_pass(self):
        fixture = FIXTURES / "es" / "ok_onmouseleave_signature.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_three_param_declaration_warns(self):
        fixture = FIXTURES / "es" / "warn_onmouseleave_3params.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-ONMOUSELEAVE-PARAM-COUNT", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_onmouseleave_3params.c", warning["file"])
        self.assertEqual(3, warning["line"])
        self.assertIn("SKILL.md:635", warning["message"])
        assert_standard_findings(self, result)

    def test_delegate_class_without_handler_base_passes(self):
        fixture = FIXTURES / "es" / "ok_onmouseleave_delegate_3params.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_three_param_multiline_declaration_warns(self):
        fixture = FIXTURES / "es" / "warn_onmouseleave_3params_multiline.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-ONMOUSELEAVE-PARAM-COUNT", warning["rule_id"])
        self.assertEqual(
            "warn_onmouseleave_3params_multiline.c", warning["file"]
        )
        self.assertEqual(3, warning["line"])
        assert_standard_findings(self, result)


class TestEsRegisterRecipesTypo(unittest.TestCase):
    def test_correct_double_i_hook_passes(self):
        fixture = FIXTURES / "es" / "ok_registerrecipies_correct.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_override_single_i_fails(self):
        fixture = FIXTURES / "es" / "bad_registerrecipes_override.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        error = result["errors"][0]
        self.assertEqual("ES-REGISTERRECIPES-TYPO", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_registerrecipes_override.c", error["file"])
        self.assertEqual(3, error["line"])
        self.assertIn("RegisterRecipies", error["message"])
        assert_standard_findings(self, result)

    def test_plain_single_i_warns(self):
        fixture = FIXTURES / "es" / "warn_registerrecipes_plain.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-REGISTERRECIPES-TYPO", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual(3, warning["line"])
        self.assertIn("silently not registered", warning["message"])
        assert_standard_findings(self, result)


class TestEsNonexistentMethod(unittest.TestCase):
    def test_verified_alternatives_pass(self):
        fixture = FIXTURES / "es" / "ok_nonexistent_method_alternatives.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_nonexistent_method_calls_fail(self):
        fixture = FIXTURES / "es" / "bad_nonexistent_method_call.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(3, len(result["errors"]))
        by_line = {error["line"]: error for error in result["errors"]}
        self.assertEqual({5, 6, 11}, set(by_line.keys()))
        for error in result["errors"]:
            self.assertEqual("ES-NONEXISTENT-METHOD", error["rule_id"])
            self.assertEqual("FAIL", error["severity"])
        self.assertIn("InsertIngredient", by_line[5]["message"])
        self.assertIn("SetIsCacheable", by_line[6]["message"])
        self.assertIn("DamageSystem.ExplosionDamage", by_line[11]["message"])
        assert_standard_findings(self, result)

    def test_mod_declared_homonym_passes(self):
        fixture = FIXTURES / "es" / "ok_nonexistent_method_declared.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestEsRespawnEquipOnClientRespawnEvent(unittest.TestCase):
    def test_kill_only_respawn_and_newevent_equip_pass(self):
        fixture = FIXTURES / "es" / "ok_onclientrespawn_kill_only.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_equip_in_respawn_event_warns(self):
        fixture = FIXTURES / "es" / "warn_onclientrespawn_equip.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(2, len(result["warnings"]))
        by_line = {warning["line"]: warning for warning in result["warnings"]}
        self.assertEqual({6, 7}, set(by_line.keys()))
        for warning in result["warnings"]:
            self.assertEqual(
                "ES-RESPAWN-EQUIP-IN-ONCLIENTRESPAWNEVENT", warning["rule_id"]
            )
            self.assertEqual("WARN", warning["severity"])
        self.assertIn("CreateInInventory", by_line[6]["message"])
        self.assertIn("CreateAttachment", by_line[7]["message"])
        self.assertIn("OnClientNewEvent", by_line[6]["message"])
        assert_standard_findings(self, result)


class TestFullCorpus(unittest.TestCase):
    def test_full_es_corpus_consolidated_json(self):
        exit_code, result = script_validator.run([str(FIXTURES / "es")])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(103, result["info"]["files_scanned"])
        assert_standard_findings(self, result)

        observed_errors = {
            (finding["rule_id"], pathlib.Path(finding["file"]).name)
            for finding in result["errors"]
        }
        observed_warnings = {
            (finding["rule_id"], pathlib.Path(finding["file"]).name)
            for finding in result["warnings"]
        }

        expected_errors = {
            ("ES-EMPTY-IFDEF", "bad_empty_ifdef_with_comments.c"),
            ("ES-EMPTY-IFDEF", "bad_empty_ifndef_with_comments.c"),
            ("ES-CTX-READ-UNCHECKED", "bad_ctx_read_unchecked_in_rpc.c"),
            (
                "ES-CTX-READ-UNCHECKED",
                "bad_ctx_read_unchecked_in_rpc_outer_server_guard.c",
            ),
            ("ES-CTX-READ-UNCHECKED", "bad_ctx_read_unchecked_onstoreload.c"),
            (
                "ES-CTX-READ-UNCHECKED",
                "bad_ctx_read_unchecked_onstoreload_multiline.c",
            ),
            (
                "ES-CTX-READ-UNCHECKED",
                "bad_ctx_read_unchecked_with_renamed_param.c",
            ),
            ("ES-SYNCVAR-CONTRACT", "bad_syncvar_dirty_in_other_method.c"),
            ("ES-SYNCVAR-CONTRACT", "bad_syncvar_register_outside_ctor.c"),
            ("ES-SYNCVAR-CONTRACT", "bad_syncvar_write_no_dirty.c"),
            ("ES-LOCAL-VAR-REDECLARE", "bad_local_var_redeclare_sibling.c"),
            ("ES-LOCAL-VAR-REDECLARE", "bad_local_var_redeclare_nested_for.c"),
            ("ES-MEMBER-REDECLARE-BASE", "bad_member_redeclare_base.c"),
            ("ES-OVERRIDE-PARAM-NAME-MISMATCH", "bad_override_param_mismatch.c"),
            ("ES-METHOD-NAME-COLLIDES-VANILLA-CLASS", "bad_method_name_collides.c"),
            ("ES-REGISTERRECIPES-TYPO", "bad_registerrecipes_override.c"),
            ("ES-NONEXISTENT-METHOD", "bad_nonexistent_method_call.c"),
            (
                "ES-OVERRIDE-OF-PLATFORM-GATED-METHOD",
                "bad_override_platform_gated.c",
            ),
        }
        expected_warnings = {
            ("ES-SOURCE-UNTERMINATED-BLOCK-COMMENT", "bad_unterminated_block_comment.c"),
            ("ES-SOURCE-UNTERMINATED-STRING", "bad_unterminated_string.c"),
            (
                "ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN",
                "bad_ifdef_empty_with_unsupported_only.c",
            ),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "bad_syncvar_in_else_branch.c"),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "ok_ifdef_with_unsupported_inner.c"),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "warn_endif_stray.c"),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "warn_ifdef_unterminated.c"),
            (
                "ES-CTX-READ-UNSUPPORTED-PATTERN",
                "warn_ctx_read_unchecked_combined_condition.c",
            ),
            ("ES-CTX-READ-UNSUPPORTED-PATTERN", "warn_ctx_read_in_try_catch.c"),
            ("ES-CTX-READ-UNCHECKED", "warn_ctx_read_unchecked_in_onvarsync.c"),
            (
                "ES-CTX-READ-UNCHECKED",
                "warn_ctx_read_unchecked_in_rpc_ifndef_server.c",
            ),
            ("ES-CTX-READ-UNCHECKED", "warn_ctx_read_unchecked_in_rpc_no_guard.c"),
            ("ES-SYNCVAR-CLASS-UNKNOWN", "warn_syncvar_class_template.c"),
            ("ES-SYNCVAR-UNSUPPORTED-PATTERN", "bad_syncvar_in_else_branch.c"),
            ("ES-SYNCVAR-UNSUPPORTED-PATTERN", "warn_syncvar_alternative_guard.c"),
            (
                "ES-SYNCVAR-UNSUPPORTED-PATTERN",
                "warn_syncvar_method_generic_return.c",
            ),
            ("ES-INT-MIN-COMPARISON", "warn_int_min_compare_symbolic.c"),
            ("ES-INT-MIN-COMPARISON", "warn_int_min_compare_literal.c"),
            ("ES-GETTYPE-EXACT-MATCH", "warn_gettype_equality.c"),
            ("ES-GETTYPE-EXACT-MATCH", "warn_gettype_equality_eq.c"),
            ("ES-GETTYPE-EXACT-MATCH", "warn_gettype_typename_uppercase.c"),
            ("ES-REF-AUTOPTR-COMBINED", "warn_ref_autoptr_combined.c"),
            ("ES-REF-AUTOPTR-COMBINED", "warn_autoptr_ref_combined.c"),
            ("ES-ONMOUSELEAVE-PARAM-COUNT", "warn_onmouseleave_3params.c"),
            (
                "ES-ONMOUSELEAVE-PARAM-COUNT",
                "warn_onmouseleave_3params_multiline.c",
            ),
            ("ES-REGISTERRECIPES-TYPO", "warn_registerrecipes_plain.c"),
            (
                "ES-RESPAWN-EQUIP-IN-ONCLIENTRESPAWNEVENT",
                "warn_onclientrespawn_equip.c",
            ),
        }

        self.assertTrue(expected_errors.issubset(observed_errors))
        self.assertTrue(expected_warnings.issubset(observed_warnings))


class TestEsLocalVarRedeclare(unittest.TestCase):
    def test_sibling_redeclare_fails(self):
        fixture = FIXTURES / "es" / "bad_local_var_redeclare_sibling.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-LOCAL-VAR-REDECLARE", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_local_var_redeclare_sibling.c", error["file"])
        self.assertEqual(11, error["line"])
        self.assertIn("multiple declaration", error["message"])
        assert_standard_findings(self, result)

    def test_nested_for_shadow_fails(self):
        fixture = FIXTURES / "es" / "bad_local_var_redeclare_nested_for.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual("ES-LOCAL-VAR-REDECLARE", result["errors"][0]["rule_id"])
        self.assertEqual(6, result["errors"][0]["line"])
        assert_standard_findings(self, result)

    def test_hoisted_single_declaration_passes(self):
        fixture = FIXTURES / "es" / "ok_local_var_hoisted.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_same_name_distinct_methods_passes(self):
        fixture = FIXTURES / "es" / "ok_local_var_distinct_methods.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_sequential_for_loops_pass(self):
        fixture = FIXTURES / "es" / "ok_local_var_sequential_for.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_ifdef_else_same_name_is_not_redeclare(self):
        fixture = FIXTURES / "es" / "ok_local_var_ifdef_else.c"
        exit_code, result = script_validator.run([str(fixture)])

        redeclare = [
            error
            for error in result["errors"]
            if error["rule_id"] == "ES-LOCAL-VAR-REDECLARE"
        ]
        self.assertEqual([], redeclare)
        assert_standard_findings(self, result)


class TestEsMemberRedeclareBase(unittest.TestCase):
    def test_member_redeclare_fails(self):
        fixture = FIXTURES / "es" / "bad_member_redeclare_base.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-MEMBER-REDECLARE-BASE", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(3, error["line"])
        self.assertIn("m_NoiseSystem", error["message"])
        assert_standard_findings(self, result)

    def test_distinct_member_name_passes(self):
        fixture = FIXTURES / "es" / "ok_member_distinct_name.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_unknown_base_passes(self):
        fixture = FIXTURES / "es" / "ok_member_unknown_base.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsOverrideParamNameMismatch(unittest.TestCase):
    def test_param_name_mismatch_fails(self):
        fixture = FIXTURES / "es" / "bad_override_param_mismatch.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-OVERRIDE-PARAM-NAME-MISMATCH", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(3, error["line"])
        self.assertIn("action_data", error["message"])
        assert_standard_findings(self, result)

    def test_param_name_match_passes(self):
        fixture = FIXTURES / "es" / "ok_override_param_match.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_unknown_override_method_passes(self):
        fixture = FIXTURES / "es" / "ok_override_unknown_method.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsConfigNestedOverride(unittest.TestCase):
    def test_missing_forward_ref_fails(self):
        addon_root = FIXTURES / "config_nested" / "bad"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual(
            "ES-CONFIG-NESTED-OVERRIDE-NO-FORWARDREF", error["rule_id"]
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(14, error["line"])
        self.assertIn("SimulationModule", error["message"])
        assert_standard_findings(self, result)

    def test_with_forward_ref_passes(self):
        addon_root = FIXTURES / "config_nested" / "ok"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsInputsXmlNotRegistered(unittest.TestCase):
    def test_inputs_xml_present_unregistered_fails(self):
        addon_root = FIXTURES / "config_inputs" / "bad_missing"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        error = next(
            e for e in result["errors"]
            if e["rule_id"] == "CONFIG-INPUTS-XML-NOT-REGISTERED"
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(1, error["line"])
        assert_standard_findings(self, result)

    def test_inputs_xml_registered_passes(self):
        addon_root = FIXTURES / "config_inputs" / "ok_registered"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_no_inputs_xml_passes(self):
        addon_root = FIXTURES / "config_inputs" / "ok_no_inputs_xml"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsAttachmentsCompoundAppendCrossPbo(unittest.TestCase):
    def test_crosspbo_append_warns(self):
        addon_root = FIXTURES / "config_attachments" / "bad"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        warning = next(
            w for w in result["warnings"]
            if w["rule_id"] == "ES-ATTACHMENTS-COMPOUND-APPEND-CROSSPBO"
        )
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual(6, warning["line"])
        assert_standard_findings(self, result)

    def test_full_list_passes(self):
        addon_root = FIXTURES / "config_attachments" / "ok_full_list"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["warnings"])

    def test_same_pbo_parent_passes(self):
        addon_root = FIXTURES / "config_attachments" / "ok_same_pbo"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["warnings"])


class TestPdrivePathRvmat(unittest.TestCase):
    def test_relative_path_passes(self):
        fixture = FIXTURES / "pdrive" / "ok_relative_path.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_pdrive_path_warns(self):
        fixture = FIXTURES / "pdrive" / "bad_pdrive_path.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("RVMAT-PDRIVE-PATH", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("bad_pdrive_path.rvmat", warning["file"])
        self.assertEqual(3, warning["line"])
        assert_standard_findings(self, result)

    def test_pdrive_in_comment_passes(self):
        fixture = FIXTURES / "pdrive" / "ok_pdrive_in_comment.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["warnings"])


class TestPdrivePathConfig(unittest.TestCase):
    def test_pdrive_path_warns(self):
        addon_root = FIXTURES / "pdrive" / "config_bad"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        warning = next(
            w for w in result["warnings"] if w["rule_id"] == "CONFIG-PDRIVE-PATH"
        )
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_relative_path_passes(self):
        addon_root = FIXTURES / "pdrive" / "config_ok"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestEsInputsXmlWrongRoot(unittest.TestCase):
    def test_wrong_root_fails(self):
        addon_root = FIXTURES / "inputs_root" / "bad"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        error = next(
            e for e in result["errors"]
            if e["rule_id"] == "CONFIG-INPUTS-XML-WRONG-ROOT"
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(1, error["line"])
        self.assertEqual("inputs.xml", error["file"])
        self.assertIn("modded_inputs", error["message"])
        assert_standard_findings(self, result)

    def test_correct_root_passes(self):
        addon_root = FIXTURES / "inputs_root" / "ok"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_non_inputs_xml_ignored(self):
        addon_root = FIXTURES / "inputs_root" / "ok_other_xml"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestLayoutXmlFormat(unittest.TestCase):
    def test_brace_layout_passes(self):
        fixture = FIXTURES / "layout_xml" / "ok_brace.layout"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_xml_layout_fails(self):
        fixture = FIXTURES / "layout_xml" / "bad_xml.layout"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("LAYOUT-XML-FORMAT", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_xml.layout", error["file"])
        self.assertEqual(1, error["line"])
        self.assertIn("XML", error["message"])
        assert_standard_findings(self, result)


class TestEsLayoutFileMissing(unittest.TestCase):
    def test_present_layout_passes(self):
        addon_root = FIXTURES / "layout_file_missing" / "ok_present"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(2, result["info"]["files_scanned"])

    def test_missing_layout_fails(self):
        addon_root = FIXTURES / "layout_file_missing" / "bad_missing"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-LAYOUT-FILE-MISSING", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("dialog.c", error["file"])
        self.assertEqual(5, error["line"])
        self.assertIn("my_dialog.layout", error["message"])
        assert_standard_findings(self, result)

    def test_no_prefix_skips(self):
        addon_root = FIXTURES / "layout_file_missing" / "ok_no_prefix"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestEsMethodNameCollidesVanillaClass(unittest.TestCase):
    def test_safe_method_name_passes(self):
        fixture = FIXTURES / "es" / "ok_method_name_safe.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_collision_fails(self):
        fixture = FIXTURES / "es" / "bad_method_name_collides.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-METHOD-NAME-COLLIDES-VANILLA-CLASS", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_method_name_collides.c", error["file"])
        self.assertEqual(3, error["line"])
        self.assertIn("LogManager", error["message"])
        assert_standard_findings(self, result)


class TestEsOverrideOfPlatformGatedMethod(unittest.TestCase):
    def test_unguarded_override_fails(self):
        fixture = FIXTURES / "es" / "bad_override_platform_gated.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual(
            "ES-OVERRIDE-OF-PLATFORM-GATED-METHOD", error["rule_id"]
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_override_platform_gated.c", error["file"])
        self.assertEqual(3, error["line"])
        self.assertIn("GetConsoleToolbarText", error["message"])
        self.assertIn("PLATFORM_CONSOLE", error["message"])
        assert_standard_findings(self, result)

    def test_guarded_override_passes(self):
        fixture = FIXTURES / "es" / "ok_override_platform_gated.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_other_class_override_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "ok_other_class.c"
            path.write_text(
                "class WidgetHost\n"
                "{\n"
                "    override string GetConsoleToolbarText()\n"
                "    {\n"
                "        return \"\";\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            exit_code, result = script_validator.run([str(path)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])



class TerseOutputTests(unittest.TestCase):
    """The verdict must be the FIRST line: a reader that stops there has the answer."""

    def test_pass_is_a_single_line(self):
        _code, result = script_validator.run([str(FIXTURES / "empty")])
        terse = script_validator.format_terse(result)

        self.assertEqual("PASS", terse)

    def test_verdict_leads_and_counts_are_summarised(self):
        result = {
            "status": "FAIL",
            "errors": [{"rule_id": "ES-NO-DELETE", "message": "boom"}],
            "warnings": [{"rule_id": "ES-EMPTY-IFDEF", "message": "meh"}],
        }
        lines = script_validator.format_terse(result).split("\n")

        self.assertEqual("FAIL - 1 error, 1 warning", lines[0])
        self.assertEqual(3, len(lines))
        self.assertIn("ES-NO-DELETE", lines[1])
        self.assertIn("ES-EMPTY-IFDEF", lines[2])

    def test_json_stays_the_default(self):
        parser = script_validator.build_parser()

        self.assertFalse(parser.parse_args(["some_root"]).terse)
        self.assertTrue(parser.parse_args(["some_root", "--terse"]).terse)

class TestProtectedCrossModule(unittest.TestCase):
    """ES-PROTECTED-CROSS-MODULE — verified at runtime 2026-09-17.

    A disposable probe was built into a PBO and booted on a dedicated server:
    World compiled, Mission did not, with "Variable 'm_LFPG_ProbeValue' is
    protected" / "Can't compile \"Mission\" script module!".
    """

    def test_mission_reading_world_protected_fails(self):
        fixture = FIXTURES / "protected_cross_module" / "bad"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-PROTECTED-CROSS-MODULE", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertIn("m_FxHidden", error["message"])
        self.assertIn("4_World", error["message"])
        assert_standard_findings(self, result)

    def test_public_accessor_passes(self):
        fixture = FIXTURES / "protected_cross_module" / "ok_accessor"
        _exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)

    def test_same_module_access_passes(self):
        """`protected` within one module is legal and must not fire."""
        fixture = FIXTURES / "protected_cross_module" / "ok_same_module"
        _exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)


class TestExternalConsumerMissing(unittest.TestCase):
    """ES-EXTERNAL-CONSUMER-MISSING — observed 2026-09-17.

    A refactor deleted facade methods after proving no file under the addon's
    own scripts/ called them. The mission init.c did, and the server refused to
    compile it. The deleted names still existed on a subclass, so a plain
    "declared somewhere" search stays silent: the receiver's declared type is
    what decides.
    """

    def test_external_call_to_deleted_method_fails(self):
        fixture = FIXTURES / "external_consumer"
        exit_code, result = script_validator.run(
            [str(fixture / "bad"),
             "--external-scripts", str(fixture / "bad_external")]
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-EXTERNAL-CONSUMER-MISSING", error["rule_id"])
        self.assertIn("FX_GetOutgoing", error["message"])
        self.assertIn("FX_GraphImpl", error["message"])
        assert_standard_findings(self, result)

    def test_method_declared_on_receiver_passes(self):
        fixture = FIXTURES / "external_consumer"
        _exit_code, result = script_validator.run(
            [str(fixture / "ok_declared"),
             "--external-scripts", str(fixture / "ok_external")]
        )

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)

    def test_vanilla_method_not_declared_in_addon_passes(self):
        """The addon declares the name nowhere, so it comes from vanilla."""
        fixture = FIXTURES / "external_consumer"
        _exit_code, result = script_validator.run(
            [str(fixture / "ok_vanilla_method"),
             "--external-scripts", str(fixture / "ok_vanilla_external")]
        )

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)

    def test_check_is_inert_without_external_roots(self):
        """Without --external-scripts there is nothing to compare against."""
        fixture = FIXTURES / "external_consumer" / "bad"
        _exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)


RESERVED = FIXTURES / "reserved_word_identifier"
RESERVED_RULE = "ES-RESERVED-WORD-IDENTIFIER"


def _errors_of(result, rule_id):
    return [e for e in result["errors"] if e["rule_id"] == rule_id]


class TestReservedWordIdentifier(unittest.TestCase):
    """ES-RESERVED-WORD-IDENTIFIER: a keyword used as a name.

    sealed: parameter, DayZDiag 1.29.163709, 2026-10-02, "Expected name, not a
    keyword 'sealed'". local: local variable, DayZDiag 1.30.164014 (Exp),
    2026-09-28, "Broken expression (missing ';'?)". owned and out: the same
    error on a local (enforce-script-reference SKILL.md).
    """

    def test_sealed_parameter_fails(self):
        exit_code, result = script_validator.run([str(RESERVED / "bad_sealed_param")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, RESERVED_RULE)
        self.assertEqual([5], [e["line"] for e in errors])
        self.assertIn("fx_probe_sealed.c", errors[0]["file"])
        self.assertIn("'sealed'", errors[0]["message"])
        self.assertEqual("FAIL", errors[0]["severity"])
        assert_standard_findings(self, result)

    def test_local_variable_fails_on_its_declaration(self):
        exit_code, result = script_validator.run([str(RESERVED / "bad_local_var")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, RESERVED_RULE)
        # The declaration only; `local[0] = mx;` and `return local;` follow it.
        self.assertEqual([7], [e["line"] for e in errors])
        self.assertIn("'local'", errors[0]["message"])

    def test_owned_member_and_out_local_fail(self):
        _code, result = script_validator.run([str(RESERVED / "bad_owned_out")])

        errors = _errors_of(result, RESERVED_RULE)
        self.assertEqual(
            [(3, "owned"), (7, "out")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )

    def test_keywords_where_vanilla_puts_them_pass(self):
        _code, result = script_validator.run([str(RESERVED / "ok_modifiers")])

        self.assertEqual([], _errors_of(result, RESERVED_RULE))

    def test_only_branches_that_can_compile_are_judged(self):
        _code, result = script_validator.run([str(RESERVED / "preprocessor")])

        # `vector local;` and `EntityAI owned;` under #ifndef of macros this file
        # always defines (one of them under an #ifdef it guarantees) and
        # `int out;` under #if 0 never compile; `vector sealed;` compiles once
        # FX_SOME_OTHER_MOD's mod is loaded.
        self.assertEqual(
            [(16, "sealed")],
            [(e["line"], e["message"].split("'")[1])
             for e in _errors_of(result, RESERVED_RULE)],
        )

    def test_else_follows_its_macro_both_ways(self):
        _code, result = script_validator.run([str(RESERVED / "else_branches")])

        # FX_ELSE_ON is always defined: the #else of its #ifndef compiles
        # (`vector local;`) and so does its #ifdef branch (`EntityAI owned;`);
        # `vector sealed;` and `int out;` never compile.
        self.assertEqual(
            [(12, "local"), (15, "owned")],
            [(e["line"], e["message"].split("'")[1])
             for e in _errors_of(result, RESERVED_RULE)],
        )

    def test_names_without_their_type_before_them_on_the_line(self):
        exit_code, result = script_validator.run(
            [str(RESERVED / "bad_more_declarations")]
        )

        # A parameter split over two lines, a later declarator, a foreach
        # variable and the second variable of a for header; not the use of
        # `out` among the arguments of line 11. Later declarators end with
        # `=`, `;`, `,` and `[` (review round 2, R2-06).
        self.assertEqual(1, exit_code)
        self.assertEqual(
            [(8, "sealed"), (10, "out"), (12, "local"), (15, "owned"),
             (18, "local"), (19, "owned"), (20, "out")],
            [(e["line"], e["message"].split("'")[1])
             for e in _errors_of(result, RESERVED_RULE)],
        )


MODULO = FIXTURES / "modulo_float_context"
MODULO_RULE = "ES-MODULO-FLOAT-CONTEXT"


class TestModuloFloatContext(unittest.TestCase):
    """ES-MODULO-FLOAT-CONTEXT: '%' in an expression with a float literal.

    `((g % 5) - 2) * 7.0` failed on DayZDiag 1.29 (2026-09-28) and
    `float ox = (n % 4) * 0.7 - 1.05;` on DayZ 1.30 Exp (2026-09-24), both
    with "Unknown operator '%'".
    """

    def test_both_failing_shapes_fail(self):
        exit_code, result = script_validator.run([str(MODULO / "bad")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, MODULO_RULE)
        self.assertEqual([7, 12], [e["line"] for e in errors])
        self.assertIn("7.0", errors[0]["message"])
        self.assertIn("0.7", errors[1]["message"])
        assert_standard_findings(self, result)

    def test_integer_modulo_and_the_int_local_fix_pass(self):
        _code, result = script_validator.run([str(MODULO / "ok")])

        self.assertEqual([], _errors_of(result, MODULO_RULE))

    def test_expression_boundaries(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        def flagged(statement):
            source = (
                "class C\n{\n    void F(int n, int i)\n    {\n        %s\n    }\n}\n"
                % statement
            )
            stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
            return bool(check_es_modulo_float_context(source, stripped, "x.c"))

        # Same expression as the float literal: judged.
        self.assertTrue(flagged("float a = 0.5 * (n % 4);"))
        self.assertTrue(flagged("return (n % 4) * 0.5;"))
        self.assertTrue(flagged("SetPos(1, ((n % 3) + 1) * 2.5);"))
        # Another expression: an argument, an index, a comparison, another
        # statement, or a call's arguments. Not judged.
        self.assertFalse(flagged("Foo(n % 4, 0.5);"))
        self.assertFalse(flagged("float b = m_Arr[i % 3] * 0.5;"))
        self.assertFalse(flagged("if (n % 2 == 0) x = 1.5;"))
        self.assertFalse(flagged("int k = n % 4; float c = k * 0.5;"))
        self.assertFalse(flagged("float d = Math.Floor(n % 4) * 0.5;"))
        self.assertFalse(flagged("n %= 4;"))
        # A string literal makes `+` a concatenation: not judged, also when
        # the string comes first.
        self.assertFalse(flagged('Print("cell " + (n % 4) + " of " + 0.5);'))
        self.assertFalse(flagged('Print("cell " + (n % 4) + 0.5);'))
        # A comment is not part of the expression, quotes in it included.
        self.assertFalse(flagged("int k = n % 4; // scale by 0.5 later"))
        self.assertTrue(flagged("float e = (n % 4) /* cell */ * 0.5;"))
        self.assertTrue(flagged('float e2 = (n % 4) /* "cell" */ * 0.5;'))
        self.assertTrue(flagged('float e3 = (n % 4) // "cell"\n            * 0.5;'))
        # An int cast makes an int of its operand, float literal or not.
        self.assertFalse(flagged("int j = n % (int)2.5;"))
        self.assertFalse(flagged("int j2 = n % ((int)-2.5);"))
        self.assertFalse(flagged("int j3 = n % (int)(2.5 * i);"))
        self.assertTrue(flagged("float j4 = (n % 4) * (int)i + 0.5;"))
        # A condition in parentheses is a value of its own; behind a `?` only
        # the results count; arithmetic before a comparison is still judged.
        self.assertFalse(flagged("int b = n % (i > 0.5);"))
        self.assertFalse(flagged("float t = (n % 4) * (i > 0.5 ? 1 : 2);"))
        self.assertTrue(flagged("float t2 = (n % 4) * (i > 1 ? 0.5 : 2);"))
        self.assertTrue(flagged("bool t3 = (n % 4 * 0.5 > 2);"))
        self.assertTrue(flagged("float t4 = (n % 4) * (Max(i > 1, 2) + 0.5);"))
        # Code that never compiles is not judged; another mod's branch is.
        self.assertFalse(flagged("#if 0\nfloat g = (n % 4) * 0.5;\n#endif"))
        self.assertTrue(flagged("#ifdef FX_OTHER_MOD\nfloat h = (n % 4) * 0.5;\n#endif"))

    def test_an_expression_skips_dead_lines_and_other_branches_of_its_blocks(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        def flagged(body):
            source = "class C\n{\n    int F(int n)\n    {\n%s\n    }\n}\n" % body
            stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
            return bool(check_es_modulo_float_context(source, stripped, "x.c"))

        # Every block around the `%` counts, not only the innermost one
        # (review round 2, R2-05).
        self.assertFalse(flagged(
            "        return n\n"
            "#ifdef FX_OUTER\n#ifdef FX_INNER\n            % 4\n"
            "#else\n            % 4\n#endif\n"
            "#else\n            * 0.5\n#endif\n        ;"
        ))

        # A float in a branch that never compiles is no part of the
        # expression (review round 1, R01).
        self.assertFalse(flagged(
            "#define FX_INTEGER\n"
            "        return (n % 4)\n"
            "#ifdef FX_INTEGER\n            + 1\n"
            "#else\n            * 0.5\n#endif\n        ;"
        ))
        # Nor is a float in the other branch of the block the `%` sits in,
        # whatever the macro: the two never compile together.
        self.assertFalse(flagged(
            "        return n\n"
            "#ifdef FX_OTHER_MOD\n            % 4\n"
            "#else\n            * 0.5\n#endif\n        ;"
        ))
        # A float in a branch that compiles along with the `%` is.
        self.assertTrue(flagged(
            "        return (n % 4)\n"
            "#ifdef FX_OTHER_MOD\n            * 0.5\n#endif\n        ;"
        ))

    def test_deep_parentheses_end_in_a_finding_not_an_exception(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        # Deeper than the interpreter's recursion limit (review round 2,
        # R2-01: 1100 pairs raised RecursionError).
        depth = sys.getrecursionlimit() + 200
        statement = (
            "return (n % 4) * " + "(" * depth + "0.7" + ")" * depth + " - 1.05;"
        )
        source = "class C\n{\n    float F(int n)\n    {\n        %s\n    }\n}\n" % statement
        stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
        errors = check_es_modulo_float_context(source, stripped, "x.c")

        self.assertEqual([5], [e["line"] for e in errors])
        self.assertIn("0.7", errors[0]["message"])

    def test_an_index_before_the_float_does_not_end_the_expression(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        # The index is skipped and the expression reads on to the float after
        # it, at the top level and inside a group (review round 3, R3-01:
        # ending the expression at an index kept every other test green).
        source = (
            "class C\n{\n    int m_Values[2];\n    float F(int n, int i)\n    {\n"
            "        float a = (n % 4) + m_Values[i] * 0.5;\n"
            "        return (n % 4) * (m_Values[0] + 2.5);\n"
            "    }\n}\n"
        )
        stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
        errors = check_es_modulo_float_context(source, stripped, "x.c")

        self.assertEqual([6, 7], [e["line"] for e in errors])
        self.assertIn("float literal 0.5.", errors[0]["message"])
        self.assertIn("float literal 2.5.", errors[1]["message"])

    def test_string_spans_are_the_strings_the_stripper_blanks(self):
        from detectors.es_modulo_float_context import _string_spans
        from stripper import strip_enforce_comments_and_strings

        source = (
            'a = "x \\" // y" + b; // "not a string"\n'
            '/* "nor this" */ c = "z";\n'
            'd = "open'
        )
        stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
        spans = _string_spans(source)

        self.assertEqual(
            ['"x \\" // y"', '"z"', '"open'],
            [source[start:end] for start, end in spans],
        )
        for start, end in spans:
            self.assertEqual("", stripped[start:end].strip())


UNDEFINED = FIXTURES / "undefined_class_ref"
UNDEFINED_RULE = "ES-UNDEFINED-CLASS-REF"


def _undefined_run(fixture, *extra):
    return script_validator.run(
        [str(UNDEFINED / fixture), "--vanilla-root", str(UNDEFINED / "vanilla")]
        + [str(arg) for arg in extra]
    )


def _rule_errors(result):
    return [e for e in result["errors"] if e["rule_id"] == UNDEFINED_RULE]


def _rule_skips(result):
    return [
        s for s in result["info"].get("skipped_checks", [])
        if s["rule_id"] == UNDEFINED_RULE
    ]


class TestUndefinedClassRef(unittest.TestCase):
    """ES-UNDEFINED-CLASS-REF — observed 2026-09-19 on TransferZ PR #12.

    The PR deleted class TransferZExternalStagingSortPlanner from 4_World while
    5_Mission still called TransferZExternalStagingSortPlanner.Sort(...). The
    type existed in no module, so Mission could not compile; the linter said
    WARN with 0 errors. `bad_mission_ref` is that shape with fixture names.
    """

    def test_mission_calls_class_that_exists_in_no_module_fails(self):
        exit_code, result = _undefined_run("bad_mission_ref")

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual(UNDEFINED_RULE, error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(11, error["line"])
        self.assertIn("fx_maintenance_client.c", error["file"])
        self.assertIn("FX_ExternalStagingSortPlanner", error["message"])
        self.assertIn("5_Mission", error["message"])
        self.assertEqual([], _rule_skips(result))
        assert_standard_findings(self, result)

    def test_same_tree_with_the_class_declared_passes(self):
        exit_code, result = _undefined_run("ok_mission_ref")

        self.assertEqual(0, exit_code)
        self.assertEqual([], result["errors"])
        self.assertEqual([], _rule_skips(result))

    def test_each_reference_form_and_macro_gate(self):
        _exit_code, result = _undefined_run("forms")

        flagged = {
            e["message"].split("'")[1] for e in _rule_errors(result)
        }
        self.assertEqual(
            {
                "FX_MissingNew",
                "FX_MissingCast",
                "FX_MissingDecl",
                "FX_MissingTemplateArg",
                "FX_MissingStatic",
                # a space before the call's parenthesis, as in vanilla's
                # `Math.Sqrt (` (5_mission/dayzintroscenepc.c:31)
                "FX_MissingSpacedCall",
                # judged: DIAG_DEVELOPER is a build flag vanilla tests, so both
                # of its branches compile in some build; FX_FORMS_ON is in the
                # addon's defines[] and FX_LOCAL_FLAG is #define'd, so the
                # branch where they are defined compiles
                "FX_MissingUnderVanillaMacro",
                "FX_MissingUnderVanillaElse",
                "FX_MissingUnderConfigDefine",
                "FX_MissingUnderLocalDefine",
                # FX_DIAG_ONLY_FLAG is #define'd only under #ifdef DIAG_DEVELOPER,
                # and FX_CONDITIONAL_CONFIG_FLAG is in a defines[] under
                # #ifdef FX_OPTIONAL_MOD: neither is always on, so their
                # #ifndef branches compile too
                "FX_MissingUnderConditionalDefine",
                "FX_MissingUnderConditionalConfigDefine",
                # named as a template argument in an unjudged branch: a comma
                # inside `<...>` does not declare a variable
                "FX_MissingBehindTemplate",
            },
            flagged,
        )
        # Not flagged: a PascalCase member used as a receiver (Planner), enum
        # access, a typedef, a template parameter, a vanilla class declared
        # under #ifdef, a `/*sealed*/ class`, code under another mod's flag,
        # the second variable of `string fx_first, FX_Second;`, and the
        # #ifndef / #else branches of macros the addon always defines.
        for name in ("Planner", "EVanillaMode", "TStringArray", "TItem",
                     "FX_VanillaDiagOnly", "PlayerBase", "FX_OptionalDependency",
                     "SurfaceDetectionParameters", "FX_Second",
                     "FX_DeadUnderIfndef", "FX_DeadUnderElse"):
            self.assertNotIn(name, flagged)
        assert_standard_findings(self, result)

    def test_uncovered_dependency_is_skipped_not_failed(self):
        """requiredAddons names a mod no scanned root provides: the type may live there."""
        exit_code, result = _undefined_run("dependency")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("FX_Dep_Scripts", skips[0]["reason"])
        self.assertEqual(
            {"FX_DepManager", "FX_GonePlanner"},
            {item["name"] for item in skips[0]["unresolved"]},
        )

    def test_dependency_passed_as_external_root_turns_skip_into_verdict(self):
        exit_code, result = _undefined_run(
            "dependency",
            "--external-scripts", UNDEFINED / "dependency_external",
        )

        self.assertEqual(1, exit_code)
        errors = _rule_errors(result)
        self.assertEqual(1, len(errors))
        self.assertIn("FX_GonePlanner", errors[0]["message"])
        self.assertEqual([], _rule_skips(result))

    def test_dependency_named_by_a_macro_is_unknown(self):
        exit_code, result = _undefined_run("macro_required_addon")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("FX_DEPENDENCY (not a string literal)", skips[0]["reason"])
        self.assertIn("123 (not a string literal)", skips[0]["reason"])

    def test_dependency_of_a_dependency_must_be_scanned_too(self):
        exit_code, result = _undefined_run(
            "transitive",
            "--external-scripts", UNDEFINED / "transitive_dep_a",
        )

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("FX_DepB_Scripts", skips[0]["reason"])

        exit_code, result = _undefined_run(
            "transitive",
            "--external-scripts", UNDEFINED / "transitive_dep_a",
            "--external-scripts", UNDEFINED / "transitive_dep_b",
        )

        self.assertEqual(1, exit_code)
        self.assertEqual(
            ["FX_GoneEverywhere"],
            [e["message"].split("'")[1] for e in _rule_errors(result)],
        )
        self.assertEqual([], _rule_skips(result))

    def test_a_dz_prefixed_mod_patch_is_not_vanilla(self):
        exit_code, result = _undefined_run("dz_prefixed_dependency")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("DZ_FX_ThirdParty", skips[0]["reason"])

    def test_a_file_is_not_a_vanilla_root(self):
        path, reason = vanilla_tree.resolve_vanilla_root(
            str(UNDEFINED / "bad_mission_ref" / "config.cpp")
        )

        self.assertIsNone(path)
        self.assertIn("vanilla tree not found", reason)

    def test_vanilla_root_that_is_empty_a_file_or_without_the_class_skips(self):
        with tempfile.TemporaryDirectory() as empty:
            with tempfile.TemporaryDirectory() as enum_only:
                # an enum named Managed is not the class every scripts tree
                # declares
                (pathlib.Path(enum_only) / "only.c").write_text(
                    "enum Managed\n{\n    FX_Value\n}\n", encoding="utf-8"
                )
                for vanilla in (empty, enum_only,
                                UNDEFINED / "bad_mission_ref" / "config.cpp"):
                    exit_code, result = script_validator.run(
                        [str(UNDEFINED / "bad_mission_ref"),
                         "--vanilla-root", str(vanilla)]
                    )

                    self.assertEqual(0, exit_code)
                    self.assertEqual([], _rule_errors(result))
                    self.assertEqual(1, len(_rule_skips(result)))

    def test_empty_required_addons_means_unknown_dependencies(self):
        exit_code, result = _undefined_run("no_required_addons")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertEqual(
            ["FX_SomeoneElsesType"], [item["name"] for item in skips[0]["unresolved"]]
        )

    def test_missing_vanilla_tree_is_a_skip_never_a_fail(self):
        exit_code, result = script_validator.run(
            [str(UNDEFINED / "bad_mission_ref"),
             "--vanilla-root", str(UNDEFINED / "no_such_vanilla_tree")]
        )

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("vanilla tree not found", skips[0]["reason"])

    def test_default_resolution_without_any_vanilla_tree_skips(self):
        """No --vanilla-root, no DAYZ_VANILLA_ROOT, no P:\\scripts (setUpModule)."""
        exit_code, result = script_validator.run([str(UNDEFINED / "bad_mission_ref")])

        self.assertEqual(0, exit_code)
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(_rule_skips(result)))

    def test_vanilla_tree_as_its_own_addon_is_clean(self):
        """The vanilla control shape: the tree is both the addon and vanilla.

        Its config-less layout must not turn into "dependencies unknown": a
        finding here has to fail the control, not hide in a SKIP.
        """
        vanilla = UNDEFINED / "vanilla"
        result = script_validator.validate_addon(vanilla, vanilla_root=vanilla)

        self.assertEqual([], _rule_errors(result))
        self.assertEqual([], _rule_skips(result))

    def test_skip_is_printed_after_the_verdict_in_terse_mode(self):
        _code, result = _undefined_run("dependency")
        lines = script_validator.format_terse(result).split("\n")

        self.assertEqual("PASS", lines[0])
        self.assertTrue(lines[1].startswith("  SKIP ES-UNDEFINED-CLASS-REF"))
        self.assertIn("FX_GonePlanner", lines[1])


if __name__ == "__main__":
    unittest.main()

