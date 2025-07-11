# Releasing Flowkeeper

- Run unit and e2e tests in all available VMs.
- Run the build pipeline and check Windows binaries via Virustotal.
- Collect screenshots from all supported environments, upload them to website repo.
- Prepare the release page for the website. Record screenshots and GIFs for new features.
- Prepare a release announcement for LinkedIn, Reddit, Discord, Telegram, and mailing list.
- Review CHANGELOG.txt and update the date.
- Review and merge the rc PR into main.
- Create a new tag + release in GitHub, mark it as a draft.
- Wait for the release pipeline to complete.
- Trigger private Jenkins pipeline to sign Windows binaries.
- Check the binaries via Virustotal one more time.
- Remove the "draft" flag from GitHub release.
- Check website -- it should pick up changes automatically.
- Update download links on the website, if needed.
- Update OBS repo.
- Update Flatpak repo.
- Reply and close related GitHub issues.
- Distribute the release announcement on LinkedIn, Reddit, Discord, Telegram, and mailing list.
- Write about new Flowkeeper features in r/kde, r/opensource, r/Windows10, r/Windows11, r/windows, 
r/macapps, r/Python, r/QtFramework, r/debian, r/openSUSE, r/linux, r/pomodoro, r/ProductivityApps.

# Qt6 versions

Last updated: **9 June 2025** for Flowkeeper **1.0.0**.

| OS                    | Released   | EOL        | Python  | Qt 6  | PySide6 | Running options | Comments              |
|-----------------------|------------|------------|---------|-------|---------|-----------------|-----------------------|
| Debian Bullseye 11    | 2021-08-14 | 2024-08-14 | 3.9     | N/A   |         |                 | 6.4.2 is in backports |
| Debian Bookworm 12    | 2023-06-10 | 2026-06-10 | 3.11    | 6.4.2 |         |                 |                       |
| Debian Trixie 13      | 2025-..-.. | N/A        | 3.12    | 6.8.2 |         |                 |                       |
| Debian Sid            | N/A        | N/A        | 3.13    | 6.8.2 |         |                 |                       |
| Ubuntu Focal 20.04    | 2020-04-23 | 2025-05-29 | 3.8.2   | N/A   |         |                 |                       |
| Ubuntu Jammy 22.04    | 2022-04-21 | 2027-06-01 | 3.10.6  | 6.2.4 |         |                 |                       |
| Ubuntu Noble 24.04    | 2024-04-25 | 2029-05-31 | 3.12.3  | 6.4.2 |         |                 |                       |
| Ubuntu Oracular 24.10 | 2024-10-10 | 2025-07-.. | 3.12.6  | 6.6.2 |         |                 |                       |
| Ubuntu Plucky 25.04   | 2025-04-17 | 2026-01-.. | 3.13.3  | 6.8.3 |         |                 |                       |
| Fedora 40             | 2024-04-23 | 2025-05-13 | 3.12.3  | 6.6.2 |         |                 |                       |
| Fedora 41             | 2024-10-29 | 2025-11-19 | 3.13.0  | 6.7.2 |         |                 |                       |
| Fedora 42             | 2025-04-15 | 2026-05-16 | 3.13.2  | 6.8.2 |         |                 |                       |
| RHEL 8                | 2019-05-07 | 2029-..    | 3.6     | N/A   |         |                 |                       |
| RHEL 9                | 2022-05-17 | 2032-..    | 3.12.9  | N/A   |         |                 |                       |
| RHEL 10               | 2025-05-20 | 2035-..    | 3.12.9  | 6.8.1 |         |                 |                       |
| openSUSE Leap 15.6    | 2024-06-10 | 2025-12-.. | 3.11    | 6.6.3 |         |                 |                       |
| openSUSE Tumbleweed   | N/A        | N/A        | 3.13    | 6.9.0 |         |                 |                       |
| Slackware 15          | 2022-02-02 | N/A        | 3.9.10  | N/A   |         |                 |                       |
| Slackware Current     | N/A        | N/A        | 3.12.10 | 6.8.3 |         |                 |                       |

Here *Running options* are:
- **S**: Run directly from source (git clone, generate-resources.sh, run.sh)
- **V**: Run from source in a Python Virtual Environment (venv)
- **D**: Flowkeeper is available in a distro packages repository
- **3**: Flowkeeper is available in a 3rd-party packages repository
- **P**: A portable binary or standalone ZIP from flowkeeper.org
- **I**: An installer (e.g. DEB) from flowkeeper.org
- **F**: Flatpak (org.flowkeeper.Flowkeeper on Flathub)
- **A**: AppImage from flowkeeper.org works

This table needs to be updated with:
1. PySide6 versions
2. Shell command to install those
3. How to run Flowkeeper there (see running options above)
