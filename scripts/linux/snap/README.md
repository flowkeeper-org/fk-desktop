# Flowkeeper in Snapcraft

- End-user link: https://snapcraft.io/flowkeeper
- Upstream repo: https://github.com/flathub/org.flowkeeper.Flowkeeper

## Installing Snapcraft on Ubuntu

```shell
snap install snapcraft --classic
snap install lxd
sudo usermod -a -G lxd $USER
# Reboot

sudo apt install git
git clone https://github.com/flowkeeper-org/fk-desktop.git
cd fk-desktop/

# Don't push this to Git
ln -s scripts/linux/snap/snapcraft.yaml snapcraft.yaml
```

## Prerequisites

- Update [snapcraft.yaml](snapcraft.yaml)
- Login to Snapcraft: `snapcraft login`
- Register snap name (you only need to do it once): `snapcraft register flowkeeper`

## Build locally

```shell
snapcraft pack

# Test locally
snap install ./flowkeeper_1.1.0_amd64.snap --dangerous
snap remove flowkeeper

# Publish
snapcraft upload --release=stable flowkeeper_1.1.0_amd64.snap

# Test end result
snap install flowkeeper
flowkeeper
snap remove flowkeeper
```
