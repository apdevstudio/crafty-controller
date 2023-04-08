# Changelog
## --- [4.0.22] - 2023/04/08
### Bug fixes
- Fix dashboard crash for users without disks or if crafty doesn't have permission to access mount point ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/571))
- Strip Minecraft motd obfuscation chars to prevent text jumping on dashboard ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/572))
### Tweaks
- Improve logging on tz failures ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/569))
- Add fallback for ping domain to provide better feedback on internet connection ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/570))
<br><br>

## --- [4.0.21] - 2023/03/04
### New features
- Add better feedback for uploads with a progress bar ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/546))
- Add ignored exit codes for crash detection ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/553))
- Allow users to change the directory where Crafty Stores Servers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/539)) <br>
    *(Only for non-docker, docker users should change host volume mount)*
- Add host storage display option to the dashboard ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/551))
### Bug fixes
- Fix exception related to page data on server start ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/544))
- Fix logical issue with uploading dynamic files ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/555))
- Fix backups failing by correctly using tz objects ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/556))
- Bump Cryptography/pyOpenSSL for CVE-2023-23931 ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/554))
- Fix debug logging to only display with the -v (verbose) flag ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/560))
- Optimize world size calculation ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/550))
- Only copy bedrock_server executable on update ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/562))
- Fix bug where unloaded servers could not be deleted ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/566))
- Fix bug where "servers" was not appended ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/567))
### Tweaks
- Cleanup authentication helpers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/545))
- Optimize file upload progress WS ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/546))
- Truncate sidebar servers to a max of 10 ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/552))
- Upgrade to FA 6. Add Translations ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/549))([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/558))
- Forge installer and Java Detection improvements ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/559))
- Crafty log clean up -config option ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/563))
### Lang
- Add additional translations to backups page strings ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/543))
- Add additional missing translations ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/549))
<br><br>

## --- [4.0.20] - 2023/01/29
### New features
- Add option to run command before backup. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/536))
- Make Config.json editable from panel. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/532))
- Managed config.json refector (See MR for details). ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/485))
### Bug fixes
- Fix local java server imports. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/529))
- Fix Schedule Restore | Add Backup Config Preservation. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/533))
- Rework `/public` Route. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/538))
### Tweaks
- Hide stats DB directory from files tree. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/530))
- Make it so file tree doesn't reload on upload/delete. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/541))
- Add upload completed feedback to file upload. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/541))
- Added further login screen customisation settings. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/531))
- Set backup filename to use same time as schedule. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/534))
- Move Schedules to from DB to Queue Datatype. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/535))
- Move raknet icon failure to a debug log. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/537))
- Add Default redirection to Dashboard if the user is connected. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/540))
<br><br>

## --- [4.0.19] - 2023/01/07
### Bug fixes
- Fix port tooltip not showing on dash while server online. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/503))
- Fix '+' char in path causing any file operation to fail. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/502))
- Fix colours on public pages. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/504))
- Fix bug where public background was not sent to public pages...like the error page resulting in an error...ironic...I know. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/505))
- Be sure a user cannot server import crafty dir. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/506))
- Remove Pathlib from sub path check ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/507))
- Fix root dir selection in Upload Zip Import ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/508))
- Fix stats error on mac M1 chips ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/512))
- Fix window path escape on java override ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/513))
- Fix Forge import stalling on 1.17 Forge servers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/515))
- Fix issue with server config for SU Accounts ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/516))
- Fix Nested reaction tasks ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/521))
- Remove legacy unzip code causing issues with single file zip files ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/522))
### Tweaks
- Make server directories non-configurable ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/511))
- Add popover to server port to detail it's purpose ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/514))
- Add server start timeout w/ WS Warning ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/518))
- Replace google ping for ntp for internet checks in locked-down countries ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/524))
- Add pushing to DockerHub registry (`arcadiatechnology/crafty-4`) ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/526))
### Lang
- Added Czech translation ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/519))
<br><br>

## --- [4.0.17/4.0.18] - 2022/11/30
### New features
- Automate forge install process through Crafty server creation for Forge server version 1.16 and greater. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/495))
- Tooltip for server port on dashboard. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/496))
- Custom login image backgrounds. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/494))
### Bug fixes
- Fix no port on bedrock server creation. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/493))
### Tweaks
- Docker🐋 | Update image base to Ubuntu 22.04 Jammy. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/497))<br>
*(OpenJDK16 Removed, no jammy backport)*
### Hotfix (4.0.18)
- Apply custom login backgrounds on all public pages. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/499))
<br><br>

