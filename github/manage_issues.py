#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Perform actions based on frost results."""

import argparse
import json
from dataclasses import dataclass
import logging
from pprint import pprint
from typing import List, Optional, Sequence, Tuple


logger = logging.getLogger(__name__)

_epilog = ""


@dataclass
class Action:
    final_status: str = ""  # after frost exemption processing
    base_status: str = ""  # native pytest status
    owner: str = ""
    repo: str = ""
    branch: str = ""
    standard: str = ""
    summary: str = ""
    messages: Optional[List[str]] = None


def parse_action_string(name: str) -> Optional[Sequence[str]]:
    """comment."""
    matches = SPEC_DECODER_RE.match(name)
    return matches.groups() if matches else None


def infer_resource_type(metadata: dict) -> str:
    """infer object type.

    This relies on the file system structure of the tests We currently
    assume it is:     "github/" resource_type "/.*"
    """
    prefix = "github/"
    start = path.find(prefix) + len(prefix)
    end = path.find("/", start)
    resource_type = path[start:end]
    return resource_type


def create_branch_action(action_spec: dict) -> Action:
    """Parse pytest info into information needed to open an issue against a
    specific branch."""

    # most information comes from the (parametrized) name of the test
    test_info = action_spec["name"]
    *_, standard, test_name, param_id = parse_action_string(test_info)
    owner, repo = param_id.split("/")

    # details for branches come from the assertion text
    branch_details = action_spec["call"]["longrepr"]
    errors = []
    branch = "BoGuS"
    for item in ASSERT_DECODER_RE.finditer(branch_details):
        info = item.groupdict()["info"]
        # further parse info
        branch = "BoGuS"
        matches = BRANCH_INFO_DECODER_RE.match(info)
        if matches:
            owner, repo, branch = matches.groups()
        errors.append(
            f"Branch {branch} of {owner}/{repo} failed {standard} {test_name}"
        )

    summary = f"{len(errors)} for {owner}/{repo}:{branch}"
    final_status, base_status = get_status(action_spec)
    action = Action(
        final_status=final_status,
        base_status=base_status,
        owner=owner,
        repo=repo,
        branch=branch,
        standard=standard,
        summary=summary,
        messages=errors,
    )
    return action


def get_status(action_spec: dict) -> Tuple[str, str]:
    final_status = action_spec["value"]
    base_status = action_spec["metadata"][0]["outcome"]
    return final_status, base_status


def create_org_action(action_spec: dict) -> Action:
    """Break out the org info from the json."""
    # TODO check for outcome of xfailed (means exemption no longer needed)
    # most information comes from the (parametrized) name of the test
    test_info = action_spec["name"]
    # path, method, standard, test_name, param_id = parse_action_string(test_info)
    md = action_spec["metadata"]
    org_full_name = md["org_name"]
    standard_number = md["standard_number"]
    test_name = action_spec["test_name"]
    summary = f"Org {org_full_name} failed {standard_number} {test_name}"
    final_status, base_status = get_status(action_spec)
    action = Action(
        final_status=final_status,
        base_status=base_status,
        owner=md["login"],
        # TODO add v4 id
        standard=standard_number,
        summary=summary,
    )
    return action


def create_action_spec(action_spec: dict) -> Action:
    # for now, just return Action -- later decode may involve inferring what to
    # do ("xpass" detection -- see GH-325)
    # full name is file_path::method[test_name-parametrize_id]
    name = action_spec["name"]
    # path, *_ = parse_action_string(name)
    test_object = action_spec["metadata"]["object"]
    # resource_type = infer_resource_type(action_spec["metadata"])
    if test_object == "org":
        action = create_org_action(action_spec)
    elif test_object == "branche":
        action = create_branch_action(action_spec)
    else:
        raise TypeError(f"unknown test object '{test_object}' from '{name}")

    return action


def _open_issue(action: Action) -> bool:
    """Report status via a GitHub issue.

    Used for actions which relate to a specific repository
    TODO support grouping actions for same main issue.
        i.e. SOGH001[abc] should all report under same issue

    Args:
        action (Action): Information about the type of problem

    Returns:
        bool: True if processed successfully
    """
    logger.info(
        f"GitHub issue regarding {action.standard} relating to {action.owner}/{action.repo}"
    )
    return True


def _alert_owners(action: Action) -> bool:
    """Contact org owners.

    Unsure how to do this - may be slack or email to secops. There is no good native way in GitHub.

    Args:
        action (Action): Information about the type of problem

    Returns:
        bool: True if processed successfully
    """
    logger.info(
        f"Contacting owners regarding {action.standard} relating to org {action.owner}."
    )
    return True


dispatch_table = {
    "SOGH001": _open_issue,
    "SOGH001b": _open_issue,
    "SOGH002": _open_issue,
    "SOGH003": _alert_owners,
}


def perform_action(action: Action) -> bool:
    """Initiate the appropriate action.

    Args:
        action (Action): All the data needed to perform the action

    Returns:
        bool: True if action completed successfully
    """
    if action.standard in dispatch_table:
        return dispatch_table[action.standard](action)
    else:
        logger.error(f"No action defined for standard '{action.standard}'")
        return False


def parse_args():
    # import argcomplete  # type: ignore
    parser = argparse.ArgumentParser(description=__doc__, epilog=_epilog)
    parser.add_argument("json_file", help="frost json output")
    # argcomplete.autocomplete(parser)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    args = parse_args()

    with open(args.json_file) as jf:
        frost_report = json.loads(jf.read())

    test_results = frost_report["results"]
    print(f"Processing {len(test_results)} test results")
    for result in test_results:
        if result["value"] == "passed":
            continue
        action = create_action_spec(result)
        # TODO integrate actual issue handling
        # print(action)
        perform_action(action)
