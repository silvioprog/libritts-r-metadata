#!/bin/sh

set -e

DIST_DIR="dist"
TMP_DIR="tmp"

rm -rf "$DIST_DIR"

mkdir -p "$DIST_DIR"
mkdir -p "$TMP_DIR"

files="doc.tar.gz dev_clean.tar.gz dev_other.tar.gz test_clean.tar.gz test_other.tar.gz"

echo "Downloading resources..."
base_url="https://openslr.org/resources/141"
for file in $files; do
    echo "Downloading $file..."
    wget --no-verbose --continue --show-progress "$base_url/$file" -P "$TMP_DIR"
done

echo "Extracting resources..."
for file in $files; do
    echo "Extracting $file..."
    tar -xzf "$TMP_DIR/$file" -C "$TMP_DIR" --keep-old-files
done

echo "Preparing environment..."
python3 -m venv venv
venv/bin/pip install --upgrade pip --quiet
venv/bin/pip install -r requirements.txt --quiet

echo "Generating files..."
venv/bin/python generator.py "$DIST_DIR" "$TMP_DIR"

echo "Done"
