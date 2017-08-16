from testing import UbuntuAdvantageTest
from fakes import (
    SNAP_LIVEPATCH_NOT_INSTALLED,
    LIVEPATCH_ENABLED,
    LIVEPATCH_DISABLED)


class UbuntuAdvantageScriptTest(UbuntuAdvantageTest):

    def test_enable_disable_needs_root(self):
        """The script must be run as root for enable and disable actions."""
        self.make_fake_binary('id', command='echo 100')
        actions = ['enable-esm', 'disable-esm', 'enable-livepatch',
                   'disable-livepatch']
        for action in actions:
            # we don't need to pass a token for the enable actions since the
            # root check is before the parameter check
            process = self.script(action)
            self.assertEqual(2, process.returncode)
            self.assertIn('This command must be run as root', process.stderr)

    def test_usage(self):
        """Calling the script with no args prints out the usage."""
        process = self.script()
        self.assertEqual(1, process.returncode)
        self.assertIn('usage: ubuntu-advantage', process.stderr)

    def test_enable_esm(self):
        """The enable-esm option enables the ESM repository."""
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository enabled', process.stdout)
        expected = (
            'deb https://user:pass@esm.ubuntu.com/ubuntu precise main\n'
            '# deb-src https://user:pass@esm.ubuntu.com/ubuntu precise main\n')
        self.assertEqual(expected, self.repo_list.read_text())
        keyring_file = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        self.assertEqual('GPG key', keyring_file.read_text())
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_esm_install_apt_transport_https(self):
        """enable-esm installs apt-transport-https if needed."""
        self.apt_method_https.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_esm_install_apt_transport_https_fails(self):
        """Stderr is printed if apt-transport-https install fails."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_esm_install_ca_certificates(self):
        """enable-esm installs ca-certificates if needed."""
        self.ca_certificates.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency ca-certificates',
            process.stdout)

    def test_enable_esm_install_ca_certificates_fails(self):
        """Stderr is printed if ca-certificates install fails."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_esm_missing_token(self):
        """The token must be specified when using enable-esm."""
        process = self.script('enable-esm')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_esm_invalid_token(self):
        """The ESM token must be specified as "user:password"."""
        process = self.script('enable-esm', 'foo-bar')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_esm_only_supported_on_precise(self):
        """The enable-esm option fails if not on Precise."""
        self.make_fake_binary('lsb_release', command='echo xenial')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Extended Security Maintenance is not supported on xenial',
            process.stderr)

    def test_disable_esm(self):
        """The disable-esm option disables the ESM repository."""
        self.script('enable-esm', 'user:pass')
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository disabled', process.stdout)
        self.assertFalse(self.repo_list.exists())
        # the keyring file is removed
        keyring_file = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        self.assertFalse(keyring_file.exists())

    def test_disable_esm_disabled(self):
        """If the ESM repo is not enabled, disable-esm is a no-op."""
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository was not enabled', process.stdout)

    def test_disable_esm_only_supported_on_precise(self):
        """The disable-esm option fails if not on Precise."""
        self.make_fake_binary('lsb_release', command='echo xenial')
        process = self.script('disable-esm')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Extended Security Maintenance is not supported on xenial',
            process.stderr)

    def test_is_esm_enabled_true(self):
        """is-esm-enabled returns 0 if the repository is enabled."""
        self.make_fake_binary('apt-cache', command='echo esm.ubuntu.com')
        process = self.script('is-esm-enabled')
        self.assertEqual(0, process.returncode)

    def test_is_esm_enabled_false(self):
        """is-esm-enabled returns 1 if the repository is not enabled."""
        self.make_fake_binary('apt-cache')
        process = self.script('is-esm-enabled')
        self.assertEqual(1, process.returncode)

    def test_livepatch_supported_trusty_xenial_not_precise(self):
        """Livepatch is supported in trusty and xenial but not precise."""
        for release in ['trusty', 'xenial']:
            self.make_fake_binary(
                'lsb_release', command='echo {}'.format(release))
            process = self.script('enable-livepatch')
            # if we get a token error, that means we passed the ubuntu
            # release check.
            self.assertEqual(3, process.returncode)
            self.assertIn('Invalid or missing Livepatch token', process.stderr)
        # precise is not supported
        self.make_fake_binary('lsb_release', command='echo precise')
        process = self.script('enable-livepatch')
        self.assertEqual(4, process.returncode)
        self.assertIn('Sorry, but Canonical Livepatch is not supported on '
                      'precise', process.stderr)

    def test_enable_livepatch_missing_token(self):
        """The token must be specified when using enable-livepatch."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        process = self.script('enable-livepatch')
        self.assertEqual(3, process.returncode)
        self.assertIn('Invalid or missing Livepatch token', process.stderr)

    def test_enable_livepatch_invalid_token(self):
        """The Livepatch token must be specified as 32 hex chars."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        process = self.script('enable-livepatch', 'invalid:token')
        self.assertEqual(3, process.returncode)
        self.assertIn('Invalid or missing Livepatch token', process.stderr)

    def test_enable_livepatch_installs_snapd(self):
        """enable-livepatch installs snapd if needed."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.snapd.unlink()
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn('Installing missing dependency snapd', process.stdout)

    def test_enable_livepatch_installs_snap(self):
        """enable-livepatch installs the livepatch snap if needed."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary('snap', command=SNAP_LIVEPATCH_NOT_INSTALLED)
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing the canonical-livepatch snap', process.stdout)

    def test_is_livepatch_enabled_true(self):
        """is-livepatch-enabled returns 0 if the service is enabled."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_ENABLED)
        process = self.script('is-livepatch-enabled')
        self.assertEqual(0, process.returncode)

    def test_is_livepatch_enabled_false(self):
        """is-livepatch-enabled returns 1 if the service is not enabled."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        process = self.script('is-livepatch-enabled')
        self.assertEqual(1, process.returncode)

    def test_enable_livepatch_enabled(self):
        """enable-livepatch when it's already enabled is detected."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn('Livepatch already enabled.', process.stdout)

    def test_enable_livepatch(self):
        """enable-livepatch enables the livepatch service."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn('Successfully enabled device. Using machine-token:',
                      process.stdout)

    def test_disable_livepatch_invalid_remove_snap_option(self):
        """disable-livepatch complains if given an invalid argument."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        process = self.script('disable-livepatch', '-invalidargument')
        self.assertEqual(1, process.returncode)
        self.assertIn('Unknown option "-invalidargument"', process.stderr)

    def test_disable_livepatch_already_disabled(self):
        """disable-livepatch when it's already disabled is detected."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        process = self.script('disable-livepatch')
        self.assertEqual(0, process.returncode)
        self.assertIn('Livepatch is already disabled.', process.stdout)

    def test_disable_livepatch_supported_trusty_xenial_not_precise(self):
        """Livepatch can't be disabled on unsupported distros."""
        for release in ['trusty', 'xenial']:
            self.make_fake_binary(
                'lsb_release', command='echo {}'.format(release))
            process = self.script('disable-livepatch')
            self.assertEqual(0, process.returncode)
        # precise is not supported
        self.make_fake_binary('lsb_release', command='echo precise')
        process = self.script('disable-livepatch')
        # self.assertEqual(4, process.returncode)
        self.assertIn('Sorry, but Canonical Livepatch is not supported on '
                      'precise', process.stderr)

    def test_disable_livepatch(self):
        """disable-livepatch disables the service."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        process = self.script('disable-livepatch')
        self.assertEqual(0, process.returncode)
        self.assertIn('Successfully disabled device. Removed machine-token: '
                      'deadbeefdeadbeefdeadbeefdeadbeef', process.stdout)
        self.assertIn('Note: the canonical-livepatch snap is still installed',
                      process.stdout)

    def test_disable_livepatch_removing_snap(self):
        """disable-livepatch with '-r' will also remove the snap."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        process = self.script('disable-livepatch', '-r')
        self.assertEqual(0, process.returncode)
        self.assertIn('Successfully disabled device. Removed machine-token: '
                      'deadbeefdeadbeefdeadbeefdeadbeef', process.stdout)
        self.assertIn('canonical-livepatch removed', process.stdout)

    def test_enable_livepatch_old_kernel(self):
        """enable-livepatch with an old kernel will not enable livepatch."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        old_kernel = '3.10.0-30-generic'
        self.make_fake_binary('uname', command='echo {}'.format(old_kernel))
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(5, process.returncode)
        self.assertIn('Your currently running kernel ({}) is too '
                      'old'.format(old_kernel), process.stdout)

    def test_enable_livepatch_apt_output_is_hidden(self):
        """Hide all apt output when enabling livepatch if exit status is 0."""
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary('apt-get',
                              command='echo this goes to stderr >&2;'
                              'echo this goes to stdout;exit 0')
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        self.snapd.unlink()
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        # the UA script is redirecting stderr to stdout and capturing that,
        # but then writing everything back to stderr if there was an error
        self.assertNotIn('this goes to stderr', process.stderr)
        self.assertNotIn('this goes to stdout', process.stderr)

    def test_enable_livepatch_apt_output_shown_if_errors(self):
        """enable-livepatch displays apt errors if there were any."""
        apt_error_code = 99
        self.make_fake_binary('lsb_release', command='echo trusty')
        self.make_fake_binary(
            'apt-get', command='echo this goes to stderr >&2;'
            'echo this goes to stdout;exit {}'.format(apt_error_code))
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        self.snapd.unlink()
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(apt_error_code, process.returncode)
        # the UA script is redirecting stderr to stdout and capturing that,
        # but then writing everything back to stderr if there was an error
        self.assertIn('this goes to stderr', process.stderr)
        self.assertIn('this goes to stdout', process.stderr)

    def test_status_precise(self):
        """The status command shows livepatch not available on precise."""
        self.make_fake_binary('lsb_release', command='echo precise')
        self.make_fake_binary('snap', command=SNAP_LIVEPATCH_NOT_INSTALLED)
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        process = self.script('status')
        self.assertIn("livepatch: disabled (not available)", process.stdout)
        self.assertIn("esm: disabled", process.stdout)

    def test_status_precise_esm_enabled(self):
        """The status command shows esm enabled."""
        self.make_fake_binary('lsb_release', command='echo precise')
        self.make_fake_binary('snap', command=SNAP_LIVEPATCH_NOT_INSTALLED)
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        self.make_fake_binary('apt-cache', command='echo esm.ubuntu.com')
        process = self.script('status')
        self.assertIn("livepatch: disabled (not available)", process.stdout)
        self.assertIn("esm: enabled", process.stdout)

    def test_status_xenial(self):
        """The status command shows only livepatch available on xenial."""
        self.make_fake_binary('lsb_release', command='echo xenial')
        self.make_fake_binary(
            'canonical-livepatch', command=LIVEPATCH_DISABLED)
        process = self.script('status')
        self.assertIn("livepatch: disabled", process.stdout)
        self.assertIn("esm: disabled (not available)", process.stdout)

    def test_status_xenial_livepatch_enabled(self):
        """The status command shows livepatch enabled on xenial."""
        self.make_fake_binary('lsb_release', command='echo xenial')
        process = self.script('status')
        self.assertIn("livepatch: enabled", process.stdout)
        # the livepatch status output is also included
        self.assertIn("fully-patched: true", process.stdout)
        self.assertIn("esm: disabled (not available)", process.stdout)
