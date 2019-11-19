import mock

import pytest

from uaclient.cli import (
    action_attach_premium,
    attach_premium_parser,
    get_parser,
)
from uaclient.exceptions import AlreadyAttachedError, NonRootUserError
from uaclient.testing.fakes import FakeConfig
from uaclient.tests.test_cli_attach import BASIC_MACHINE_TOKEN

M_PATH = "uaclient.cli."


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_attach_premium(mock.MagicMock(), cfg)


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAttach:
    def test_already_attached(self, _m_getuid, capsys):
        """Check that an attached machine raises AlreadyAttachedError."""
        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)

        with pytest.raises(AlreadyAttachedError):
            action_attach_premium(mock.MagicMock(), cfg)

    @mock.patch(M_PATH + "contract.request_updated_contract")
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_premium_aws_contract_token"
    )
    @mock.patch("uaclient.clouds.identity.cloud_instance_factory")
    @mock.patch("uaclient.clouds.identity.get_cloud_type", return_value="aws")
    @mock.patch(M_PATH + "action_status")
    def test_happy_path_on_aws(
        self,
        action_status,
        get_cloud_type,
        cloud_instance_factory,
        contract_aws_token,
        request_updated_contract,
        _m_getuid,
    ):
        """A mock-heavy test for the happy path on Premium AWS without args"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        token = "contract-token"
        args = mock.MagicMock(token=token)
        cfg = FakeConfig()

        def fake_aws_contract_token(contract_token):
            return {"contractToken": "myPKCS7-token"}

        contract_aws_token.side_effect = fake_aws_contract_token

        def fake_request_updated_contract(cfg, contract_token, allow_enable):
            cfg.write_cache("machine-token", BASIC_MACHINE_TOKEN)
            return BASIC_MACHINE_TOKEN

        request_updated_contract.side_effect = fake_request_updated_contract

        def fake_instance_factory():
            m_instance = mock.Mock()
            m_instance.identity_doc = "mypkcs7"
            return m_instance

        cloud_instance_factory.side_effect = fake_instance_factory
        ret = action_attach_premium(args, cfg)

        assert 0 == ret
        assert 1 == get_cloud_type.call_count
        assert 1 == action_status.call_count
        assert [mock.call("mypkcs7")] == contract_aws_token.call_args_list
        expected_calls = [mock.call(cfg, "myPKCS7-token", allow_enable=True)]
        assert expected_calls == request_updated_contract.call_args_list


class TestParser:
    def test_attach_premium_parser_updates_parser_config(self):
        """Update the parser configuration for 'attach-premium'."""
        m_parser = attach_premium_parser(mock.Mock())
        assert "ua attach-premium [flags]" == m_parser.usage
        assert "attach-premium" == m_parser.prog
        assert "Flags" == m_parser._optionals.title

        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "attach-premium"]):
            args = full_parser.parse_args()
        assert "attach-premium" == args.command
        assert "action_attach_premium" == args.action.__name__