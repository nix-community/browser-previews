# why?

google-chrome-beta and google-chrome-dev were not getting maintained in nixpkgs,
and were dropped in https://github.com/NixOS/nixpkgs/pull/261870.


# how?

```
NIXPKGS_ALLOW_UNFREE=1 nix run github:r-k-b/browser-previews#google-chrome-dev --impure
```

(Must have flakes enabled.)


# why not include chromium?

The chromium build takes more resources than I'm willing to spend.
