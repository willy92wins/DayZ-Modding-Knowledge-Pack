# Test suite — rules CANDIDATE-1..7 implemented in top-5; CANDIDATE-8/9/10 added 2026-05-19.
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import script_validator


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

if __name__ == "__main__":
    unittest.main()

