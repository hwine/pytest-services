# TODO: discover why/how the exemptions.py & regressions.py processess screw up
#       normal pytest operations.  All the fixtures below could/should be in
#       the heroku/conftest.py file, and no mark.parametrize would be needed on
#       the actual tests.
#
#       With the local conftest.py setup, the tests work, but the warnings are
#       quite noisy. :/  We're trading off (for the moment at least) test
#       readability for output readability.

import pytest

from conftest import heroku_client


@pytest.fixture(scope="session")
def raw_json_data():
    """
    """
    raw = heroku_client.get("all", [], {})
    return raw


@pytest.fixture(scope="session")
def users(raw_json_data):
    """
    Get the members for this organization/team

    Each dictionary is as described at
        https://devcenter.heroku.com/articles/platform-api-reference#team-member

    Returns: a list of member dictionaries
    """
    just_key = raw_json_data.extract_key(heroku_client.data_set_names.USER, [])
    members = list(*just_key.results)

    return members


# expose email as explicit parameter to make parametrized test names useful
@pytest.mark.parametrize(
    "email, account", [(x["email"], x) for x in users(raw_json_data())]
)
def test_mozilla_user(email, account):
    if account["federated"]:
        assert not email.startswith("heroku")
        assert email.endswith("@mozilla.com")
    elif account["two_factor_authentication"]:
        # may have @m.c if starts with "heroku-"
        if email.endswith("@mozilla.com"):
            assert email.startswith("heroku")
    else:
        assert not email
