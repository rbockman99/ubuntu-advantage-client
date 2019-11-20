from uaclient.entitlements import repo


class ESMBaseEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/esm"
    origin = "UbuntuESM"
    repo_pin_priority = "never"
    disable_apt_auth_only = True  # Only remove apt auth files when disabling


class ESMAppsEntitlement(ESMBaseEntitlement):
    name = "esm-apps"
    title = "ESM Apps"
    description = "UA Apps: Extended Security Maintenance"
    repo_key_file = "ubuntu-advantage-esm-apps.gpg"


class ESMInfraEntitlement(ESMBaseEntitlement):
    name = "esm-infra"
    title = "ESM Infra"
    description = "UA Infra: Extended Security Maintenance"
    repo_key_file = "ubuntu-advantage-esm-infra-trusty.gpg"
