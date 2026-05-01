This is a set of four workflows that should be imported into each pkg-*
repository to enable Debusine CI. They must be placed in the default branch,
and debusine-pr-hook.yml and debusine-release.yml must also be copied to each
enabled packaging (`qcom/debian/*)` branch. README.debusine.md should also be
copied into each branch touched to help future maintainers.

When these files are updated, they must also updated in every "managed" pkg-*
repository. Currently this process is manual. We
[agreed](https://github.com/qualcomm-linux/debusine-action/pull/15) that once
landed into this repository through a peer-reviewed PR, no further PRs are
required to update the corresponding workflow files in the pkg-* repositories.
