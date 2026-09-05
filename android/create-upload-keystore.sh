#!/usr/bin/env bash
# Creates a Play upload keystore on YOUR computer. Keep this file private and back it up.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f desifitness-upload.jks ]]; then
  echo "desifitness-upload.jks already exists. Not overwriting."
  exit 1
fi

read -r -s -p "Keystore password: " STORE_PASS
echo
read -r -s -p "Repeat keystore password: " STORE_PASS2
echo
if [[ "$STORE_PASS" != "$STORE_PASS2" ]]; then
  echo "Passwords do not match."
  exit 1
fi

keytool -genkeypair -v \
  -keystore desifitness-upload.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias upload \
  -dname "CN=Muhammad Badar Hayat, OU=Desi Fitness, O=Muhammad Badar Hayat, L=Lahore, ST=Punjab, C=PK" \
  -storepass "$STORE_PASS" \
  -keypass "$STORE_PASS"

cat > keystore.properties <<EOF
storeFile=desifitness-upload.jks
storePassword=$STORE_PASS
keyAlias=upload
keyPassword=$STORE_PASS
EOF

echo
echo "Created desifitness-upload.jks and keystore.properties."
echo "Back both up somewhere safe. If you lose them, you cannot update the Play listing with a new upload key without extra Play Console recovery steps."
