# Releasing Flowkeeper

- Run unit and e2e tests in all available VMs.
- Run the build pipeline and check Windows binaries via Virustotal.
- Collect screenshots from all supported environments, upload them to website repo.
- Prepare the release page for the website. Record screenshots and GIFs for new features.
- Prepare a release announcement for LinkedIn, Reddit, Discord, Telegram, and mailing list.
- Review CHANGELOG.txt and update the date.
- Review and merge the rc PR into main.
- Create a new tag + release in GitHub, mark it as a draft.
- Wait for the release pipeline to complete, then sign Windows binaries.
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
