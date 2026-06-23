# Ansible Setup Scripts

These are ansible playbooks to ensure all of my hosts have at least a minimal
baseline together.

It should support MacOS, Debian-based Linux, and Arch-based Linux.

## Features

- Ensure users are present
- Ensure skel is deployed to each user
- Ensure users have shells set to zsh
- Install package groups depending on host role
