# Crafty 4 - A contributors guide.
*Don't Panic!*<br><br>

First off, thank you for choosing Crafty Controller! <br>
We hope you've been enjoying Crafty so far and are absolutely thrilled that you are looking to contribute!

The following guide will show you how to easily and safely contribute to our current workflow. There are a few components that need to be taken into account and processes that need followed before we can merge your code into our repository.
<br><br>
## Getting started
There are two incredibly helpful ways of contributing to the project: `Issues` and `Changes`.

### Issues

#### Create a new issue

If you spot a problem with crafty, [search if an issue already exists](https://gitlab.com/crafty-controller/crafty-4/-/issues). If a related issue doesn't exist, you can [open a new issue](https://gitlab.com/crafty-controller/crafty-4/-/issues/new) using a relevant issue template:
- Bug - For any bugs you may find in Crafty.
- Feature Request - For any features you'd like to see in Crafty.
- Change Request - For any changes you'd like to see to existing Crafty functions.

#### Solve an issue

If you're feeling inclined and want to help us with our workload you can have a look through our [existing issues](https://gitlab.com/crafty-controller/crafty-4/-/issues) to find one that interests you. (You can narrow down the search using `labels` as filters.)

### Make changes

1. [Install Git](https://docs.gitlab.com/ee/topics/git/how_to_install_git/).

2. Fork the repository.

3. Create a branch from `dev` with a suitable name that matches our folder branch flow<br> `bugfix/` `tweak/` `lang/` `feature/`<br>
   For Example:<br>
     `tweak/websocket-auto-reconnect`<br>
     `bugfix/blank-page-as-non-superuser`<br>
     `lang/german-spelling-correction`<br>
     `feature/support-log-downloader`

4. Make your changes!

5. Make sure your code is formatted correctly ([We use Black](https://black.readthedocs.io/en/stable/getting_started.html)).
> 🧑‍🎓 If you are using **VSCODE** you can follow this [handy dandy tiny guide](https://marcobelo.medium.com/setting-up-python-black-on-visual-studio-code-5318eba4cd00) on how to setup formatting on save.<br>
This will allow you to write your code without having to think about ⬛**black**, and then when you press `ctrl+s` black will immediately format your code!


### Commit your update

Commit your changes once you are happy with them. See [Chris Beam's guide](https://chris.beams.io/posts/git-commit/) on how to write a suitable commit message. This will be enforced. If your commit messages don't meet suitable standards, your merge request will not be merged.

- Please make sure and test the area that you have been working in, this makes our reviewers' lives easier!

### Create a merge request

Once you are all done making your changes make a MR (merge request) into our `dev` branch.

- Fill in the merge request template. This template helps reviewers understand your changes as well as the purpose of your merge request. Make sure to include details!
- If you are solving an issue don't forget to link the MR to that issue.
- Make sure to [allow upstream commits](https://docs.gitlab.com/ee/user/project/merge_requests/allow_collaboration.html#allow-commits-from-upstream-members) so we can prepare the branch for merge if it's not quite right. <br> A member of the maintainer team will review your proposal. We may also ask questions or request additional information at this stage. On some occasions we may reject your proposal, please don't be disheartened if we do so. Even if your code does not make it into the repo we appreciate your time and effort spent on creating the MR.
- Please make sure your merge request complies with the pylint's Code Climate report on your MR and fix any issues that are raised.
- We may ask for changes to be made before a MR can be merged, either using [suggested changes](https://docs.gitlab.com/ee/user/project/merge_requests/reviews/suggestions.html), inline comments or merge request threads. You can apply suggested changes directly through GitLab's UI. You can also make any other changes in your fork, then commit them to your branch before the merge request is processed.
- As you update your MR with changes we request, mark each thread as [resolved](https://docs.gitlab.com/ee/user/discussions/#resolve-a-thread).
- If you run into any merge issues checkout this [git tutorial](https://about.gitlab.com/blog/2016/09/06/resolving-merge-conflicts-from-the-gitlab-ui/) to help you resolve them. (If you get stuck your reviewer can help you.)

### Your MR is merged!

Congratulations 🎉 You've successfully made a contribution to Crafty!