## --- [4.0.16] - 2022/10/23
### New features
- Automatically set update url for (new) server creation ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/487))
- Add filter to logs panel ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/484))
### Bug fixes
- Fix conditional issue with zip imports/uploads ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/476))
- Fix API Schedule updates ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/478))
- Add port constraint for all server creation & api ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/479))
- Clean up backup configs when deleting servers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/480))
- Add timeout to socket for servers with incorrect port selection ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/482))
- Fix server_stats db file when deleting server ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/486))
- Fix "cannot render after finish" from backup_now ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/489))
- Fix Support Logs on windows by changing the way we declare projects working directory ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/491) | [Commit](https://gitlab.com/crafty-controller/crafty-4/-/commit/a6aa0f86797856a09c639317c5151c354f4024dc))
### Tweaks
- Fix sidebar to not move when scrolling ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/481))
- Add the rest of CSS predefined colors to themes ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/477))
- Only send realtime stats when clients connected ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/488))
<br><br>

## --- [4.0.15] - 2022/10/02
### New features
- Base Theme Switching (Dark, Light, Default) 🤩🎨 ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/471))
- Upload Zip functionality for server imports 🏗️🎉 ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/472))
### Bug fixes
- Fix traceback on basic schedule with "days" interval ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/469))
- Fix bad method call with API stdin ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/470))<br>
    *(Thank you ['IWant2Tryhard'](https://github.com/MyNameTsThad) for catching that 🐛)*
- Fix clients variable as static to prevent crash if client list changed while sending a websocket ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/473))
<br><br>

## --- [4.0.14] - 2022/09/23
### Bug fixes
- HOTFIX - Rollback breaking websockets change !461 (self.clients was already a set and we tried to subscript a set of a set) ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/467))
<br><br>

## --- [4.0.13] - 2022/09/20
### Bug fixes
- Fix bug where trying to reconfigure unloaded server would stack ([Commit](https://gitlab.com/crafty-controller/crafty-4/-/commit/1b2fef06fb3b02b76c9506caf7e07e932df95fab) | [Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/460))
- Fix traceback error when a user click the roles config tab while already on the roles config page; **this is for new role creation only** ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/452))
- Fix logic issue when removing items from backup exclusions ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/453))
- Cleanup various JS errors ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/455))
- Temp fix for `&amp;` issue in pathing and minecraft colour codes ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/457))
- Cache Gravatar pfp's as to not query every page load ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/459))
- Fix crash on client list changing while sending websockets ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/461))
- Set default parent option on edit of reaction schedule ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/462))
- Fix wtol Nonetype error on server start when 'which java' returns `none` ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/463))
### Tweaks
- Add button to scroll to bottom of vterm ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/454))
- Persist schedules and execution commands across backup restores ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/458))
### Release Testing- Bug fixes
- Fix bug with logical issues surrounding gravatar caching ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/465))
- Fix bug where server terminal would not scroll on startup ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/465))
- Fix issue on post with adding users when no email is included (this also affected editing users) ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/466))
- Fix issue with schedules allowing days to be more than 30 ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/466))
- Fix issue with schedules when trying to edit a cron task ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/466))
<br><br>

## --- [4.0.12] - 2022/09/04
### New features
- Win Portable Updater will now be included in Windows Package ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/446))
- Bedrock Server Creator ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/443))
### Bug fixes
- Fix performance issues on server metrics panels 'with metrics range' ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/440)) ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/448))
- Fix no id on import3 servers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/442))
- Fix functionality of bedrock update ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/441))
- Fix mc-ping Traceback ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/444))
### Tweaks
- Flatten input on password resets ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/447))
<br><br>

## --- [4.0.11] - 2022/08/28
### New features
- Add server import status indicators ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/433))
- Users can now be assigned as manager of other users/roles ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/434))
- Add variable shutdown timeouts ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/435))
- Add server metrics graph ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/436))
### Bug fixes
- Fix creation quota not refilling after server delete ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/434))
- Add missing bedrock dependency (libcurl.so.4) ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/437))
### Tweaks
- Make imports threaded ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/433))
- Add 'Created By' Field to servers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/434))
- Add Zip comments to support archives ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/438))
<br><br>

## --- [4.0.10] - 2022/08/14
### Bug fixes
- Fix reaction tasks not firing ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/423))
- QOL task delay offset not following over on task edit ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/423))
- Fix Fresh Install Detection Logic issues ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/425))
- Fix reload issue on backup panel - on certain browsers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/431))
- Fix '&' in backup paths ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/431))
### Tweaks
- Session Handling | Logout on browser close ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/424))
- Backups Panel | Only display zips ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/426))
- User creation | Fix page browser title ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/427))
<br><br>

## --- [4.0.9] - 2022/08/06
### Bug fixes
- Fix Schedules Traceback Bug ([Merge Request |](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/419) [Commit |](https://gitlab.com/crafty-controller/crafty-4/-/commit/f69d79b7023d6c26fccb5caeae9e47b40ebe5af2) [Commit](https://gitlab.com/crafty-controller/crafty-4/-/commit/ad318296dc93beb5533fcd13066440df9f9e799a))
- Fix handling of missing servers ([Merge Request🎉](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/420))
- Fix offline credits panel stack ([Commit](https://gitlab.com/crafty-controller/crafty-4/-/commit/247678e6c6af5e7d5dbfcf3bfdcec49fc5980e55))
### Tweaks
- credits-v2| Translator status ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/421))
- Use Names in Schedules ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/419))
### Lang
- Make Schedules panel translatable ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/419))
<br><br>

