#!/bin/sh

# Check if config exists taking one from image if needed.
if [ ! "$(ls -A --ignore=.gitkeep ./app/config)" ]; then
    echo "\033[36mWrapper | \033[33m🏗️  Config not found, pulling defaults..."
    mkdir ./app/config/ 2> /dev/null
    cp -r ./app/config_original/* ./app/config/

    if [ $(id -u) -eq 0 ]; then
        # We're running as root;
        # Look for files & dirs that require group permissions to be fixed
        # This will do the full /crafty dir, so will take a miniute.
        echo "\033[36mWrapper | \033[35m📋 Looking for problem bind mount permissions globally..."
        find . ! -group root -exec chgrp root {} \;
        find . ! -perm g+rw -exec chmod g+rw {} \;
        find . -type d ! -perm g+s -exec chmod g+s {} \;
    fi
else
    # Keep version file up to date with image
    cp -f ./app/config_original/version.json ./app/config/version.json
fi


if [ $(id -u) -eq 0 ]; then
    # We're running as root

    # If we find files in import directory, we need to ensure all dirs are owned by the root group,
    # This fixes bind mounts that may have incorrect perms.
    if [ "$(find ./import -type f ! -name '.gitkeep')" ]; then
        echo "\033[36mWrapper | \033[35m📋 Files present in import directory, checking/fixing permissions..."
        echo "\033[36mWrapper | \033[33m⏳ Please be patient for larger servers..."
        find . ! -group root -exec chgrp root {} \;
        find . ! -perm g+rw -exec chmod g+rw {} \;
        find . -type d ! -perm g+s -exec chmod g+s {} \;
        echo "\033[36mWrapper | \033[32m✅ Permissions Fixed! (This will happen every boot until /import is empty!)"
    fi

    # Switch user, activate our prepared venv and lauch crafty
    args="$@"
    echo "\033[36mWrapper | \033[32m🚀 Launching crafty with [\033[34m$args\033[32m]"
    exec sudo -u crafty bash -c "source ./.venv/bin/activate && exec python3 main.py $args"
else
    # Activate our prepared venv
    echo "\033[36mWrapper | \033[32m🚀 Non-root host detected, using normal exec"
    . ./.venv/bin/activate
    # Use exec as our perms are already correct
    # This is likely if using Kubernetes/OpenShift etc
    exec python3 main.py $@
fi
