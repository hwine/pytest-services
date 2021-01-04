#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# PyTest support for the various GitHub branch checks

# Implementation decisions:
# - defer adding rate limiting support until needed: https://github.com/mozilla/frost/issues/426

# from github.branches.validate_compliance import Criteria
from .helpers import BranchProtectionData

# from github.branches.retrieve_github_data import BranchOfInterest
from conftest import METADATA_KEYS


METADATA_KEYS.update(BranchProtectionData.metadata_to_log())

## New stuff to consider adding
# - module scope GitHubQuery automatic parameter
# - fixture for branches (proxy - real code in client.py)

if __name__ == "__main__":
    pass
