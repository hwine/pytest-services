#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import List

from .retrieve_github_data import OrgInfo

# define the criteria we care about. Identify each critera with a string that will
# appear in the results.
required_criteria = [
    "two factor required",
]
optional_criteria = [
    # "commit signing",  # may not be knowable
]
warning_criteria = []


def meets_criteria(org_info: OrgInfo, criteria: str) -> bool:
    met = True
    # ugly implementation for now
    if criteria == "two factor required":
        met = org_info.requires_two_factor_authentication
    else:
        # raising assert works best when called from pytest, as we won't
        # _always_ be called from pytest.
        assert False, f"ERROR: no support for '{criteria}'"
    return met


def validate_org_info(data: OrgInfo, criteria: str) -> List[str]:
    """
        Validate the protections

    """

    results = []

    for criteria in required_criteria:
        if not meets_criteria(data, criteria):
            results.append(f"ERROR: no {criteria} for org '{data.name}' (required)")
    for criteria in optional_criteria:
        if not meets_criteria(data, criteria):
            results.append(f"FYI: no {criteria} for org '{data.name}' (optional)")

    # regardless of match, we'll also warn on conflicting rules
    for criteria in warning_criteria:
        if not meets_criteria(data, criteria):
            results.append(f"WARNING: no {criteria} for org '{data.name}' (required)")

    return len(results) == 0, results
