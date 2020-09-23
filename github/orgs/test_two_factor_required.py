#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from typing import List

from github.orgs.validate_compliance import Criteria
from typing import Any, Optional

from .retrieve_github_data import get_all_org_data, OrgInfo
from . import validate_compliance

# from .conftest import orgs_to_check


import pytest

viewer_login: str = "<unqueried>"


def get_viewer(endpoint):
    from sgqlc.operation import Operation  # noqa: I900
    from github import github_schema as schema  # noqa: I900

    global viewer_login
    if viewer_login == "<unqueried>":
        op = Operation(schema.Query)

        org = op.viewer()
        org.login()
        d = endpoint(op)
        errors = d.get("errors")
        if errors:
            viewer_login = "<unknown>"
        else:
            viewer_login = (op + d).viewer.login

    return viewer_login


@pytest.mark.parametrize("org_info", get_all_org_data(), ids=OrgInfo.idfn)
@pytest.mark.parametrize(
    "criteria", validate_compliance.required_criteria, ids=Criteria.idfn
)
def test_require_2fa(
    # gql_connection: Any, org_to_check: str, criteria: validate_compliance.Criteria
    gql_connection: Any,
    org_info: List[str],
    criteria: validate_compliance.Criteria,
) -> None:
    # info = get_org_info(gql_connection, f"{org_to_check}")
    print(f"before call: {org_info}")
    if org_info:
        met, message = validate_compliance.validate_org_info(org_info, criteria)
        print(f"authed as {get_viewer(gql_connection)}")
        assert met, message
