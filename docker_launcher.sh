#!/bin/sh

repair_permissions () {
        echo -e "\033[36mWrapper | \033[35m📋 (1/3) Ensuring root group ownership..."
        find . ! -group root -print0 | xargs -0 -r chgrp root
        echo -e "\033[36mWrapper | \033[35m📋 (2/3) Ensuring group read-write is present on files..."
        find . ! -perm g+rw -print0 | xargs -0 -r chmod g+rw
        echo -e "\033[36mWrapper | \033[35m📋 (3/3) Ensuring sticky bit is present on directories..."
        find . -type d ! -perm g+s -print0 | xargs -0 -r chmod g+s
}

# Check if config exists taking one from image if needed.
if [ ! "$(ls -A --ignore=.gitkeep ./app/config)" ]; then
    echo -e "\033[36mWrapper | \033[33m🏗️  Config not found, pulling defaults..."
    mkdir ./app/config/ 2> /dev/null
    cp -r ./app/config_original/* ./app/config/

    if [ $(id -u) -eq 0 ]; then
        # We're running as root;
        # Look for files & dirs that require group permissions to be fixed
        # This will do the full /crafty dir, so will take a miniute.
        echo -e "\033[36mWrapper | \033[35m📋 Looking for problem bind mount permissions globally..."

        repair_permissions

        echo -e "\033[36mWrapper | \033[32m✅ Initialization complete!"
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
        echo -e "\033[36mWrapper | \033[35m📋 Files present in import directory, checking/fixing permissions..."
        echo -e "\033[36mWrapper | \033[33m⏳ Please be patient for larger servers..."

        repair_permissions

        echo -e "\033[36mWrapper | \033[32m✅ Permissions Fixed! (This will happen every boot until /import is empty!)"
    fi

    # Switch user, activate our prepared venv and lauch crafty
    args="$@"
    echo -e "\033[36mWrapper | \033[32m🚀 Launching crafty with [\033[34m$args\033[32m]"
    exec sudo -u crafty bash -c "source ./.venv/bin/activate && exec python3 main.py $args"
else
    # Activate our prepared venv
    echo -e "\033[36mWrapper | \033[32m🚀 Non-root host detected, using normal exec"
    . ./.venv/bin/activate
    # Use exec as our perms are already correct
    # This is likely if using Kubernetes/OpenShift etc
    exec python3 main.py $@
fi
