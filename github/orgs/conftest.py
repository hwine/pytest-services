#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# PyTest support for the various GitHub organization checks

# Implementation decisions:
# - defer adding rate limiting support until needed: https://github.com/mozilla/frost/issues/426

from github.orgs.validate_compliance import Criteria
from github.orgs.helpers import OrgData


from conftest import METADATA_KEYS  # noqa: I900

METADATA_KEYS.update(OrgData.metadata_to_log())
METADATA_KEYS.update(Criteria.metadata_to_log())
