# Privacy Policy

## Local data storage

Flowkeeper stores your data as plain-text files on your local file system. The exact location is configurable in "Settings (F10) > Connection >
Data file". This data does not contain any personally identifiable information beyond what you type in Flowkeeper. You can audit the content of 
those data files using a simple text editor like Notepad.

## Using GitHub

In addition to Flowkeeper source code, GitHub hosts 
- flowkeeper.org website, 
- compiled binaries / installers,
- information about releases,
- antivirus scan results.

Every time you launch Flowkeeper, the app checks for updates by sending a request to GitHub Releases API: 
https://api.github.com/repos/flowkeeper-org/fk-desktop/releases/latest. This is the only outgoing network connection that Flowkeeper attempts to
establish. This HTTP request does not carry any personally identifiable payload.

Update checks are enabled by default, but you can disable them in "Settings (F10) > General > Check for updates."

Flowkeeper binaries are hosted using GitHub Releases, see https://github.com/flowkeeper-org/fk-desktop/releases. GitHub counts the total number of 
downloads for each binary in each release, and exposes this data via its public REST API.

## Remote data storage

Support for an experimental online data sync via WebSockets is built into the application, but it is disabled and is not accessible by end users.
In the future this Privacy Policy will evolve to include other data storage modes, but as of version v1.1, Flowkeeper is local-only.

## Websites

Flowkeeper.org does not store any cookies and does not track its users in any way. It is hosted via GitHub Pages, so you can audit its code and 
see it for yourself: https://github.com/flowkeeper-org/website

## Diagnostics, telemetry, etc.

Flowkeeper desktop application does not collect nor send any diagnostics or telemetry data.

## Contact Information

For any questions or concerns regarding the privacy policy, please reach out via contact@flowkeeper.org.
