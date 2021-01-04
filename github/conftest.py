#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Fixtures to fetch data for the various GitHub branch checks

# TODO: add doctests

# Implementation decisions:
# - defer adding rate limiting support until needed: https://github.com/mozilla/frost/issues/426


import logging

logger = logging.getLogger(__name__)
# Data to move to config
DEFAULT_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"


# Configure Frost results extraction

from .helpers import Criteria
from conftest import METADATA_KEYS

METADATA_KEYS.update(Criteria.metadata_to_log())