## --- [4.0.8] - 2022/08/05
### New features
- Add Crafty Version Check and notification ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/411))
### Bug fixes
- Fix SU status not sticking on user creation ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/410))
- Handle Missing Java From Win Registry ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/413))
- Disable restart while server is backing up ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/414))
- Fix server creation with serverjars API ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/415))
- Fix API Key delete confirmations ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/416))
### Tweaks
- Add next run to schedule info ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/417))
### Lang
- Updated `es_ES` ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/412))
- Added `pl_PL` ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/412))
<br><br>

## --- [4.0.7] - 2022/07/18
### New features
- Task toggle ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/398))
- Basic API for modifying tasks ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/398))
- Toggle Visible servers on status page ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/399))
### Bug fixes
- Fixes stats recording for Oracle hosts ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/397))
- Improve use of object oriented architecture ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/400))
- Fix issue with API Server Instance is not serializable ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/401))
- Fix issue where the motd was not displayed properly on small screens ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/402))
- Fix log file path issues caused by using relative paths ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/406))
- Fix servers order on creation page ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/407))
### Tweaks
- Remove server.props requirement ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/403))
- Add platform & crafty version info to support logs ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/405))
### Lang
- Updated `fi_FI, fr_FR, he_IL, lv_LV, nl_BE, zh_CN, id_ID, lol_EN` ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/408))
- Added `pt_BR` ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/408))
- Sorted/Corrected `en_EN` ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/408))
<br><br>

## --- [4.0.6] - 2022/07/06
### Bug fixes
- Remove redundant path check on backup restore ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/390))
- Fix issue with stats pinging on slow starting servers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/391))
- Fix unhandled exeption when serverjars api returns 'None' ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/392))
- Fix ajax issue with unzip on firefox ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/393))
- Turn off verbose logging on Docker ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/394))
- Refactor tempdir from packaging logs ([Commit](https://gitlab.com/crafty-controller/crafty-4/-/commit/f1d11bfb0d943c737ef2c4ef77bd0bfc9bcf83ba))
### Tweaks
- Remove autofill on user form ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/395))
- Confirm username does not exist on edituser ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/395))
- Check for passwords matching on client side ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/395))
### Lang
- Add string "cloneConfirm" to german translation ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/389))
<br><br>

## --- [4.0.5] - 2022/06/24
### New features
None
### Bug fixes
- Fix cannot delete backup on page 2 ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/382))
- Fix server starting up without stats monitoring after backup shutdown. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/386))
- Fix pathing issue when launching with just "java" ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/386))
- Fix path issue with update-alternatives  ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/387))
### Tweaks
- Rework server list on status page display for use on small screens ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/383))
- Add clone server confirmation ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/384))
### Lang
- German translation review, fixed some spelling issues and added some missing strings ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/385))
<br><br>

## --- [4.0.4-hotfix2] - 2022/06/21
### Bug fixes
- Fix Traceback on schedule config page ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/381))
<br><br>

## --- [4.0.4-hotfix] - 2022/06/21
### Bug fixes
- Remove bad check for backups path ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/380))
<br><br>

## --- [4.0.4] - 2022/06/21
### New features
- Add shutdown on backup feature ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/373))
- Add detection and dropdown of java versions ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/375))
- Add file-editor size toggle ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/378))
### Bug fixes
- Backup/Config.json rework for API key hardening ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/369))
- Fix stack on ping result being falsy ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/371))
- Fix sec bug with server creation roles ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/376))
### Tweaks
- Spelling mistake fixed in German lang file ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/370))
- Backup failure warning (Tab text goes red) ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/373))
- - ([Merge Request 2](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/377))
- Rework server list on dashboard display for use on small screens ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/372))
- File handling enhancements ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/362))
<br><br>

## --- [4.0.3] - 2022/06/18
### New features
- Integrate Wiki iframe into panel instead of link ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/367))
### Bug fixes
- Amend Java system variable fix to be more specfic since they only affect Oracle. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/364))
- API Token authentication hardening ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/364))
### Tweaks
- Add better error logging for statistic collection ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/359))
<br><br>

## --- [4.0.2-hotfix1] - 2022/06/17
### Crit Bug fixes
- Fix blank server_detail page for general users ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/358))
<br><br>

## --- [4.0.2] - 2022/06/16
### New features
 None
### Bug fixes
- Fix winreg import pass on non-NT systems ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/344))
- Make the WebSocket automatically reconnect. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/345))
- - ([Merge Request 2](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/351))
- Add version inheretence & config check ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/353))
- Fix support log temp file deletion issue/hang ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/354))
<br><br>

## --- [4.0.1] - 2022/06/15
### New features
 None
### Bug fixes
- Remove session.lock warning ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/338))
- Correct Dutch Spacing Issue ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/340))
- Remove no-else-* pylint exemptions and tidy code. ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/342))
