#!/bin/bash

GREP_OPTIONS=''

cookiejar=$(mktemp cookies.XXXXXXXXXX)
netrc=$(mktemp netrc.XXXXXXXXXX)
chmod 0600 "$cookiejar" "$netrc"
function finish {
  rm -rf "$cookiejar" "$netrc"
}

trap finish EXIT
WGETRC="$wgetrc"

prompt_credentials() {
    echo "Enter your Earthdata Login or other provider supplied credentials"
    read -p "Username (akraradets): " username
    username=${username:-akraradets}
    read -s -p "Password: " password
    echo "machine urs.earthdata.nasa.gov login $username password $password" >> $netrc
    echo
}

exit_with_error() {
    echo
    echo "Unable to Retrieve Data"
    echo
    echo $1
    echo
    echo "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E098_dem.tif"
    echo
    exit 1
}

prompt_credentials
  detect_app_approval() {
    approved=`curl -s -b "$cookiejar" -c "$cookiejar" -L --max-redirs 5 --netrc-file "$netrc" https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E098_dem.tif -w %{http_code} | tail  -1`
    if [ "$approved" -ne "302" ]; then
        # User didn't approve the app. Direct users to approve the app in URS
        exit_with_error "Please ensure that you have authorized the remote application by visiting the link below "
    fi
}

setup_auth_curl() {
    # Firstly, check if it require URS authentication
    status=$(curl -s -z "$(date)" -w %{http_code} https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E098_dem.tif | tail -1)
    if [[ "$status" -ne "200" && "$status" -ne "304" ]]; then
        # URS authentication is required. Now further check if the application/remote service is approved.
        detect_app_approval
    fi
}

setup_auth_wget() {
    # The safest way to auth via curl is netrc. Note: there's no checking or feedback
    # if login is unsuccessful
    touch ~/.netrc
    chmod 0600 ~/.netrc
    credentials=$(grep 'machine urs.earthdata.nasa.gov' ~/.netrc)
    if [ -z "$credentials" ]; then
        cat "$netrc" >> ~/.netrc
    fi
}

fetch_urls() {
  if command -v curl >/dev/null 2>&1; then
      setup_auth_curl
      while read -r line; do
        # Get everything after the last '/'
        filename="${line##*/}"

        # Strip everything after '?'
        stripped_query_params="${filename%%\?*}"

        curl -f -b "$cookiejar" -c "$cookiejar" -L --netrc-file "$netrc" -g -o $stripped_query_params -- $line && echo || exit_with_error "Command failed with error. Please retrieve the data manually."
      done;
  elif command -v wget >/dev/null 2>&1; then
      # We can't use wget to poke provider server to get info whether or not URS was integrated without download at least one of the files.
      echo
      echo "WARNING: Can't find curl, use wget instead."
      echo "WARNING: Script may not correctly identify Earthdata Login integrations."
      echo
      setup_auth_wget
      while read -r line; do
        # Get everything after the last '/'
        filename="${line##*/}"

        # Strip everything after '?'
        stripped_query_params="${filename%%\?*}"

        wget --load-cookies "$cookiejar" --save-cookies "$cookiejar" --output-document $stripped_query_params --keep-session-cookies -- $line && echo || exit_with_error "Command failed with error. Please retrieve the data manually."
      done;
  else
      exit_with_error "Error: Could not find a command-line downloader.  Please install curl or wget"
  fi
}

fetch_urls <<'EDSCEOF'
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E098_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E098_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E097_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E097_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E099_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E099_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N05E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N07E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N08E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N10E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N09E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N11E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N06E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N17E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N14E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N13E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N12E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N15E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N16E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E105_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E105_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E106_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E106_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E103_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E103_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E104_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N20E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E100_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E100_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E101_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E101_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E102_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N19E102_num.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E104_dem.tif
https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/ASTGTM.003/ASTGTMV003_N18E104_num.tif
EDSCEOF