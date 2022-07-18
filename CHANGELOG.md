# Changelog

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
