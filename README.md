# browser-previews flake for NixOS users

This flake provides the latest Chrome stable, beta and dev releases. The flake is updated regularly to ensure fast and up to date releases, which would otherwise not be possible in [nixpkgs](https://github.com/NixOS/nixpkgs).

## Why?

`google-chrome-beta` and `google-chrome-dev` were not getting maintained in nixpkgs,
and were dropped in [NixOS/nixpkgs#261870](https://github.com/NixOS/nixpkgs/pull/261870).

## Available packages

Run `nix flake show github:r-k-b/browser-previews` for the up-to-date list.

## How?

### To directly run latest `google-chrome` from this flake

```bash
NIXPKGS_ALLOW_UNFREE=1 nix run github:r-k-b/browser-previews#google-chrome --impure
```

Likewise for google-chrome-beta or google-chrome-dev:

```bash
NIXPKGS_ALLOW_UNFREE=1 nix run github:r-k-b/browser-previews#google-chrome-beta --impure
```

```bash
NIXPKGS_ALLOW_UNFREE=1 nix run github:r-k-b/browser-previews#google-chrome-dev --impure
```

### To install a package from this flake

- First you must add it as a input to your `flake.nix`:

```nix
inputs.browser-previews = { url = "github:r-k-b/browser-previews";
                            inputs.nixpkgs.follows = "nixpkgs"; };
```

- Pass `inputs` to your modules using `specialArgs`.

- Then in `configuration.nix`, use it like this:

```nix
{ config, lib, pkgs, inputs, ... }:
{
  environment.systemPackages = with inputs.browser-previews.packages.${pkgs.system}; [
    google-chrome # Stable Release
    google-chrome-beta # Beta Release
    google-chrome-dev # Dev Release
  ];
}
```

(Must have flakes enabled.)

## Why not include chromium?

The chromium build takes more resources than I'm willing to spend.
