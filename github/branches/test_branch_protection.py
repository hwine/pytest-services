from __future__ import annotations

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from github.branches.helpers import BranchProtectionData
from github.branches.validate_compliance import Criteria

from .client import repos_to_check
from . import validate_compliance


import pytest


@pytest.mark.parametrize(
    "repo_to_check", repos_to_check(), ids=BranchProtectionData.idfn
)
@pytest.mark.parametrize(
    "criteria", validate_compliance.required_criteria, ids=Criteria.idfn
)
def test_required_protections(
    repo_to_check: BranchProtectionData, criteria: Criteria
) -> None:
    rules = repo_to_check.protections

    if not repo_to_check.org_id:
        raise ValueError(f"no v4 org id for {repo_to_check!s}")

    if not rules:
        assert False, f"ERROR:SOGH001:{repo_to_check!s} has no branch protection"
    else:
        met, message = validate_compliance.validate_branch_protections(
            repo_to_check, criteria
        )
        assert met, message
