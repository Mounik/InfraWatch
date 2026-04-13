#!/bin/bash
# InfraWatch SSL Certificate Checker
# Standalone script to check SSL certificate expiry for domains
set -euo pipefail

WARN_DAYS=30
CRIT_DAYS=7
DOMAINS_FILE="${1:-}"

if [ -z "$DOMAINS_FILE" ]; then
    echo "Usage: $0 <domains-file>"
    echo "  domains-file format: one domain per line"
    echo "  Example: echo 'google.com' > domains.txt && $0 domains.txt"
    exit 1
fi

if [ ! -f "$DOMAINS_FILE" ]; then
    echo "Error: File $DOMAINS_FILE not found"
    exit 1
fi

EXIT_CODE=0

while IFS= read -r domain || [ -n "$domain" ]; do
    [ -z "$domain" ] && continue
    [[ "$domain" =~ ^# ]] && continue

    expiry_epoch=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null \
        | cut -d= -f2)

    if [ -z "$expiry_epoch" ]; then
        echo "CRITICAL: $domain - could not retrieve certificate"
        EXIT_CODE=2
        continue
    fi

    expiry_seconds=$(date -d "$expiry_epoch" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_epoch" +%s 2>/dev/null)
    now_seconds=$(date +%s)
    days_left=$(( (expiry_seconds - now_seconds) / 86400 ))

    if [ "$days_left" -le "$CRIT_DAYS" ]; then
        echo "CRITICAL: $domain - certificate expires in ${days_left} days (<= ${CRIT_DAYS})"
        EXIT_CODE=2
    elif [ "$days_left" -le "$WARN_DAYS" ]; then
        echo "WARNING:  $domain - certificate expires in ${days_left} days (<= ${WARN_DAYS})"
        [ "$EXIT_CODE" -eq 0 ] && EXIT_CODE=1
    else
        echo "OK:       $domain - certificate expires in ${days_left} days"
    fi
done < "$DOMAINS_FILE"

exit $EXIT_CODE