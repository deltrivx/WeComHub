#!/bin/bash
############
{0}
############

############
# WeComHub notification agent (configuration half).
#
# This file holds ONLY your configuration. The implementation lives in
#   /usr/local/emhttp/plugins/WeComHub/wecom-hub-notify-agent.sh
# and is updated together with the plugin. Because this file is not managed by
# the plugin, your settings survive plugin upgrades.
#
# Edit the variables through:
#   Settings -> Notification -> Notification Agents -> WeComHub
# Do not edit the block above by hand; the page regenerates it on Apply.
############

AGENT="/usr/local/emhttp/plugins/WeComHub/wecom-hub-notify-agent.sh"
if [[ -x "$AGENT" ]]; then
  exec "$AGENT"
fi

# Plugin body missing: record it instead of failing silently.
echo "$(date) plugin body not found: $AGENT" >>/var/log/notify_WeComHub
exit 0
