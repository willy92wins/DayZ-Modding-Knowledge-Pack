import argparse
import json
import pathlib
import re
import sys
import time


from shared.input_errors import (
    INPUT_ENCODING_ERROR_RULE_ID,
    INPUT_NOT_FOUND_RULE_ID,
    build_input_encoding_error,
    build_input_not_found_error,
    decode_error_line_number,
    discover_files,
    read_text_utf8_or_error,
    relative_path,
)
from shared.method_recognition import (
    METHOD_SIGNATURE_RE,
    PARAMS_READ_CONTEXT_PARAM_RE,
    collect_method_signature,
    count_braces,
    find_block_end_line,
    find_if_body_range,
    find_inline_pattern_line,
    find_method_for_line,
    find_method_regions,
    find_next_nonblank_line,
    find_params_read_context_param_name,
    find_signature_brace_line,
    first_param_is_params_read_context,
    method_is_onrpc,
    method_is_onstoreload,
)
from shared.control_flow import (
    ES_EMPTY_IFDEF_RE_CLOSE,
    ES_EMPTY_IFDEF_RE_OPEN,
    ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE,
    ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF,
    SERVER_GUARD_IF_RE,
    TRY_BLOCK_RE,
    compute_ifdef_stack_at,
    find_matching_endif_line,
    find_server_ifdef_block_for_line,
    line_is_inside_server_guard,
    line_is_inside_server_if_guard,
    line_is_inside_server_ifdef,
    line_is_inside_try_block,
    mark_supported_ifdef_stack_has_statement,
    unsupported_directive_opens_block,
    update_ifdef_stack_for_line,
)
from stripper import (
    UNTERMINATED_BLOCK_COMMENT_RULE_ID,
    UNTERMINATED_STRING_RULE_ID,
    make_stripper_warning,
    strip_enforce_comments_and_strings,
)
from detectors.rvmat import (
    RVMAT_MESSAGE,
    RVMAT_RULE_ID,
    RVMAT_SHADER_RE,
    check_rvmat_normalmapmacro,
    strip_rvmat_line_comment,
)
from detectors.es_no_delete import (
    ES_NO_DELETE_MESSAGE,
    ES_NO_DELETE_RE,
    ES_NO_DELETE_RULE_ID,
    check_es_no_delete,
)
from detectors.es_empty_ifdef import (
    ES_EMPTY_IFDEF_MESSAGE,
    ES_EMPTY_IFDEF_RULE_ID,
    ES_EMPTY_IFDEF_STRAY_ENDIF_MESSAGE,
    ES_EMPTY_IFDEF_UNSUPPORTED_MESSAGE,
    ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
    ES_EMPTY_IFDEF_UNTERMINATED_MESSAGE,
    build_es_empty_ifdef_stray_endif_warning,
    build_es_empty_ifdef_unsupported_warning,
    build_es_empty_ifdef_unterminated_warning,
    check_es_empty_ifdef,
)
from detectors.es_ctx_read import (
    ES_CTX_READ_FAIL_MESSAGE,
    ES_CTX_READ_RULE_ID,
    ES_CTX_READ_UNSUPPORTED_MESSAGE,
    ES_CTX_READ_UNSUPPORTED_RULE_ID,
    ES_CTX_READ_WARN_MESSAGE,
    bool_local_is_checked_within_window,
    build_es_ctx_read_finding,
    build_es_ctx_read_unsupported_warning,
    check_es_ctx_read_unchecked,
    compile_ctx_read_bool_local_re,
    compile_ctx_read_inline_negated_re,
    compile_ctx_read_inline_positive_re,
    compile_ctx_read_re,
    ctx_read_has_supported_check,
    extract_if_condition,
    find_bool_local_unsupported_reason,
    find_ctx_read_unsupported_reason,
    if_body_has_statement,
    line_has_combined_ctx_read_condition,
    line_has_statement_content,
)
from detectors.es_syncvar import (
    ES_SYNCVAR_ALT_GUARD_UNSUPPORTED_MESSAGE,
    ES_SYNCVAR_CLASS_CANDIDATE_RE,
    ES_SYNCVAR_CLASS_HEADER_NEXT_LINE_RE,
    ES_SYNCVAR_CLASS_HEADER_RE,
    ES_SYNCVAR_CLASS_UNKNOWN_MESSAGE,
    ES_SYNCVAR_CLASS_UNKNOWN_RULE_ID,
    ES_SYNCVAR_IFDEF_BRANCH_UNSUPPORTED_MESSAGE,
    ES_SYNCVAR_METHOD_UNPARSED_UNSUPPORTED_MESSAGE,
    ES_SYNCVAR_REGISTER_CALL_RE,
    ES_SYNCVAR_REGISTER_OUTSIDE_CTOR_MESSAGE,
    ES_SYNCVAR_REGISTER_RE,
    ES_SYNCVAR_RULE_ID,
    ES_SYNCVAR_SET_DIRTY_RE,
    ES_SYNCVAR_UNSUPPORTED_RULE_ID,
    ES_SYNCVAR_WRITE_NO_DIRTY_MESSAGE,
    ES_SYNCVAR_WRITE_NO_IFDEF_MESSAGE,
    build_es_syncvar_class_unknown_warning,
    build_es_syncvar_error,
    build_es_syncvar_unsupported_warning,
    check_es_syncvar_contract,
    compile_syncvar_assignment_re,
    find_es_syncvar_classes,
    find_es_syncvar_registers,
    find_unknown_class_brace_line,
    method_is_syncvar_registration_target,
    range_contains_register,
    syncvar_assignment_has_set_dirty,
    syncvar_register_match_is_code,
    unique_in_order,
)
from detectors.es_int_min_compare import (
    ES_INT_MIN_COMPARE_MESSAGE,
    ES_INT_MIN_COMPARE_RE,
    ES_INT_MIN_COMPARE_RULE_ID,
    check_es_int_min_compare,
)
from detectors.es_gettype_exact_match import (
    ES_GETTYPE_EXACT_MATCH_MESSAGE,
    ES_GETTYPE_EXACT_MATCH_RE,
    ES_GETTYPE_EXACT_MATCH_RULE_ID,
    check_es_gettype_exact_match,
)
from detectors.es_layout_path_pboprefix import (
    ES_LAYOUT_PATH_PBOPREFIX_RULE_ID,
    check_es_layout_path_pboprefix,
    parse_pboprefix,
)
from detectors.es_processdirectdamage_dt_alias import (
    ES_DT_ALIAS_RULE_ID,
    check_es_dt_alias,
)
from detectors.es_local_var_redeclare import (
    ES_LOCAL_VAR_REDECLARE_RULE_ID,
    check_es_local_var_redeclare,
)
from detectors.es_member_redeclare_base import (
    ES_MEMBER_REDECLARE_BASE_RULE_ID,
    check_es_member_redeclare_base,
)
from detectors.es_override_param_name_mismatch import (
    ES_OVERRIDE_PARAM_NAME_MISMATCH_RULE_ID,
    check_es_override_param_name_mismatch,
)
from detectors.es_config_nested_override import (
    ES_CONFIG_NESTED_OVERRIDE_RULE_ID,
    check_es_config_nested_override,
)
from detectors.es_config_inputs_xml import (
    ES_INPUTS_XML_NOT_REGISTERED_RULE_ID,
    check_es_inputs_xml_registered,
    check_es_inputs_xml_root,
    detect_inputs_xml,
)
from detectors.es_config_attachments_append import (
    ES_ATTACHMENTS_APPEND_CROSSPBO_RULE_ID,
    check_es_attachments_compound_append,
)
from detectors.es_ref_autoptr_combined import (
    ES_REF_AUTOPTR_COMBINED_RULE_ID,
    check_es_ref_autoptr_combined,
)
from detectors.pdrive_path import (
    PDRIVE_PATH_CONFIG_RULE_ID,
    PDRIVE_PATH_RVMAT_RULE_ID,
    check_pdrive_path,
)
from detectors.es_layout_file_missing import (
    ES_LAYOUT_FILE_MISSING_RULE_ID,
    check_es_layout_file_missing,
)
from detectors.es_method_name_collides_vanilla_class import (
    ES_METHOD_NAME_COLLIDES_VANILLA_CLASS_RULE_ID,
    check_es_method_name_collides_vanilla_class,
)
from detectors.layout_xml_format import check_layout_xml_format
from detectors.es_onmouseleave_param_count import (
    ES_ONMOUSELEAVE_PARAM_COUNT_RULE_ID,
    check_es_onmouseleave_param_count,
)
from detectors.es_registerrecipes_typo import (
    ES_REGISTERRECIPES_TYPO_RULE_ID,
    check_es_registerrecipes_typo,
)
from detectors.es_nonexistent_method import (
    ES_NONEXISTENT_METHOD_RULE_ID,
    check_es_nonexistent_method,
)
from detectors.es_respawn_equip_onclientrespawn import (
    ES_RESPAWN_EQUIP_RULE_ID,
    check_es_respawn_equip_onclientrespawn,
)
from detectors.es_c_style_cast import (
    ES_C_STYLE_CAST_RULE_ID,
    check_es_c_style_cast,
)
from detectors.es_string_plus_bool import (
    ES_STRING_PLUS_BOOL_RULE_ID,
    check_es_string_plus_bool,
)
from detectors.es_override_of_platform_gated_method import (
    ES_OVERRIDE_OF_PLATFORM_GATED_METHOD_RULE_ID,
    check_es_override_of_platform_gated_method,
)


