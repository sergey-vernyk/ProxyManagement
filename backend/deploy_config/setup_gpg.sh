#!/bin/bash

gpg_private=$1
gpg_public=$2
gpg_id=$3

if [[ $# -ne 3 ]]; then
    echo "Usage: ./setup_gpg.sh <gpg_private> <gpg_public> <gpg_id>"
    exit 1
fi

echo "$gpg_private" | gpg --import
echo "$gpg_public" | gpg --import

echo "$(gpg --list-keys --fingerprint |
    grep -B 1 '${gpg_id}' |
    head -1 |
    tr -d '[:space:]' |
    cut -d '=' -f 2):6" | gpg --import-ownertrust
