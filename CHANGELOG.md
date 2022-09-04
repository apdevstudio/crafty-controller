# Changelog
## --- [4.0.12] - 2022/09/04
### New features
- Win Portable Updater will now be included in Windows Package ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/446))
- Bedrock Server Creator ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/443))
### Bug fixes
- Fix performance issues on server metrics panels 'with metrics range' ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/440)) ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/448))
- Fix no id on import3 servers ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/442))
- Fix functionality of bedrock update ([Merge Request](https://gitlab.com/crafty-controller/crafty-4/-/merge_requests/441))
### Tweaks
TBD
### Lang
TBD
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
