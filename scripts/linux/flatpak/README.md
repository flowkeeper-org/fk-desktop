# Flowkeeper in Flatpak

- End-user link: https://flathub.org/apps/org.flowkeeper.Flowkeeper
- Fork repo: https://github.com/flowkeeper-org/org.flowkeeper.Flowkeeper
- Upstream repo: https://github.com/flathub/org.flowkeeper.Flowkeeper

## Prerequisites

- Update [metadata.xml](../common/org.flowkeeper.Flowkeeper.metainfo.xml)
- Sync the fork repo

## Build locally

```shell
flatpak-builder --force-clean --user --install-deps-from=flathub --repo=repo --install builddir org.flowkeeper.Flowkeeper.yaml
flatpak run org.flowkeeper.Flowkeeper
flatpak uninstall org.flowkeeper.Flowkeeper
```

Update the fork repo and open a PR to upstream. Wait till the build pipeline passes.
