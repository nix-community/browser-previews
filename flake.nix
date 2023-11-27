{
  description = "fresh browser previews (dev, beta)";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        google-chrome = channel:
          pkgs.callPackage ./google-chrome { inherit channel; };
      in {
        devShells = {
          default = pkgs.mkShell {
            name = "fresh-browser-previews-shell";

            buildInputs = with pkgs; [
              nix
              nix-prefetch-git
              nixfmt
              (python3.withPackages
                (p3pkgs: [ p3pkgs.feedparser p3pkgs.requests ]))
            ];
          };
        };
        packages = {
          default = google-chrome "stable";
          google-chrome = google-chrome "stable";
          google-chrome-beta = google-chrome "beta";
          google-chrome-dev = google-chrome "dev";
        };
      });
}
