from __future__ import annotations

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import List

from .helpers import BranchProtectionRule, BranchProtectionData
from ..helpers import Criteria


# define the criteria we care about. Identify each critera with a string that will
# appear in the results.
required_criteria = [
    Criteria("SOGH001", "rules", "active rules"),
    Criteria("SOGH001b", "admins", "admins restricted"),
]
optional_criteria = [
    Criteria("SOGH001c", "commiters", "allowed commiters configured"),
    # "commit signing",  # may not be knowable
]
warning_criteria = [
    Criteria("SOGH001d", "conflicts", "Conflict in Protection Rules"),
]


def meets_criteria(protections: List[BranchProtectionRule], criteria: Criteria) -> bool:
    met = True
    # ugly implementation for now
    if criteria.slug == "rules":
        met = len(protections) > 0
    elif criteria.slug == "admins":
        met = all(r.is_admin_enforced for r in protections)
    elif criteria.slug == "commiters":
        met = all(r.push_actor_count > 0 for r in protections)
    elif criteria.slug == "conflicts":
        met = all(r.rule_conflict_count == 0 for r in protections)
    else:
        met = False
    return met


def validate_branch_protections(
    data: BranchProtectionData, criteria: Criteria,
) -> List[str]:
    """Validate the protections."""

    results = []

    # if the production branch is not specified, use the default name
    branch = data.key.branch_str

    # Multiple steps to validate - first, is the branch even covered
    active_rules = data.protections

    if not active_rules:
        # results.append(
        assert False, f"ERROR:SOGH001:{data.key!s} has no branch protection"
        # )
    else:
        # see if at least one rule matches specified criteria
        message = f"ERROR:SOGH001:{data.key!s} has no {criteria} rule"
        return meets_criteria(active_rules, criteria), message
        # vscode correctly tells me that all code below here is unreachable
        # see if at least one rule matches each criteria
        for criteria in required_criteria:
            if not meets_criteria(active_rules, criteria):
                results.append(
                    f"ERROR: no {criteria} for branch '{data.name_with_owner}:{branch}' (required)"
                )
        for criteria in optional_criteria:
            if not meets_criteria(active_rules, criteria):
                results.append(
                    f"FYI: no {criteria} for branch '{data.name_with_owner}:{branch}' (optional)"
                )

    # vscode correctly tells me that all code below here is unreachable
    # regardless of match, we'll also warn on conflicting rules
    for criteria in warning_criteria:
        if not meets_criteria(active_rules, criteria):
            results.append(
                f"WARNING: {criteria} for branch '{data.name_with_owner}:{branch}'"
            )

    return results
