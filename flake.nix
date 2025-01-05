{
  description = "fresh browser previews (dev, beta)";

  inputs = {
    flake-utils = {
      url = "github:numtide/flake-utils";
      inputs.systems.follows = "systems";
    };
    nixpkgs.url = "nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          system = "x86_64-linux";
          config.allowUnfree = true;
        };
        google-chrome = channel: pkgs.callPackage ./google-chrome { inherit channel; };
      in
      {
        checks = {
          google-chrome = google-chrome "stable";
          google-chrome-beta = google-chrome "beta";
          google-chrome-dev = google-chrome "dev";
        };
        devShells = {
          default = pkgs.mkShell {
            name = "fresh-browser-previews-shell";

            buildInputs = with pkgs; [
              nix
              nix-prefetch-git
              nixfmt-rfc-style
              (python3.withPackages (
                p3pkgs: with p3pkgs; [
                  feedparser
                  looseversion
                  requests
                ]
              ))
            ];
          };
        };
        packages = {
          default = google-chrome "stable";
          google-chrome = google-chrome "stable";
          google-chrome-beta = google-chrome "beta";
          google-chrome-dev = google-chrome "dev";
        };
      }
    );
}
