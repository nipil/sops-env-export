#!/usr/bin/env python3

import json
import logging
import os
import os.path
import platform
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import TypeAlias, Generator

DEFAULT_BASE = os.environ.get('DEVCONTAINER_WORKSPACEFOLDER', '/')

Environment: TypeAlias = dict[str, str]


class AppError(Exception):
    pass


def get_current_environment() -> Environment:
    return dict(os.environ)


def export_environment_item(key, value) -> str:
    pf = platform.system()
    if pf == 'Windows':
        single_quote_escaped_key = key.replace(r"'", r"''")
        single_quote_escaped_value = value.replace(r"'", r"''")
        return f"[Environment]::SetEnvironmentVariable('{single_quote_escaped_key}', '{single_quote_escaped_value}')"
    elif pf == 'Linux':
        single_quote_escaped_value = value.replace(r"'", r"'\''")
        return f"export {key}='{single_quote_escaped_value}'"
    else:
        raise AppError(f'Unsupported platform: {pf}')


def export_environment(env: Environment) -> Generator[str, None, None]:
    for key, value in env.items():
        yield export_environment_item(key, value)


def get_self_command() -> str:
    me = sys.argv[0]
    pf = platform.system()
    if pf == 'Windows':
        return f'python3.exe {me}'
    elif pf == 'Linux':
        return f'python3 {me}'
    else:
        raise AppError(f'Unsupported platform: {pf}')


def get_sops_environment(entry: Path) -> Environment:
    """The command exec-env executes, must be a single string, and NOT an array"""
    logging.debug(f'Getting environment from : {entry}')
    cmd = ['sops', 'exec-env', str(entry), get_self_command()]
    logging.debug(f'SOPS command: {cmd}')
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise AppError(f'Calling SOPS failed: {result.stderr}')
    env = json.loads(result.stdout)
    logging.debug(f'SOPS environment: {env}')
    return env


def get_environment_diff(original: Environment, modified: Environment) -> Environment:
    original_env = set(original.items())
    patched_env = set(modified.items())
    diff_env = dict(patched_env - original_env)
    logging.debug(f'Environment differences: {diff_env}')
    return diff_env


class SopsEnvExport:

    def __init__(self, entries: list[Path], *, indent: int | None) -> None:
        self.entries = entries
        self.indent = indent

    def print_json_env(self, env: Environment) -> None:
        print(json.dumps(env, indent=self.indent))

    def get_merged_files_environment(self) -> Environment:
        original_env = get_current_environment()
        logging.debug(f'Original environment: {original_env}')
        patched_env = Environment()
        for entry in self.entries:
            if entry.is_dir():
                logging.warning(f'Skipping SOPS processing of directory: {entry}')
                continue
            file_env = get_sops_environment(entry)
            diff_env = get_environment_diff(original_env, file_env)
            patched_env |= diff_env
            logging.debug(f'Patched environment: {patched_env}')
        logging.info(f'Final environment patch: {patched_env}')
        return patched_env

    def run_print_env(self):
        env = get_current_environment()
        logging.debug(f'Current environment: {env}')
        self.print_json_env(env)

    def run_merge_files_env(self):
        if self.indent is not None:
            logging.warning('Indent option has no effect when SOPS files are provided')
        final_env = self.get_merged_files_environment()
        for export_statement in export_environment(final_env):
            print(export_statement)

    def run(self) -> None:
        if len(self.entries) == 0:
            self.run_print_env()
        else:
            self.run_merge_files_env()


def run(args: Namespace) -> None:
    see = SopsEnvExport(args.sopsfile, indent=args.indent)
    see.run()


def try_run(args: Namespace) -> None:
    try:
        run(args)
    except AppError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)


def main(argv: list[str] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    parser = ArgumentParser()
    parser.add_argument('--log-level', default='warning', choices=['debug', 'info', 'warning', 'error', 'critical'])
    parser.add_argument('--stack-trace', action='store_true')
    parser.add_argument('--indent', type=int)
    parser.add_argument('sopsfile', nargs='*', type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(format='%(levelname)s: %(message)s', level=getattr(logging, args.log_level.upper()))
    logging.debug(f'Args: {args}')
    if args.stack_trace:
        run(args)
    else:
        try_run(args)


if __name__ == '__main__':
    main()