def build_result(addon_root, errors, warnings, files_scanned, elapsed_ms):
    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "addon_root": str(addon_root),
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "info": {
            "files_scanned": files_scanned,
            "elapsed_ms": elapsed_ms,
        },
    }


def exit_code_for_status(status):
    if status == "FAIL":
        return 1
    if status == "WARN":
        return 2
    return 0


def validate_addon(addon_root):
    start = time.perf_counter()
    received_addon_root = pathlib.Path(addon_root)
    addon_root = pathlib.Path(addon_root).resolve()
    relative_root = addon_root if addon_root.is_dir() else addon_root.parent
    errors = []
    warnings = []

    if not addon_root.exists():
        errors.append(build_input_not_found_error(received_addon_root))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return build_result(addon_root, errors, warnings, 0, elapsed_ms)

    files = discover_files(addon_root)
    pboprefix = parse_pboprefix(addon_root)
    inputs_xml_present = detect_inputs_xml(relative_root)
    errors.extend(check_es_inputs_xml_root(relative_root))

    for path in files:
        suffix = path.suffix.lower()
        rel_path = relative_path(path, relative_root)
        source, encoding_error = read_text_utf8_or_error(path, rel_path)
        if encoding_error:
            errors.append(encoding_error)
            continue

        if suffix == ".c":
            stripped, stripper_warnings = strip_enforce_comments_and_strings(
                source, rel_path
            )
            warnings.extend(stripper_warnings)
            errors.extend(check_es_no_delete(stripped, rel_path))
            empty_ifdef_errors, empty_ifdef_warnings = check_es_empty_ifdef(
                stripped, rel_path
            )
            errors.extend(empty_ifdef_errors)
            warnings.extend(empty_ifdef_warnings)
            ctx_read_errors, ctx_read_warnings = check_es_ctx_read_unchecked(
                stripped, rel_path
            )
            errors.extend(ctx_read_errors)
            warnings.extend(ctx_read_warnings)
            syncvar_errors, syncvar_warnings = check_es_syncvar_contract(
                source, stripped, rel_path
            )
            errors.extend(syncvar_errors)
            warnings.extend(syncvar_warnings)
            warnings.extend(check_es_int_min_compare(stripped, rel_path))
            warnings.extend(check_es_gettype_exact_match(stripped, rel_path))
            warnings.extend(check_es_ref_autoptr_combined(stripped, rel_path))
            warnings.extend(
                check_es_onmouseleave_param_count(stripped, rel_path)
            )
            errors.extend(check_es_dt_alias(stripped, rel_path))
            errors.extend(check_es_local_var_redeclare(stripped, rel_path))
            errors.extend(check_es_member_redeclare_base(stripped, rel_path))
            errors.extend(check_es_override_param_name_mismatch(stripped, rel_path))
            errors.extend(
                check_es_layout_path_pboprefix(source, rel_path, pboprefix)
            )
            errors.extend(
                check_es_layout_file_missing(
                    source, rel_path, pboprefix, relative_root
                )
            )
            errors.extend(
                check_es_method_name_collides_vanilla_class(stripped, rel_path)
            )
            registerrecipes_errors, registerrecipes_warnings = (
                check_es_registerrecipes_typo(stripped, rel_path)
            )
            errors.extend(registerrecipes_errors)
            warnings.extend(registerrecipes_warnings)
            errors.extend(check_es_nonexistent_method(stripped, rel_path))
            warnings.extend(
                check_es_respawn_equip_onclientrespawn(stripped, rel_path)
            )
            errors.extend(check_es_c_style_cast(stripped, rel_path))
            errors.extend(check_es_string_plus_bool(source, rel_path))
            errors.extend(
                check_es_override_of_platform_gated_method(stripped, rel_path)
            )
        elif suffix == ".rvmat":
            errors.extend(check_rvmat_normalmapmacro(source, rel_path))
            warnings.extend(
                check_pdrive_path(source, rel_path, PDRIVE_PATH_RVMAT_RULE_ID)
            )
        elif suffix == ".layout":
            errors.extend(check_layout_xml_format(source, rel_path))
        elif suffix == ".cpp" and path.name.lower() == "config.cpp":
            config_stripped, config_strip_warnings = (
                strip_enforce_comments_and_strings(source, rel_path)
            )
            warnings.extend(config_strip_warnings)
            errors.extend(
                check_es_config_nested_override(config_stripped, rel_path)
            )
            errors.extend(
                check_es_inputs_xml_registered(
                    config_stripped, rel_path, inputs_xml_present
                )
            )
            warnings.extend(
                check_es_attachments_compound_append(config_stripped, rel_path)
            )
            warnings.extend(
                check_pdrive_path(source, rel_path, PDRIVE_PATH_CONFIG_RULE_ID)
            )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return build_result(addon_root, errors, warnings, len(files), elapsed_ms)


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("addon_root")
    args = parser.parse_args(argv)

    result = validate_addon(args.addon_root)
    return exit_code_for_status(result["status"]), result


def main(argv=None):
    exit_code, result = run(argv)
    print(json.dumps(result, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
