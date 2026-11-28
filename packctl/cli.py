from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api_index import build_index, query_index
from .builder import build_archive
from .common import exit_code_for, finding, make_report, write_json
from .evals import run_eval_case
from .live_evals import run_live_eval_case
from .install import InstallError, install, write_bundle_zip
from .gate import TEST_FOLDER_TREES, run_gate, run_test_folders
from .promotion import apply_promotion, check_promotion, recover_promotion
from .validation import validate_repo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="packctl")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("--root", required=True, type=Path)
    validate.add_argument("--report", required=True, type=Path)

    build = commands.add_parser("build")
    build.add_argument("--root", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--report", required=True, type=Path)

    install_parser = commands.add_parser(
        "install",
        help="install the pack as one routed skill: <target>/<name>/SKILL.md plus sub-skills",
    )
    install_parser.add_argument("--root", type=Path, default=Path("."))
    install_parser.add_argument("--target", required=True, type=Path)
    install_parser.add_argument("--name", default="dayz")
    install_parser.add_argument("--force", action="store_true")
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.add_argument(
        "--link",
        action="store_true",
        help="developer mode: symlink _shared/ and dayz-*/ into this repo instead of copying",
    )

    bundle = commands.add_parser(
        "bundle",
        help="write a reproducible dayz-skill ZIP (one top-level dayz/ folder) for unzip-install",
    )
    bundle.add_argument("--root", type=Path, default=Path("."))
    bundle.add_argument("--output", required=True, type=Path)
    bundle.add_argument("--name", default="dayz")

    gate = commands.add_parser("gate")
    gate.add_argument("--root", required=True, type=Path)
    gate.add_argument("--report-dir", required=True, type=Path)

    test_folders = commands.add_parser("test-folders")
    test_folders.add_argument("--root", required=True, type=Path)
    test_folders.add_argument(
        "--tree",
        action="append",
        required=True,
        choices=TEST_FOLDER_TREES,
    )
    test_folders.add_argument("--report-dir", required=True, type=Path)

    api = commands.add_parser("api-index")
    api_commands = api.add_subparsers(dest="api_command", required=True)
    api_build = api_commands.add_parser("build")
    api_build.add_argument("--root", required=True, type=Path)
    api_build.add_argument("--include", action="append", required=True)
    api_build.add_argument("--output-dir", required=True, type=Path)
    api_build.add_argument("--source-id", required=True)
    api_build.add_argument("--source-revision", required=True)
    api_build.add_argument("--dayz-build", required=True)
    api_build.add_argument("--report", required=True, type=Path)

    api_query = api_commands.add_parser("query")
    api_query.add_argument("--index-dir", required=True, type=Path)
    api_query.add_argument("--symbol", required=True)
    api_query.add_argument("--expected-build")
    api_query.add_argument("--expected-schema", type=int, default=1)
    api_query.add_argument("--report", required=True, type=Path)

    eval_parser = commands.add_parser("eval")
    eval_commands = eval_parser.add_subparsers(dest="eval_command", required=True)
    eval_run = eval_commands.add_parser("run")
    eval_run.add_argument("--case", required=True)
    eval_run.add_argument("--variant", required=True)
    eval_run.add_argument("--out", required=True, type=Path)
    eval_live = eval_commands.add_parser("live")
    eval_live.add_argument("--root", required=True, type=Path)
    eval_live.add_argument("--case", required=True, type=Path)
    eval_live.add_argument("--runner", required=True, type=Path)
    eval_live.add_argument("--report", required=True, type=Path)

    promote = commands.add_parser("promote")
    action = promote.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--apply", action="store_true")
    action.add_argument("--bootstrap", action="store_true")
    action.add_argument("--recover", action="store_true")
    promote.add_argument("--root", type=Path, default=Path("."))
    promote.add_argument(
        "--promotion-map",
        type=Path,
        default=Path("promotions/promotion-map.json"),
    )
    promote.add_argument(
        "--local-targets",
        type=Path,
        default=Path("promotions/local-targets.json"),
    )
    promote.add_argument("--plan", type=Path)
    promote.add_argument("--transaction-root", type=Path)
    return parser


def _resolve_api_source(root: Path, source_id: str) -> Path:
    source_map = __import__("json").loads(
        (root / "sources/source-map.json").read_text(encoding="utf-8")
    )
    source = next(
        item for item in source_map["sources"] if item["source_id"] == source_id
    )
    local_root_id = source["local_root_id"]
    local_roots = __import__("json").loads(
        (root / "sources/local-roots.json").read_text(encoding="utf-8")
    )
    config = local_roots["roots"][local_root_id]
    if "path" in config:
        return Path(config["path"])
    environment_name = config["path_env"]
    value = __import__("os").environ.get(environment_name)
    if not value:
        raise ValueError(f"Missing environment root: {environment_name}")
    return Path(value)


def _run_install(args: argparse.Namespace) -> int:
    try:
        result = install(
            args.root,
            args.target,
            name=args.name,
            force=args.force,
            dry_run=args.dry_run,
            link=args.link,
        )
    except FileExistsError as error:
        sys.stderr.write(f"packctl install: refused: {error}\n")
        return 1
    except InstallError as error:
        sys.stderr.write(f"packctl install: {error}\n")
        return 1
    verb = "Would install" if args.dry_run else "Installed"
    sys.stdout.write(
        f"{verb} {len(result['skills'])} skills + _shared into {result['destination']}"
        f" (router {result['router_bytes']} bytes, replaced: {result['replaced']},"
        f" mode: {result['mode']})\n"
    )
    if args.link and not args.dry_run:
        sys.stdout.write(
            "Linked to this checkout: skill edits show up at once, but the router SKILL.md is"
            " generated; rerun `packctl install --link` after changing any skill description.\n"
        )
    leftovers = result["leftovers"]
    if leftovers:
        sys.stderr.write(
            f"warning: {args.target} still holds folders from the old install shape,"
            " which Claude Code lists as separate skills next to the router:\n"
        )
        for item in leftovers:
            sys.stderr.write(f"  {Path(args.target) / item}\n")
        sys.stderr.write("Remove them yourself if you no longer need them; packctl never deletes them.\n")
    return 0


def _run_bundle(args: argparse.Namespace) -> int:
    try:
        result = write_bundle_zip(args.root, args.output, name=args.name)
    except InstallError as error:
        sys.stderr.write(f"packctl bundle: {error}\n")
        return 1
    sys.stdout.write(
        f"Wrote {result['output']} ({result['members']} files, {len(result['skills'])} skills)\n"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_repo(args.root)
            report_path = args.report
        elif args.command == "build":
            report = build_archive(args.root, args.output)
            report_path = args.report
        elif args.command == "install":
            return _run_install(args)
        elif args.command == "bundle":
            return _run_bundle(args)
        elif args.command == "gate":
            report = run_gate(args.root, args.report_dir)
            return exit_code_for(report)
        elif args.command == "test-folders":
            report = run_test_folders(args.root, args.report_dir, args.tree)
            sys.stdout.write(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
                + "\n"
            )
            return exit_code_for(report)
        elif args.command == "api-index" and args.api_command == "build":
            source_root = _resolve_api_source(args.root.resolve(), args.source_id)
            report = build_index(
                source_root=source_root,
                includes=args.include,
                output_dir=args.output_dir,
                source_id=args.source_id,
                source_revision=args.source_revision,
                dayz_build=args.dayz_build,
            )
            report_path = args.report
        elif args.command == "api-index" and args.api_command == "query":
            report = query_index(
                args.index_dir,
                args.symbol,
                expected_build=args.expected_build,
                expected_schema=args.expected_schema,
            )
            report_path = args.report
        elif args.command == "eval" and args.eval_command == "live":
            report = run_live_eval_case(
                args.root,
                args.case,
                args.runner,
                args.report,
            )
            return exit_code_for(report)
        elif args.command == "eval" and args.eval_command == "run":
            root = Path.cwd()
            case_path = Path(args.case)
            if not case_path.is_file():
                case_path = root / "evals" / "cases" / f"{args.case}.json"
            report = run_eval_case(case_path, args.variant, args.out)
            report_path = args.out / "report.json"
        elif args.command == "promote" and (args.check or args.bootstrap):
            if args.bootstrap and args.plan is None:
                parser.error("promote --bootstrap requires --plan")
            report = check_promotion(
                args.root,
                args.promotion_map,
                args.local_targets,
                args.plan,
                bootstrap=bool(args.bootstrap),
            )
            sys.stdout.write(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
                + "\n"
            )
            if args.plan is None:
                return exit_code_for(report)
            report_path = args.plan.with_suffix(".check-report.json")
        elif args.command == "promote" and args.apply:
            if args.plan is None:
                parser.error("promote --apply requires --plan")
            report = apply_promotion(args.plan)
            report_path = args.plan.with_suffix(".apply-report.json")
        elif args.command == "promote" and args.recover:
            if args.transaction_root is None:
                parser.error(
                    "promote --recover requires --transaction-root"
                )
            report = recover_promotion(args.transaction_root)
            sys.stdout.write(
                json.dumps(report, ensure_ascii=False, sort_keys=True)
                + "\n"
            )
            return exit_code_for(report)
        else:
            parser.error("unsupported command")
            return 2
        write_json(Path(report_path), report)
        return exit_code_for(report)
    except Exception as error:
        root = Path(getattr(args, "root", ".")).resolve()
        report = make_report(
            str(getattr(args, "command", "unknown")),
            root,
            [
                finding(
                    "PACKCTL-INTERNAL-ERROR",
                    path="",
                    line=0,
                    message="packctl encountered an internal error.",
                    evidence=type(error).__name__,
                )
            ],
        )
        report_path = getattr(args, "report", None)
        if report_path is not None:
            write_json(Path(report_path), report)
        else:
            sys.stderr.write(json.dumps(report, ensure_ascii=False) + "\n")
        return 2
